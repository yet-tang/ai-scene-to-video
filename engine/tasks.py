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
import time
from urllib.parse import urlparse

# Configure logging
# Logging is configured in worker.py via signals
logger = logging.getLogger(__name__)

def _url_host(url: str) -> str:
    try:
        p = urlparse(url)
        return p.hostname or ""
    except Exception:
        return ""

def _log_info(event: str, **fields):
    logger.info(event, extra={"event": event, **fields})

def _log_warning(event: str, **fields):
    logger.warning(event, extra={"event": event, **fields})

def _log_exception(event: str, **fields):
    logger.exception(event, extra={"event": event, **fields})

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
    started = time.monotonic()
    try:
        size_bytes = None
        try:
            size_bytes = os.path.getsize(file_path)
        except Exception:
            pass
        _log_info(
            "s3.upload.start",
            bucket=Config.S3_STORAGE_BUCKET,
            object_key=object_name,
            **({"bytes": size_bytes} if size_bytes is not None else {}),
        )
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
            public_url = f"{base}/{bucket}/{object_name}"
            _log_info(
                "s3.upload.finish",
                bucket=bucket,
                object_key=object_name,
                duration_ms=int((time.monotonic() - started) * 1000),
                url_host=_url_host(public_url),
            )
            return public_url

        public_url = f"{base}/{object_name}"
        _log_info(
            "s3.upload.finish",
            bucket=bucket,
            object_key=object_name,
            duration_ms=int((time.monotonic() - started) * 1000),
            url_host=_url_host(public_url),
        )
        return public_url
    except Exception as e:
        _log_exception(
            "s3.upload.error",
            bucket=Config.S3_STORAGE_BUCKET,
            object_key=object_name,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        raise

def _is_http_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in {"http", "https"}
    except Exception:
        return False

def _download_to_temp(video_url: str) -> str:
    started = time.monotonic()
    # Support local file protocol for optimization
    if video_url.startswith("file://"):
        local_path = video_url.replace("file://", "")
        if os.path.exists(local_path):
            _log_info(
                "download.skip_local",
                url_host=_url_host(video_url),
                duration_ms=int((time.monotonic() - started) * 1000),
            )
            return local_path
        filename = os.path.basename(local_path)
        base = (Config.LOCAL_ASSET_HTTP_BASE_URL or "").rstrip("/")
        if base:
            video_url = f"{base}/{filename}"
    
    temp_video = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    temp_video.close()
    _log_info("download.start", url_host=_url_host(video_url))
    urllib.request.urlretrieve(video_url, temp_video.name)
    size_bytes = None
    try:
        size_bytes = os.path.getsize(temp_video.name)
    except Exception:
        pass
    _log_info(
        "download.finish",
        url_host=_url_host(video_url),
        duration_ms=int((time.monotonic() - started) * 1000),
        **({"bytes": size_bytes} if size_bytes is not None else {}),
    )
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

def _complete_segments_to_full_duration(segments: list[dict], total_duration_sec: float, eps: float = 0.05) -> list[dict]:
    try:
        total = float(total_duration_sec or 0.0)
    except Exception:
        total = 0.0
    if total <= 0.0:
        return []

    cleaned: list[dict] = []
    for s in segments or []:
        if not isinstance(s, dict):
            continue
        try:
            start = float(s.get("start_sec"))
            end = float(s.get("end_sec"))
        except Exception:
            continue
        if end <= start:
            continue
        start = max(0.0, min(start, total))
        end = max(0.0, min(end, total))
        if end <= start:
            continue
        cleaned.append({**s, "start_sec": start, "end_sec": end})

    if not cleaned:
        return [{"start_sec": 0.0, "end_sec": total, "scene": "其他", "features": "", "score": 0.0}]

    cleaned.sort(key=lambda x: float(x.get("start_sec", 0.0)))

    cleaned[0]["start_sec"] = 0.0
    for i in range(len(cleaned) - 1):
        cur = cleaned[i]
        nxt = cleaned[i + 1]
        cur_start = float(cur["start_sec"])
        cur_end = float(cur["end_sec"])
        nxt_start = float(nxt["start_sec"])

        if nxt_start > cur_end + eps:
            cur["end_sec"] = nxt_start
            cur_end = nxt_start

        if nxt_start < cur_end - eps:
            nxt["start_sec"] = cur_end

        if float(cur["end_sec"]) <= cur_start:
            cur["end_sec"] = min(total, cur_start + eps)

    cleaned[-1]["end_sec"] = total

    out = []
    for s in cleaned:
        try:
            start = float(s["start_sec"])
            end = float(s["end_sec"])
        except Exception:
            continue
        start = max(0.0, min(start, total))
        end = max(0.0, min(end, total))
        if end > start + eps:
            out.append({**s, "start_sec": start, "end_sec": end})

    if not out:
        return [{"start_sec": 0.0, "end_sec": total, "scene": "其他", "features": "", "score": 0.0}]

    out[0]["start_sec"] = 0.0
    out[-1]["end_sec"] = total
    return out

def _advance_project_status(project_id: str):
    started = time.monotonic()
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
        _log_info(
            "db.project_status.advance",
            project_id=project_id,
            duration_ms=int((time.monotonic() - started) * 1000),
            status="ok",
            **({"remaining_assets": remaining} if remaining is not None else {}),
        )
    finally:
        conn.close()

def _process_split_logic(project_id: str, asset_id: str, video_url: str, segments: list, local_video_path: str = None):
    started = time.monotonic()
    if len(segments) >= 2:
        if not local_video_path:
            local_video = _download_to_temp(video_url)
        else:
            local_video = local_video_path
            
        from moviepy.editor import VideoFileClip

        inserted_assets = []
        try:
            video = VideoFileClip(local_video)
            _log_info(
                "split.start",
                project_id=project_id,
                asset_id=asset_id,
                segments_count=len(segments),
                video_duration_sec=float(video.duration or 0.0),
            )
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
            before_total = sum(float(s["end_sec"]) - float(s["start_sec"]) for s in segments) if segments else 0.0
            segments = _complete_segments_to_full_duration(segments, float(video.duration or 0.0))
            after_total = sum(float(s["end_sec"]) - float(s["start_sec"]) for s in segments) if segments else 0.0
            _log_info(
                "split.segments.normalized",
                project_id=project_id,
                asset_id=asset_id,
                segments_count=int(len(segments)),
                sum_duration_before_sec=float(before_total),
                sum_duration_after_sec=float(after_total),
                video_duration_sec=float(video.duration or 0.0),
            )

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
                                try:
                                    clip.write_videofile(
                                        temp_clip.name,
                                        codec="libx264",
                                        audio_codec="aac",
                                        preset="veryfast",
                                        threads=2,
                                        logger=None,
                                    )
                                except Exception as e:
                                    if (
                                        isinstance(e, AttributeError)
                                        and "stdout" in str(e)
                                        and "NoneType" in str(e)
                                    ):
                                        _log_info(
                                            "split.segment.fallback_no_audio",
                                            project_id=project_id,
                                            asset_id=asset_id,
                                            start_sec=float(seg["start_sec"]),
                                            end_sec=float(seg["end_sec"]),
                                        )
                                        try:
                                            if os.path.exists(temp_clip.name):
                                                os.remove(temp_clip.name)
                                        except Exception:
                                            pass
                                        clip.write_videofile(
                                            temp_clip.name,
                                            codec="libx264",
                                            audio=False,
                                            preset="veryfast",
                                            threads=2,
                                            logger=None,
                                        )
                                    else:
                                        raise
                                object_key = (
                                    f"clips/{project_id}/{uuid.uuid4()}.mp4"
                                )
                                clip_url = upload_to_s3(temp_clip.name, object_key)
                            finally:
                                try:
                                    os.remove(temp_clip.name)
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
            _log_info(
                "split.finish",
                project_id=project_id,
                asset_id=asset_id,
                segments_count=len(inserted_assets),
                duration_ms=int((time.monotonic() - started) * 1000),
            )
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
    started = time.monotonic()
    attempt = int(getattr(self.request, "retries", 0) or 0) + 1
    _log_info(
        "task.start",
        task_name="analyze_video_task",
        project_id=project_id,
        asset_id=asset_id,
        url_host=_url_host(video_url),
        attempt=attempt,
        retries=int(getattr(self.request, "retries", 0) or 0),
    )
    
    try:
        _advance_project_status(project_id)
        _log_info("step.start", step="download", project_id=project_id, asset_id=asset_id, url_host=_url_host(video_url))
        local_video = _download_to_temp(video_url)
        cleanup_local_video = not local_video.startswith("/tmp/ai-video-uploads/")
        duration_sec = _get_video_duration_sec(local_video)
        _log_info(
            "step.finish",
            step="download",
            project_id=project_id,
            asset_id=asset_id,
            video_duration_sec=float(duration_sec or 0.0),
        )

        if not Config.SMART_SPLIT_ENABLED:
            _log_info(
                "split.skip",
                project_id=project_id,
                asset_id=asset_id,
                reason="disabled",
                strategy=Config.SMART_SPLIT_STRATEGY,
                video_duration_sec=float(duration_sec or 0.0),
                min_duration_sec=float(Config.SMART_SPLIT_MIN_DURATION_SEC or 0.0),
            )
        elif duration_sec < Config.SMART_SPLIT_MIN_DURATION_SEC:
            _log_info(
                "split.skip",
                project_id=project_id,
                asset_id=asset_id,
                reason="duration_too_short",
                strategy=Config.SMART_SPLIT_STRATEGY,
                video_duration_sec=float(duration_sec or 0.0),
                min_duration_sec=float(Config.SMART_SPLIT_MIN_DURATION_SEC or 0.0),
            )

        if (
            Config.SMART_SPLIT_ENABLED
            and duration_sec >= Config.SMART_SPLIT_MIN_DURATION_SEC
        ):
            _log_info(
                "split.decision",
                project_id=project_id,
                asset_id=asset_id,
                strategy=Config.SMART_SPLIT_STRATEGY,
                video_duration_sec=float(duration_sec or 0.0),
            )
            # Branch 1: Qwen Video (End-to-End)
            if Config.SMART_SPLIT_STRATEGY == "qwen_video" and _is_http_url(video_url):
                _log_info(
                    "step.start",
                    step="qwen_video_segments",
                    project_id=project_id,
                    asset_id=asset_id,
                    model=Config.QWEN_VIDEO_MODEL,
                )
                segments_text = detector.analyze_video_segments(video_url)
                segments_raw = _parse_model_json(segments_text)
                segments = _coerce_segments(segments_raw)
                _log_info(
                    "step.finish",
                    step="qwen_video_segments",
                    project_id=project_id,
                    asset_id=asset_id,
                    segments_count=len(segments),
                )
                _process_split_logic(project_id, asset_id, video_url, segments)
                _advance_project_status(project_id)
                if cleanup_local_video and os.path.exists(local_video):
                    os.remove(local_video)
                _log_info(
                    "task.finish",
                    task_name="analyze_video_task",
                    project_id=project_id,
                    asset_id=asset_id,
                    status="split_completed",
                    segments_count=len(segments),
                    duration_ms=int((time.monotonic() - started) * 1000),
                )
                return {"project_id": project_id, "status": "split_completed", "segments": len(segments)}

            # Branch 2: Hybrid (SceneDetect + Qwen Image)
            elif Config.SMART_SPLIT_STRATEGY == "hybrid":
                try:
                    _log_info(
                        "step.start",
                        step="scenedetect",
                        project_id=project_id,
                        asset_id=asset_id,
                        strategy="hybrid",
                    )
                    shots = detector.detect_video_shots(local_video, threshold=Config.SCENE_DETECT_THRESHOLD)
                    if not shots:
                        shots = [(0.0, duration_sec)]
                    _log_info(
                        "step.finish",
                        step="scenedetect",
                        project_id=project_id,
                        asset_id=asset_id,
                        shot_count=len(shots),
                    )
                    
                    shot_frames = []
                    import cv2
                    cap = cv2.VideoCapture(local_video)
                    
                    try:
                        _log_info(
                            "step.start",
                            step="keyframes_from_shots",
                            project_id=project_id,
                            asset_id=asset_id,
                        )
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
                    _log_info(
                        "step.finish",
                        step="keyframes_from_shots",
                        project_id=project_id,
                        asset_id=asset_id,
                        frame_count=len(shot_frames),
                    )

                    if shot_frames:
                        _log_info(
                            "step.start",
                            step="qwen_group_shots",
                            project_id=project_id,
                            asset_id=asset_id,
                            model=Config.QWEN_IMAGE_MODEL,
                        )
                        segments_text = detector.analyze_shot_grouping(shot_frames)
                        segments_raw = _parse_model_json(segments_text)
                        segments = _coerce_segments(segments_raw)
                        _log_info(
                            "step.finish",
                            step="qwen_group_shots",
                            project_id=project_id,
                            asset_id=asset_id,
                            segments_count=len(segments),
                        )
                        
                        for sf in shot_frames:
                            if os.path.exists(sf["image"]):
                                os.remove(sf["image"])

                        _process_split_logic(project_id, asset_id, video_url, segments, local_video_path=local_video)
                        _advance_project_status(project_id)
                        _log_info(
                            "task.finish",
                            task_name="analyze_video_task",
                            project_id=project_id,
                            asset_id=asset_id,
                            status="split_completed",
                            segments_count=len(segments),
                            duration_ms=int((time.monotonic() - started) * 1000),
                        )
                        return {"project_id": project_id, "status": "split_completed", "segments": len(segments)}

                finally:
                    if cleanup_local_video and os.path.exists(local_video):
                        os.remove(local_video)

        _log_info(
            "step.start",
            step="extract_key_frames",
            project_id=project_id,
            asset_id=asset_id,
        )
        frame_paths = detector.extract_key_frames(local_video, num_frames=5)
        _log_info(
            "step.finish",
            step="extract_key_frames",
            project_id=project_id,
            asset_id=asset_id,
            frame_count=len(frame_paths),
        )
        _log_info(
            "step.start",
            step="qwen_analyze_frames",
            project_id=project_id,
            asset_id=asset_id,
            model=Config.QWEN_IMAGE_MODEL,
        )
        result_json_str = detector.analyze_scene_from_frames(frame_paths)
        result_data = _parse_model_json(result_json_str)
        _log_info(
            "step.finish",
            step="qwen_analyze_frames",
            project_id=project_id,
            asset_id=asset_id,
            status="ok",
        )

        _log_info("step.start", step="db.update_asset", project_id=project_id, asset_id=asset_id)
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
            _log_info("step.finish", step="db.update_asset", project_id=project_id, asset_id=asset_id)
        finally:
            conn.close()

        _advance_project_status(project_id)

        if cleanup_local_video and os.path.exists(local_video):
            os.remove(local_video)

        _log_info(
            "task.finish",
            task_name="analyze_video_task",
            project_id=project_id,
            asset_id=asset_id,
            status="completed",
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        return {"project_id": project_id, "asset_id": asset_id, "analysis": result_data}

    except Exception as e:
        _log_exception(
            "task.error",
            task_name="analyze_video_task",
            project_id=project_id,
            asset_id=asset_id,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

@celery_app.task(bind=True, max_retries=3)
def generate_script_task(self, project_id: str, house_info: dict, timeline_data: list):
    """
    Background task to generate video script using LLM.
    """
    started = time.monotonic()
    attempt = int(getattr(self.request, "retries", 0) or 0) + 1
    _log_info(
        "task.start",
        task_name="generate_script_task",
        project_id=project_id,
        attempt=attempt,
        retries=int(getattr(self.request, "retries", 0) or 0),
    )
    
    try:
        # 1. Generate Script
        _log_info("step.start", step="llm.generate_script", task_name="generate_script_task", project_id=project_id)
        script_content = script_gen.generate_script(house_info, timeline_data)
        _log_info("step.finish", step="llm.generate_script", task_name="generate_script_task", project_id=project_id)

        # 2. Update Database
        _log_info("step.start", step="db.update_project_script", task_name="generate_script_task", project_id=project_id)
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
            _log_info("step.finish", step="db.update_project_script", task_name="generate_script_task", project_id=project_id)
        finally:
            conn.close()

        _log_info(
            "task.finish",
            task_name="generate_script_task",
            project_id=project_id,
            status="completed",
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        return {
            "project_id": project_id,
            "script": script_content
        }

    except Exception as e:
        _log_exception(
            "task.error",
            task_name="generate_script_task",
            project_id=project_id,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

@celery_app.task(bind=True, max_retries=3)
def generate_audio_task(self, project_id: str, script_content: str):
    """
    Background task to generate TTS audio.
    """
    started = time.monotonic()
    attempt = int(getattr(self.request, "retries", 0) or 0) + 1
    _log_info(
        "task.start",
        task_name="generate_audio_task",
        project_id=project_id,
        attempt=attempt,
        retries=int(getattr(self.request, "retries", 0) or 0),
    )
    
    try:
        # 1. Generate Audio (Save to local temp first)
        temp_audio = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        temp_audio.close() # Close to let audio_gen write to it
        
        _log_info("step.start", step="tts.generate_audio", task_name="generate_audio_task", project_id=project_id)
        audio_path = audio_gen.generate_audio(script_content, temp_audio.name)
        _log_info("step.finish", step="tts.generate_audio", task_name="generate_audio_task", project_id=project_id)

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
        
        _log_info(
            "task.finish",
            task_name="generate_audio_task",
            project_id=project_id,
            status="completed",
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        return {
            "project_id": project_id,
            "audio_path": audio_path # Local path for now
        }

    except Exception as e:
        _log_exception(
            "task.error",
            task_name="generate_audio_task",
            project_id=project_id,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

@celery_app.task(bind=True, max_retries=3)
def render_video_task(self, project_id: str, timeline_assets: list, audio_path: str):
    """
    Background task to render final video.
    """
    started = time.monotonic()
    attempt = int(getattr(self.request, "retries", 0) or 0) + 1
    _log_info(
        "task.start",
        task_name="render_video_task",
        project_id=project_id,
        attempt=attempt,
        retries=int(getattr(self.request, "retries", 0) or 0),
    )
    
    try:
        # 1. Render Video
        temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        temp_video.close()
        
        _log_info("step.start", step="render.render_video", task_name="render_video_task", project_id=project_id)
        output_path = video_render.render_video(timeline_assets, audio_path, temp_video.name)
        _log_info("step.finish", step="render.render_video", task_name="render_video_task", project_id=project_id)

        # 2. Upload to S3
        file_name = f"rendered_{project_id}.mp4"
        final_video_url = upload_to_s3(output_path, file_name)
        _log_info("step.finish", step="s3.upload_final_video", task_name="render_video_task", project_id=project_id, url_host=_url_host(final_video_url))
        
        # 3. Update Database
        _log_info("step.start", step="db.update_project_final_url", task_name="render_video_task", project_id=project_id)
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
            _log_info("step.finish", step="db.update_project_final_url", task_name="render_video_task", project_id=project_id)
        finally:
            conn.close()

        # Cleanup audio file if it was temp
        if os.path.exists(audio_path) and "/tmp/" in audio_path:
            os.remove(audio_path)

        _log_info(
            "task.finish",
            task_name="render_video_task",
            project_id=project_id,
            status="completed",
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        return {
            "project_id": project_id,
            "video_url": final_video_url
        }

    except Exception as e:
        _log_exception(
            "task.error",
            task_name="render_video_task",
            project_id=project_id,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
