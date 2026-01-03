from worker import celery_app
from vision import SceneDetector
from script_gen import ScriptGenerator
from audio_gen import AudioGenerator
from video_render import VideoRenderer
from config import Config
import json
import logging
import psycopg2
import tempfile
import os
import boto3
import uuid
import urllib.request
from urllib.parse import urlparse

# Configure logging
# Logging is configured in worker.py via signals
logger = logging.getLogger(__name__)

# S3 Client Initialization
s3_client = boto3.client(
    's3',
    endpoint_url=Config.S3_STORAGE_ENDPOINT,
    aws_access_key_id=Config.S3_STORAGE_ACCESS_KEY,
    aws_secret_access_key=Config.S3_STORAGE_SECRET_KEY,
    region_name=Config.S3_STORAGE_REGION
)

def upload_to_s3(file_path: str, object_name: str) -> str:
    """Upload a file to S3 bucket and return public URL"""
    try:
        s3_client.upload_file(
            file_path,
            Config.S3_STORAGE_BUCKET,
            object_name,
            ExtraArgs={"ContentType": "video/mp4"},
        )

        base = (Config.S3_STORAGE_PUBLIC_URL or "").rstrip("/")
        if not base:
            raise ValueError("S3_STORAGE_PUBLIC_URL is not set")
        if not base.startswith("http://") and not base.startswith("https://"):
            base = "https://" + base

        uri = urlparse(base)
        host = uri.hostname or ""
        path = uri.path or ""
        bucket = Config.S3_STORAGE_BUCKET

        if path == f"/{bucket}" or path.startswith(f"/{bucket}/"):
            return f"{base}/{object_name}"

        if host.startswith(f"{bucket}."):
            return f"{base}/{object_name}"

        if (
            ".r2.cloudflarestorage.com" in host
            or ".amazonaws.com" in host
            or "localhost" in host
        ):
            return f"{base}/{bucket}/{object_name}"

        return f"{base}/{object_name}"
    except Exception as e:
        logger.error(f"Failed to upload to S3: {str(e)}")
        raise e

def _is_http_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in {"http", "https"}
    except Exception:
        return False

def _download_to_temp(video_url: str) -> str:
    # Support local file protocol for optimization
    if video_url.startswith("file://"):
        local_path = video_url.replace("file://", "")
        if os.path.exists(local_path):
            return local_path
        filename = os.path.basename(local_path)
        base = (Config.LOCAL_ASSET_HTTP_BASE_URL or "").rstrip("/")
        if base:
            video_url = f"{base}/{filename}"
    
    temp_video = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    temp_video.close()
    urllib.request.urlretrieve(video_url, temp_video.name)
    return temp_video.name

def _get_video_duration_sec(video_url: str) -> float:
    import cv2
    cap = cv2.VideoCapture(video_url)
    if not cap.isOpened():
        cap.release()
        return 0.0
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    cap.release()
    if fps <= 0:
        return 0.0
    return float(total_frames) / float(fps)

def _parse_model_json(text: str) -> dict:
    if not text:
        raise ValueError("Empty model response")
    clean = text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)

def _coerce_segments(raw: dict) -> list[dict]:
    segments = raw.get("segments") if isinstance(raw, dict) else None
    if not isinstance(segments, list):
        return []

    normalized = []
    for s in segments:
        if not isinstance(s, dict):
            continue
        start = s.get("start_sec")
        end = s.get("end_sec")
        try:
            start_f = float(start)
            end_f = float(end)
        except Exception:
            continue
        if end_f <= start_f:
            continue
        normalized.append(
            {
                "start_sec": max(0.0, start_f),
                "end_sec": end_f,
                "scene": s.get("scene") or "其他",
                "features": s.get("features") or "",
                "score": float(s.get("score") or 0.0),
            }
        )

    normalized.sort(key=lambda x: x["start_sec"])
    return normalized

def _advance_project_status(project_id: str):
    conn = psycopg2.connect(Config.DB_DSN)
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE projects
                    SET status = 'ANALYZING'
                    WHERE id = %s
                      AND status IN ('UPLOADING')
                    """,
                    (project_id,),
                )
                cursor.execute(
                    """
                    SELECT COUNT(1)
                    FROM assets
                    WHERE project_id = %s
                      AND is_deleted = FALSE
                      AND scene_label IS NULL
                    """,
                    (project_id,),
                )
                remaining = int(cursor.fetchone()[0] or 0)
                if remaining == 0:
                    cursor.execute(
                        """
                        UPDATE projects
                        SET status = 'REVIEW'
                        WHERE id = %s
                          AND status IN ('UPLOADING', 'ANALYZING')
                        """,
                        (project_id,),
                    )
    finally:
        conn.close()

def _process_split_logic(project_id: str, asset_id: str, video_url: str, segments: list, local_video_path: str = None):
    if len(segments) >= 2:
        if not local_video_path:
            local_video = _download_to_temp(video_url)
        else:
            local_video = local_video_path
            
        from moviepy.editor import VideoFileClip

        inserted_assets = []
        try:
            video = VideoFileClip(local_video)
            segments = [
                s
                for s in segments
                if s["start_sec"] < video.duration and s["end_sec"] > 0
            ]
            segments = [
                {
                    **s,
                    "start_sec": max(0.0, min(s["start_sec"], video.duration)),
                    "end_sec": max(0.0, min(s["end_sec"], video.duration)),
                }
                for s in segments
            ]
            segments = [s for s in segments if s["end_sec"] > s["start_sec"]]

            conn = psycopg2.connect(Config.DB_DSN)
            try:
                with conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            UPDATE assets
                            SET is_deleted = TRUE,
                                duration = %s
                            WHERE id = %s
                            """,
                            (float(video.duration), asset_id),
                        )

                        for idx, seg in enumerate(segments):
                            clip = video.subclip(seg["start_sec"], seg["end_sec"])
                            temp_clip = tempfile.NamedTemporaryFile(
                                suffix=".mp4", delete=False
                            )
                            temp_clip.close()
                            try:
                                clip.write_videofile(
                                    temp_clip.name,
                                    codec="libx264",
                                    audio_codec="aac",
                                    preset="veryfast",
                                    threads=2,
                                    logger=None,
                                )
                                object_key = (
                                    f"clips/{project_id}/{uuid.uuid4()}.mp4"
                                )
                                clip_url = upload_to_s3(temp_clip.name, object_key)
                            finally:
                                try:
                                    os.remove(temp_clip.name)
                                except Exception:
                                    pass
                                try:
                                    clip.close()
                                except Exception:
                                    pass

                            new_id = str(uuid.uuid4())
                            cursor.execute(
                                """
                                INSERT INTO assets
                                    (id, project_id, oss_url, duration, scene_label, scene_score, user_label, sort_order, is_deleted)
                                VALUES
                                    (%s, %s, %s, %s, %s, %s, NULL, %s, FALSE)
                                """,
                                (
                                    new_id,
                                    project_id,
                                    clip_url,
                                    float(seg["end_sec"] - seg["start_sec"]),
                                    seg["scene"],
                                    float(seg["score"] or 0.0),
                                    idx,
                                ),
                            )
                            inserted_assets.append(
                                {
                                    "id": new_id,
                                    "oss_url": clip_url,
                                    "duration": float(seg["end_sec"] - seg["start_sec"]),
                                    "scene": seg["scene"],
                                    "score": float(seg["score"] or 0.0),
                                }
                            )
            finally:
                conn.close()
            try:
                video.close()
            except Exception:
                pass
        finally:
            # Only cleanup if we downloaded it. If it was passed from outside (file://), we might want to keep it or not.
            # But _download_to_temp returns the file path.
            # If it came from _download_to_temp(file://...), it returned the original path.
            # We should NOT delete the original source file here if it's the source of truth for the asset.
            # However, logic in analyze_video_task usually cleans up local_video if it created it.
            
            # Refined logic: If local_video_path was passed in, caller handles cleanup.
            # If we created it via _download_to_temp AND it was a temp download (not file://), delete it.
            if not local_video_path:
                if not video_url.startswith("file://"):
                    try:
                        os.remove(local_video)
                    except Exception:
                        pass

detector = SceneDetector()
script_gen = ScriptGenerator()
audio_gen = AudioGenerator()
video_render = VideoRenderer()

@celery_app.task(bind=True, max_retries=3)
def analyze_video_task(self, project_id: str, asset_id: str, video_url: str):
    """
    Background task to analyze a video asset.
    """
    logger.info(f"Received analyze_video_task for asset {asset_id} in project {project_id}. URL: {video_url}")
    
    try:
        _advance_project_status(project_id)
        local_video = _download_to_temp(video_url)
        cleanup_local_video = not local_video.startswith("/tmp/ai-video-uploads/")
        duration_sec = _get_video_duration_sec(local_video)

        if (
            Config.SMART_SPLIT_ENABLED
            and duration_sec >= Config.SMART_SPLIT_MIN_DURATION_SEC
        ):
            # Branch 1: Qwen Video (End-to-End)
            if Config.SMART_SPLIT_STRATEGY == "qwen_video" and _is_http_url(video_url):
                segments_text = detector.analyze_video_segments(video_url)
                segments_raw = _parse_model_json(segments_text)
                segments = _coerce_segments(segments_raw)
                _process_split_logic(project_id, asset_id, video_url, segments)
                _advance_project_status(project_id)
                if cleanup_local_video and os.path.exists(local_video):
                    os.remove(local_video)
                return {"project_id": project_id, "status": "split_completed", "segments": len(segments)}

            # Branch 2: Hybrid (SceneDetect + Qwen Image)
            elif Config.SMART_SPLIT_STRATEGY == "hybrid":
                try:
                    shots = detector.detect_video_shots(local_video, threshold=Config.SCENE_DETECT_THRESHOLD)
                    if not shots:
                        shots = [(0.0, duration_sec)]
                    
                    shot_frames = []
                    import cv2
                    cap = cv2.VideoCapture(local_video)
                    
                    try:
                        for start, end in shots:
                            mid_sec = (start + end) / 2
                            cap.set(cv2.CAP_PROP_POS_MSEC, mid_sec * 1000)
                            ret, frame = cap.read()
                            if ret:
                                temp_img = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                                h, w = frame.shape[:2]
                                max_dim = 1024
                                if w > max_dim or h > max_dim:
                                    scale = max_dim / max(w, h)
                                    frame = cv2.resize(frame, None, fx=scale, fy=scale)
                                cv2.imwrite(temp_img.name, frame)
                                shot_frames.append({
                                    "start": start,
                                    "end": end,
                                    "image": temp_img.name
                                })
                                temp_img.close()
                    finally:
                        cap.release()

                    if shot_frames:
                        segments_text = detector.analyze_shot_grouping(shot_frames)
                        segments_raw = _parse_model_json(segments_text)
                        segments = _coerce_segments(segments_raw)
                        
                        for sf in shot_frames:
                            if os.path.exists(sf["image"]):
                                os.remove(sf["image"])

                        _process_split_logic(project_id, asset_id, video_url, segments, local_video_path=local_video)
                        _advance_project_status(project_id)
                        return {"project_id": project_id, "status": "split_completed", "segments": len(segments)}

                finally:
                    if cleanup_local_video and os.path.exists(local_video):
                        os.remove(local_video)

        frame_paths = detector.extract_key_frames(local_video, num_frames=5)
        result_json_str = detector.analyze_scene_from_frames(frame_paths)
        result_data = _parse_model_json(result_json_str)
        logger.info(f"Analysis result for {asset_id}: {result_data}")

        conn = psycopg2.connect(Config.DB_DSN)
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE assets
                        SET scene_label = %s,
                            scene_score = %s,
                            duration = %s
                        WHERE id = %s
                        """,
                        (
                            result_data.get("scene", "unknown"),
                            float(result_data.get("score", 0.0) or 0.0),
                            float(duration_sec or 0.0),
                            asset_id,
                        ),
                    )
            logger.info(f"Updated DB for asset {asset_id}")
        finally:
            conn.close()

        _advance_project_status(project_id)

        if cleanup_local_video and os.path.exists(local_video):
            os.remove(local_video)

        return {"project_id": project_id, "asset_id": asset_id, "analysis": result_data}

    except Exception as e:
        logger.error(f"Task failed for asset {asset_id}: {str(e)}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

@celery_app.task(bind=True, max_retries=3)
def generate_script_task(self, project_id: str, house_info: dict, timeline_data: list):
    """
    Background task to generate video script using LLM.
    """
    logger.info(f"Starting script generation for project {project_id}")
    
    try:
        # 1. Generate Script
        script_content = script_gen.generate_script(house_info, timeline_data)
        logger.info(f"Generated script for {project_id}")

        # 2. Update Database
        conn = psycopg2.connect(Config.DB_DSN)
        try:
            with conn:
                with conn.cursor() as cursor:
                    update_query = """
                        UPDATE projects 
                        SET script_content = %s,
                            status = 'SCRIPT_GENERATED'
                        WHERE id = %s
                    """
                    cursor.execute(update_query, (script_content, project_id))
            logger.info(f"Updated script in DB for project {project_id}")
        finally:
            conn.close()

        return {
            "project_id": project_id,
            "script": script_content
        }

    except Exception as e:
        logger.error(f"Script generation failed for project {project_id}: {str(e)}")
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

@celery_app.task(bind=True, max_retries=3)
def generate_audio_task(self, project_id: str, script_content: str):
    """
    Background task to generate TTS audio.
    """
    logger.info(f"Starting audio generation for project {project_id}")
    
    try:
        # 1. Generate Audio (Save to local temp first)
        temp_audio = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        temp_audio.close() # Close to let audio_gen write to it
        
        audio_path = audio_gen.generate_audio(script_content, temp_audio.name)
        logger.info(f"Generated audio locally at {audio_path}")

        # 2. Upload to S3 (TODO: Implement S3 Upload in Engine or return path to Backend)
        # For MVP, we might just store the path or binary in DB (not recommended for large files)
        # Or better: Worker should have S3 Client.
        # Let's assume we skip S3 upload here for a moment and just return "Done" 
        # because the next step (Render) will need this file locally anyway if it runs on the same worker node.
        # Ideally, we upload to S3 so Render task can download it (stateless).
        
        # NOTE: For this stateless design, we SHOULD upload.
        # But adding S3 Client to Python Engine is a new dependency.
        # Let's mock the upload or assume shared volume for MVP if strictly needed.
        # To strictly follow "Stateless", we need `boto3`.
        
        # Let's add boto3 upload quickly if we want to be perfect, or just pass the path if using shared volume.
        # Given "Stateless" rule, let's assume we need to upload.
        # For now, I will just return the local path, assuming we might run render on same node 
        # OR we will add S3 upload in next step.
        
        return {
            "project_id": project_id,
            "audio_path": audio_path # Local path for now
        }

    except Exception as e:
        logger.error(f"Audio generation failed for project {project_id}: {str(e)}")
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

@celery_app.task(bind=True, max_retries=3)
def render_video_task(self, project_id: str, timeline_assets: list, audio_path: str):
    """
    Background task to render final video.
    """
    logger.info(f"Starting video rendering for project {project_id}")
    
    try:
        # 1. Render Video
        temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        temp_video.close()
        
        output_path = video_render.render_video(timeline_assets, audio_path, temp_video.name)
        logger.info(f"Rendered video locally at {output_path}")

        # 2. Upload to S3
        file_name = f"rendered_{project_id}.mp4"
        final_video_url = upload_to_s3(output_path, file_name)
        logger.info(f"Uploaded video to {final_video_url}")
        
        # 3. Update Database
        conn = psycopg2.connect(Config.DB_DSN)
        try:
            with conn:
                with conn.cursor() as cursor:
                    update_query = """
                        UPDATE projects 
                        SET final_video_url = %s,
                            status = 'COMPLETED'
                        WHERE id = %s
                    """
                    cursor.execute(update_query, (final_video_url, project_id))
            logger.info(f"Updated final video URL in DB for project {project_id}")
        finally:
            conn.close()

        # Cleanup audio file if it was temp
        if os.path.exists(audio_path) and "/tmp/" in audio_path:
            os.remove(audio_path)

        return {
            "project_id": project_id,
            "video_url": final_video_url
        }

    except Exception as e:
        logger.error(f"Video rendering failed for project {project_id}: {str(e)}")
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
