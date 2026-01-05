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
import math
from urllib.parse import urlparse
from celery.exceptions import Retry

# Configure logging
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

def upload_to_s3(file_path: str, object_name: str, content_type: str = "video/mp4") -> str:
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
            content_type=content_type,
            **({"bytes": size_bytes} if size_bytes is not None else {}),
        )
        s3_client.upload_file(
            file_path,
            Config.S3_STORAGE_BUCKET,
            object_name,
            ExtraArgs={"ContentType": content_type},
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
            public_url = f"{base}/{object_name}"
        elif host.startswith(f"{bucket}."):
            public_url = f"{base}/{object_name}"
        elif (
            ".r2.cloudflarestorage.com" in host
            or ".amazonaws.com" in host
            or "localhost" in host
        ):
            public_url = f"{base}/{bucket}/{object_name}"
        else:
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

def _set_project_status(project_id: str, status: str, *, skip_if_status_in: tuple[str, ...] | None = None):
    started = time.monotonic()
    conn = psycopg2.connect(Config.DB_DSN)
    try:
        with conn:
            with conn.cursor() as cursor:
                if skip_if_status_in:
                    placeholders = ",".join(["%s"] * len(skip_if_status_in))
                    cursor.execute(
                        f"""
                        UPDATE projects
                        SET status = %s
                        WHERE id = %s
                          AND (status IS NULL OR status NOT IN ({placeholders}))
                        """,
                        (status, project_id, *skip_if_status_in),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE projects
                        SET status = %s
                        WHERE id = %s
                        """,
                        (status, project_id),
                    )
        _log_info(
            "db.project_status.set",
            project_id=project_id,
            status_value=status,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
    finally:
        conn.close()

def _get_project_status(project_id: str) -> str | None:
    conn = psycopg2.connect(Config.DB_DSN)
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT status FROM projects WHERE id = %s", (project_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                return row[0]
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
    # (Original content of analyze_video_task)
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
            _log_info("split.skip", project_id=project_id, asset_id=asset_id, reason="disabled")
        elif duration_sec < Config.SMART_SPLIT_MIN_DURATION_SEC:
            _log_info("split.skip", project_id=project_id, asset_id=asset_id, reason="duration_too_short")

        if (Config.SMART_SPLIT_ENABLED and duration_sec >= Config.SMART_SPLIT_MIN_DURATION_SEC):
            # ... Split Logic ...
            
            if Config.SMART_SPLIT_STRATEGY == "qwen_video" and _is_http_url(video_url):
                 segments_text = detector.analyze_video_segments(video_url)
                 segments_raw = _parse_model_json(segments_text)
                 segments = _coerce_segments(segments_raw)
                 _process_split_logic(project_id, asset_id, video_url, segments)
                 _advance_project_status(project_id)
                 if cleanup_local_video and os.path.exists(local_video): os.remove(local_video)
                 return {"project_id": project_id, "status": "split_completed", "segments": len(segments)}

            elif Config.SMART_SPLIT_STRATEGY == "hybrid":
                 # ... Hybrid Logic ...
                 shots = detector.detect_video_shots(local_video, threshold=Config.SCENE_DETECT_THRESHOLD)
                 if not shots: shots = [(0.0, duration_sec)]
                 
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
                             scale = 1024 / max(w, h) if max(w, h) > 1024 else 1.0
                             if scale != 1.0: frame = cv2.resize(frame, None, fx=scale, fy=scale)
                             cv2.imwrite(temp_img.name, frame)
                             shot_frames.append({"start": start, "end": end, "image": temp_img.name})
                             temp_img.close()
                 finally:
                     cap.release()

                 if shot_frames:
                     segments_text = detector.analyze_shot_grouping(shot_frames)
                     segments_raw = _parse_model_json(segments_text)
                     segments = _coerce_segments(segments_raw)
                     
                     for sf in shot_frames:
                         if os.path.exists(sf["image"]): os.remove(sf["image"])

                     _process_split_logic(project_id, asset_id, video_url, segments, local_video_path=local_video)
                     _advance_project_status(project_id)
                     if cleanup_local_video and os.path.exists(local_video): os.remove(local_video)
                     return {"project_id": project_id, "status": "split_completed", "segments": len(segments)}

                 if cleanup_local_video and os.path.exists(local_video): os.remove(local_video)

        # Fallback single frame analysis
        frame_paths = detector.extract_key_frames(local_video, num_frames=5)
        result_json_str = detector.analyze_scene_from_frames(frame_paths)
        result_data = _parse_model_json(result_json_str)
        
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
                        (result_data.get("scene", "unknown"), float(result_data.get("score", 0.0) or 0.0), float(duration_sec or 0.0), asset_id),
                    )
        finally:
            conn.close()

        _advance_project_status(project_id)
        if cleanup_local_video and os.path.exists(local_video): os.remove(local_video)
        return {"project_id": project_id, "asset_id": asset_id, "analysis": result_data}

    except Exception as e:
        _log_exception("task.error", task_name="analyze_video_task", project_id=project_id, asset_id=asset_id)
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

@celery_app.task(bind=True, max_retries=3)
def generate_script_task(self, project_id: str, house_info: dict, timeline_data: list):
    """
    Background task to generate video script using LLM.
    """
    started = time.monotonic()
    try:
        # 1. Generate Script
        script_content = script_gen.generate_script(house_info, timeline_data)

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
        finally:
            conn.close()

        return {"project_id": project_id, "script": script_content}
    except Exception as e:
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

def _parse_and_align_segments(project_id: str, script_content: str):
    """
    Fetch assets, parse script (JSON/Text), and prepare for audio generation.
    """
    # Fetch assets to get durations
    conn = psycopg2.connect(Config.DB_DSN)
    timeline_assets = []
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, oss_url, duration, scene_label 
                    FROM assets 
                    WHERE project_id = %s AND is_deleted = FALSE 
                    ORDER BY sort_order ASC
                """, (project_id,))
                rows = cursor.fetchall()
                for r in rows:
                    duration_val = float(r[2] or 0.0)
                    if duration_val <= 0:
                        duration_val = 5.0
                    timeline_assets.append({
                        "id": str(r[0]),
                        "oss_url": r[1],
                        "duration": duration_val,
                        "scene_label": r[3]
                    })
    finally:
        conn.close()
        
    segments = []
    try:
        # Try parsing as JSON
        data = json.loads(script_content)
        if isinstance(data, list):
            text_map = {item.get('asset_id'): item.get('text', '') for item in data}
            for asset in timeline_assets:
                aid = asset.get('id')
                dur = float(asset.get('duration', 5.0))
                text = text_map.get(aid, '')
                segments.append({
                    'text': text,
                    'duration': dur,
                    'asset_id': aid,
                    'oss_url': asset.get('oss_url')
                })
            return segments, timeline_assets
    except Exception:
        pass
        
    # Fallback: Plain text split
    import re
    sentences = re.split(r'([。！？.!?])', script_content)
    clean_sentences = []
    current = ""
    for s in sentences:
        if s in "。！？.!?":
            current += s
            clean_sentences.append(current)
            current = ""
        else:
            current = s
    if current: clean_sentences.append(current)
    clean_sentences = [s for s in clean_sentences if s.strip()]
    
    count = len(timeline_assets)
    if count > 0:
        per_clip = math.ceil(len(clean_sentences) / count)
        for i, asset in enumerate(timeline_assets):
            start = i * per_clip
            end = min((i + 1) * per_clip, len(clean_sentences))
            chunk = "".join(clean_sentences[start:end])
            segments.append({
                'text': chunk,
                'duration': float(asset.get('duration', 5.0)),
                'asset_id': asset.get('id'),
                'oss_url': asset.get('oss_url')
            })
            
    return segments, timeline_assets

@celery_app.task(bind=True, max_retries=3)
def generate_audio_task(self, project_id: str, script_content: str):
    """
    Background task to generate TTS audio (preview).
    """
    started = time.monotonic()
    try:
        _set_project_status(project_id, "AUDIO_GENERATING", skip_if_status_in=("RENDERING", "COMPLETED"))

        # Prepare segments
        segments, _ = _parse_and_align_segments(project_id, script_content)
        
        # Temp dir for segments
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate aligned segments
            audio_map = audio_gen.generate_aligned_audio_segments(segments, temp_dir)
            
            # Concat for preview
            preview_path = f"/tmp/{project_id}_preview.mp3"
            sorted_files = []
            for seg in segments:
                aid = seg.get('asset_id')
                if aid in audio_map:
                    sorted_files.append(audio_map[aid])
            
            from audio_gen import _ffmpeg_concat_mp3
            if sorted_files:
                _ffmpeg_concat_mp3(sorted_files, preview_path)
            else:
                # Should not happen
                pass
                
            # Upload preview
            file_name = f"{project_id}.mp3"
            audio_url = upload_to_s3(preview_path, file_name, content_type="audio/mpeg")
            
            # Update DB
            conn = psycopg2.connect(Config.DB_DSN)
            try:
                with conn:
                    with conn.cursor() as cursor:
                        update_query = """
                            UPDATE projects 
                            SET audio_url = %s,
                                status = 'AUDIO_GENERATED'
                            WHERE id = %s
                        """
                        cursor.execute(update_query, (audio_url, project_id))
            finally:
                conn.close()
            
            if os.path.exists(preview_path): os.remove(preview_path)

        return {"project_id": project_id, "audio_url": audio_url}

    except Exception as e:
        if isinstance(e, Retry): raise
        retries = int(getattr(self.request, "retries", 0) or 0)
        max_retries = int(getattr(self, "max_retries", 0) or 0)
        if retries >= max_retries:
            _set_project_status(project_id, "FAILED", skip_if_status_in=("COMPLETED",))
            raise
        raise self.retry(exc=e, countdown=2 ** retries)

@celery_app.task(bind=True, max_retries=12)
def render_video_task(self, project_id: str, _timeline_assets: list, _audio_path: str):
    """
    Background task to render final video.
    """
    started = time.monotonic()
    try:
        _set_project_status(project_id, "RENDERING", skip_if_status_in=("COMPLETED",))

        # 1. Fetch Script
        conn = psycopg2.connect(Config.DB_DSN)
        script_content = ""
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT script_content FROM projects WHERE id = %s", (project_id,))
                    row = cursor.fetchone()
                    if row: script_content = row[0]
        finally:
            conn.close()

        # 2. Re-generate aligned audio segments locally
        segments, timeline_assets_db = _parse_and_align_segments(project_id, script_content)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate aligned segments
            audio_map = audio_gen.generate_aligned_audio_segments(segments, temp_dir)
            
            # 3. Render Video
            temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            temp_video.close()
            
            output_path = video_render.render_video(timeline_assets_db, audio_map, temp_video.name)

            # 4. Upload
            file_name = f"rendered_{project_id}.mp4"
            final_video_url = upload_to_s3(output_path, file_name)
            
            # 5. Update DB
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
            finally:
                conn.close()

            if os.path.exists(output_path): os.remove(output_path)
            
        return {"project_id": project_id, "video_url": final_video_url}

    except Exception as e:
        if isinstance(e, Retry): raise
        retries = int(getattr(self.request, "retries", 0) or 0)
        max_retries = int(getattr(self, "max_retries", 0) or 0)
        if retries >= max_retries:
            _set_project_status(project_id, "FAILED", skip_if_status_in=("COMPLETED",))
            raise
        raise self.retry(exc=e, countdown=2 ** retries)

@celery_app.task(bind=True, max_retries=3)
def render_pipeline_task(self, project_id: str, script_content: str, _timeline_assets: list):
    started = time.monotonic()
    try:
        _set_project_status(project_id, "AUDIO_GENERATING", skip_if_status_in=("COMPLETED",))
        
        segments, timeline_assets_db = _parse_and_align_segments(project_id, script_content)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Audio
            audio_map = audio_gen.generate_aligned_audio_segments(segments, temp_dir)
            
            # Concat preview
            preview_path = f"/tmp/{project_id}_preview.mp3"
            sorted_files = []
            for seg in segments:
                aid = seg.get('asset_id')
                if aid in audio_map:
                    sorted_files.append(audio_map[aid])
            
            from audio_gen import _ffmpeg_concat_mp3
            if sorted_files:
                _ffmpeg_concat_mp3(sorted_files, preview_path)
                
            audio_url = upload_to_s3(preview_path, f"{project_id}.mp3", content_type="audio/mpeg")
            
             # Update DB with audio_url
            conn = psycopg2.connect(Config.DB_DSN)
            try:
                with conn:
                    with conn.cursor() as cursor:
                        update_query = """
                            UPDATE projects 
                            SET audio_url = %s,
                                status = 'AUDIO_GENERATED'
                            WHERE id = %s
                        """
                        cursor.execute(update_query, (audio_url, project_id))
            finally:
                conn.close()

            # Render
            _set_project_status(project_id, "RENDERING", skip_if_status_in=("COMPLETED",))
            
            temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            temp_video.close()
            
            output_path = video_render.render_video(timeline_assets_db, audio_map, temp_video.name)
            
            final_video_url = upload_to_s3(output_path, f"rendered_{project_id}.mp4")
            
            # Update DB
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
            finally:
                conn.close()
                
            if os.path.exists(preview_path): os.remove(preview_path)
            if os.path.exists(output_path): os.remove(output_path)
            
        return {
            "project_id": project_id,
            "audio_url": audio_url,
            "video_url": final_video_url
        }

    except Exception as e:
        if isinstance(e, Retry): raise
        _set_project_status(project_id, "FAILED", skip_if_status_in=("COMPLETED",))
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
