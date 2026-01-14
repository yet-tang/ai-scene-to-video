from worker import celery_app
from vision import SceneDetector
from script_gen import ScriptGenerator
from audio_gen import AudioGenerator, _ffmpeg_concat_mp3
from video_render import VideoRenderer
from aliyun_client import AliyunClient
from sfx_library import SFXLibrary
from bgm_selector import BGMSelector
from agent_workflow import MultiAgentScriptGenerator
from config import Config
import json
import logging
import psycopg2
import re
import tempfile
import os
import boto3
import cv2
from moviepy.editor import VideoFileClip
import uuid
import urllib.request
import time
import math
from urllib.parse import urlparse
from celery.exceptions import Retry
import traceback
from datetime import datetime, timezone

# Configure logging
logger = logging.getLogger(__name__)

def _get_task_headers(request) -> dict:
    headers = getattr(request, "headers", None) or {}
    if not headers and hasattr(request, "get"):
        try:
            headers = request.get("headers") or {}
        except Exception:
            headers = {}
    if headers is None:
        headers = {}
    if isinstance(headers, dict):
        return headers
    try:
        return dict(headers)
    except Exception:
        return {}

def _retry_with_headers(task, *, exc: Exception, countdown: int):
    headers = _get_task_headers(getattr(task, "request", None))
    safe_headers = {}
    for k in ("request_id", "user_id"):
        v = headers.get(k)
        if v is None:
            continue
        safe_headers[k] = str(v)
    return task.retry(exc=exc, countdown=countdown, headers=safe_headers)

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

def _infer_suffix_from_url(url: str, default_suffix: str) -> str:
    try:
        path = urlparse(url).path or ""
        _, ext = os.path.splitext(path)
        if ext and len(ext) <= 8:
            return ext
    except Exception:
        pass
    return default_suffix

def _download_to_temp(video_url: str, *, suffix: str = ".mp4") -> str:
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
    
    temp_video = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
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

def _fetch_asset_source(asset_id: str) -> dict | None:
    conn = psycopg2.connect(Config.DB_DSN)
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT oss_url, storage_type, storage_bucket, storage_key, local_path
                    FROM assets
                    WHERE id = %s
                    """,
                    (asset_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return {
                    "oss_url": row[0],
                    "storage_type": row[1],
                    "storage_bucket": row[2],
                    "storage_key": row[3],
                    "local_path": row[4],
                }
    finally:
        conn.close()

def _get_video_duration_sec(video_url: str) -> float:
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

def _set_project_failed(
    project_id: str,
    *,
    task_name: str,
    step: str | None,
    task_id: str | None,
    request_id: str | None,
    exc: Exception,
):
    started = time.monotonic()
    error_log = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-20000:]
    conn = psycopg2.connect(Config.DB_DSN)
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE projects
                    SET status = 'FAILED',
                        error_log = %s,
                        error_task_id = %s,
                        error_request_id = %s,
                        error_step = %s,
                        error_at = %s
                    WHERE id = %s
                      AND status != 'COMPLETED'
                    """,
                    (
                        error_log,
                        (task_id or "")[:128] or None,
                        (request_id or "")[:128] or None,
                        (step or "")[:64] or None,
                        datetime.now(timezone.utc),
                        project_id,
                    ),
                )
        _log_exception(
            "db.project_status.failed",
            project_id=project_id,
            task_name=task_name,
            step=step,
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
aliyun_client = AliyunClient()
sfx_library = SFXLibrary()  # Initialize SFX library
video_render = VideoRenderer(aliyun_client=aliyun_client, sfx_library=sfx_library)  # Inject dependencies

@celery_app.task(bind=True, max_retries=3)
def analyze_video_task(self, project_id: str, asset_id: str, video_url: str):
    """
    Background task to analyze a video asset.
    """
    # (Original content of analyze_video_task)
    started = time.monotonic()
    attempt = int(getattr(self.request, "retries", 0) or 0) + 1
    asset_source = _fetch_asset_source(asset_id) or {"oss_url": video_url}

    _log_info(
        "task.start",
        task_name="analyze_video_task",
        project_id=project_id,
        asset_id=asset_id,
        url_host=_url_host(asset_source.get("oss_url") or video_url),
        attempt=attempt,
        retries=int(getattr(self.request, "retries", 0) or 0),
    )
    
    try:
        _advance_project_status(project_id)
        _log_info("step.start", step="download", project_id=project_id, asset_id=asset_id, url_host=_url_host(asset_source.get("oss_url") or video_url))
        local_video = video_render._download_temp(asset_source)
        cleanup_local_video = (asset_source.get("storage_type") or "").upper() != "LOCAL_FILE"
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
            
            if Config.SMART_SPLIT_STRATEGY == "qwen_video" and _is_http_url(asset_source.get("oss_url") or ""):
                 segments_text = detector.analyze_video_segments(asset_source.get("oss_url"))
                 segments_raw = _parse_model_json(segments_text)
                 segments = _coerce_segments(segments_raw)
                 _process_split_logic(
                     project_id,
                     asset_id,
                     asset_source.get("oss_url") or video_url,
                     segments,
                     local_video_path=local_video,
                 )
                 _advance_project_status(project_id)
                 if cleanup_local_video and os.path.exists(local_video): os.remove(local_video)
                 return {"project_id": project_id, "status": "split_completed", "segments": len(segments)}

            elif Config.SMART_SPLIT_STRATEGY == "hybrid":
                 # ... Hybrid Logic ...
                 shots = detector.detect_video_shots(local_video, threshold=Config.SCENE_DETECT_THRESHOLD)
                 if not shots: shots = [(0.0, duration_sec)]
                 
                 shot_frames = []
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

                     _process_split_logic(
                         project_id,
                         asset_id,
                         asset_source.get("oss_url") or video_url,
                         segments,
                         local_video_path=local_video,
                     )
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
        retries = int(getattr(self.request, "retries", 0) or 0)
        max_retries = int(getattr(self, "max_retries", 0) or 0)
        if retries >= max_retries:
            headers = getattr(self.request, "headers", {}) or {}
            _set_project_failed(
                project_id,
                task_name="analyze_video_task",
                step="analyze_video",
                task_id=getattr(self.request, "id", None),
                request_id=headers.get("request_id"),
                exc=e,
            )
            raise
        raise _retry_with_headers(self, exc=e, countdown=2 ** retries)

@celery_app.task(bind=True, max_retries=3)
def generate_script_task(self, project_id: str, house_info: dict, timeline_data: list):
    """
    Background task to generate video script using LLM.
    
    Includes quality gate: Opening hook strength validation.
    Phase 2-3: Multi-agent workflow for quality improvement.
    """
    started = time.monotonic()
    try:
        # Phase 2-3: Multi-Agent Script Generation (if enabled)
        if Config.MULTI_AGENT_ENABLED:
            try:
                logger.info(
                    "Using multi-agent workflow for script generation",
                    extra={"event": "script.multi_agent.enabled", "project_id": project_id}
                )
                
                # Initialize multi-agent generator
                multi_agent_gen = MultiAgentScriptGenerator(llm_client=None)  # Will use litellm internally
                
                # Generate script with multi-agent workflow
                final_script, metadata = multi_agent_gen.generate_script_with_multi_agent(
                    house_info=house_info,
                    timeline_data=timeline_data
                )
                
                script_content = final_script
                
                logger.info(
                    f"Multi-agent script generation completed",
                    extra={
                        "event": "script.multi_agent.complete",
                        "project_id": project_id,
                        "iterations": metadata['iterations'],
                        "quality_score": metadata['quality_score'],
                        "passed": metadata['passed']
                    }
                )
                
            except Exception as e:
                logger.warning(
                    f"Multi-agent script generation failed, falling back to standard generation: {e}",
                    extra={"event": "script.multi_agent.fallback", "project_id": project_id}
                )
                # Fallback to standard generation
                script_content = script_gen.generate_script(house_info, timeline_data)
        else:
            # Standard script generation
            script_content = script_gen.generate_script(house_info, timeline_data)

        # 2. Quality Gate: Validate Opening Hook Strength
        validation_result = _validate_opening_hook(script_content, house_info)
        
        if not validation_result['passed']:
            logger.warning(
                f"Opening hook validation failed: {validation_result['reason']}",
                extra={
                    "event": "script.hook_validation.failed",
                    "project_id": project_id,
                    "reason": validation_result['reason'],
                    "retry_attempt": int(getattr(self.request, "retries", 0) or 0)
                }
            )
            
            # Retry script generation with enhanced feedback
            if int(getattr(self.request, "retries", 0) or 0) < 2:
                raise _retry_with_headers(
                    self, 
                    exc=Exception(f"Hook validation failed: {validation_result['reason']}"),
                    countdown=1
                )
            else:
                # Max retries reached, log warning but proceed
                logger.warning(
                    f"Max retries reached for hook validation, proceeding with current script",
                    extra={"event": "script.hook_validation.max_retries", "project_id": project_id}
                )
        else:
            logger.info(
                f"Opening hook validation passed",
                extra={
                    "event": "script.hook_validation.passed",
                    "project_id": project_id,
                    "hook_strength": validation_result['strength']
                }
            )

        # 3. Update Database
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
        retries = int(getattr(self.request, "retries", 0) or 0)
        raise _retry_with_headers(self, exc=e, countdown=2 ** retries)

def _validate_opening_hook(script_content: str, house_info: dict) -> dict:
    """
    Validate opening hook strength based on viral video formula.
    
    Quality criteria:
    1. Must contain price (XXX万)
    2. Must contain location/community (from house_info)
    3. Must contain contrast/surprise element (居然/竟然/？)
    
    Returns:
        dict with keys:
        - passed: bool
        - reason: str (if failed)
        - strength: int (1-10, if passed)
    """
    try:
        data = json.loads(script_content)
        
        # Extract intro_text or first segment as hook
        hook_text = ""
        if isinstance(data, dict):
            # New format: use intro_card.headline or intro_text
            intro_card = data.get('intro_card', {})
            hook_text = intro_card.get('headline', '') if intro_card else data.get('intro_text', '')
            
            # Also check first segment if intro is missing
            if not hook_text:
                segments = data.get('segments', [])
                if segments:
                    hook_text = segments[0].get('text', '')
        elif isinstance(data, list) and data:
            # Old format: use first segment
            hook_text = data[0].get('text', '')
    except Exception:
        # Fallback: use first 50 characters
        hook_text = script_content[:50]
    
    if not hook_text:
        return {'passed': False, 'reason': 'No hook text found'}
    
    # Validation criteria
    has_price = bool(re.search(r'\d+万', hook_text))
    
    # Check location/community
    has_location = False
    community = house_info.get('community', '') or house_info.get('location', '')
    if community:
        has_location = community in hook_text
    else:
        # Fallback: check for common location patterns
        has_location = bool(re.search(r'[\u4e00-\u9fa5]{2,}区|[\u4e00-\u9fa5]{2,}路|[\u4e00-\u9fa5]{2,}苑|[\u4e00-\u9fa5]{2,}城', hook_text))
    
    # Check contrast/surprise element
    surprise_keywords = ['居然', '竟然', '？', '！', '绝了', '爱了', '谁能拒绝']
    has_surprise = any(keyword in hook_text for keyword in surprise_keywords)
    
    # Calculate strength (1-10)
    strength = 0
    if has_price:
        strength += 4
    if has_location:
        strength += 3
    if has_surprise:
        strength += 3
    
    # Minimum threshold: 7/10
    if strength >= 7:
        return {'passed': True, 'strength': strength}
    else:
        missing = []
        if not has_price:
            missing.append('价格')
        if not has_location:
            missing.append('位置')
        if not has_surprise:
            missing.append('反差/疑问')
        
        return {
            'passed': False,
            'reason': f"开场钩子缺少关键元素: {', '.join(missing)}（当前强度{strength}/10）",
            'hook_text': hook_text[:50]
        }

def _detect_video_style(script_content: str, timeline_assets: list) -> str:
    """
    检测视频风格（Phase 2-2新增）
    
    策略：
    1. 统计timeline_assets中emotion标签分布
    2. 根据主导情绪判断风格
    
    Returns:
        stunning/cozy/healing
    """
    emotion_distribution = _calculate_emotion_distribution(timeline_assets)
    
    if not emotion_distribution:
        return 'cozy'  # Default style
    
    # Find dominant emotion
    dominant_emotion = max(emotion_distribution, key=emotion_distribution.get)
    
    # Map emotion to video style
    if dominant_emotion in ['惊艳', '震撼', 'stunning']:
        return 'stunning'
    elif dominant_emotion in ['治愈', '阳光', 'healing']:
        return 'healing'
    else:
        return 'cozy'  # 温馨 is default

def _extract_keywords_from_script(script_content: str) -> list:
    """
    从脚本中提取关键词（Phase 2-2新增）
    
    Returns:
        List of keywords
    """
    keywords = []
    
    # Common real estate keywords
    keyword_patterns = [
        '江景', '湖景', '海景', '山景',
        '阳光', '采光', '通透',
        '温馨', '舒适', '优雅', '精致',
        '大空间', '开阔', '270度',
        '学区', '地铁', '商圈'
    ]
    
    # Extract from script content
    text_lower = script_content.lower()
    for keyword in keyword_patterns:
        if keyword in script_content:
            keywords.append(keyword)
    
    return keywords

def _calculate_emotion_distribution(timeline_assets: list) -> dict:
    """
    统计情绪分布（Phase 2-2新增）
    
    Returns:
        Dict of {emotion: count}
    """
    distribution = {}
    for asset in timeline_assets:
        emotion = asset.get('emotion', '普通')
        distribution[emotion] = distribution.get(emotion, 0) + 1
    return distribution

def _parse_and_align_segments(project_id: str, script_content: str):
    """
    Fetch assets, parse script (JSON/Text), and prepare for audio generation.
    
    Returns:
        Tuple of (segments, timeline_assets, intro_text, intro_card)
        - segments: List of dicts with text, duration, asset_id, oss_url
        - timeline_assets: List of asset metadata
        - intro_text: Opening voice-over text for intro (may be empty)
        - intro_card: Structured intro card data (headline, specs, highlights) or None
    """
    # Fetch assets to get durations
    conn = psycopg2.connect(Config.DB_DSN)
    timeline_assets = []
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, oss_url, storage_type, storage_bucket, storage_key, local_path, duration, scene_label 
                    FROM assets 
                    WHERE project_id = %s AND is_deleted = FALSE 
                    ORDER BY sort_order ASC
                """, (project_id,))
                rows = cursor.fetchall()
                for r in rows:
                    duration_val = float(r[6] or 0.0)
                    if duration_val <= 0:
                        duration_val = 5.0
                    timeline_assets.append({
                        "id": str(r[0]),
                        "oss_url": r[1],
                        "storage_type": r[2],
                        "storage_bucket": r[3],
                        "storage_key": r[4],
                        "local_path": r[5],
                        "duration": duration_val,
                        "scene_label": r[7]
                    })
    finally:
        conn.close()
        
    segments = []
    intro_text = ""  # 片头开场白
    intro_card = None  # 片头卡片结构化数据
    
    try:
        # Try parsing as JSON
        data = json.loads(script_content)
        
        # New format: { "intro_text": "...", "intro_card": {...}, "segments": [...] }
        if isinstance(data, dict) and "segments" in data:
            intro_text = data.get("intro_text", "")
            intro_card = data.get("intro_card")  # May be None for old scripts
            segment_list = data.get("segments", [])
            text_map = {item.get('asset_id'): item.get('text', '') for item in segment_list}
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
            return segments, timeline_assets, intro_text, intro_card
        
        # Old format: array of segments
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
            return segments, timeline_assets, intro_text, None  # Old format has no intro_card
    except Exception:
        pass
        
    # Fallback: Plain text split
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
            
    return segments, timeline_assets, intro_text, None  # Fallback has no intro_card

@celery_app.task(bind=True, max_retries=3)
def generate_audio_task(self, project_id: str, script_content: str):
    """
    Background task to generate TTS audio (preview).
    """
    started = time.monotonic()
    try:
        _set_project_status(project_id, "AUDIO_GENERATING", skip_if_status_in=("RENDERING", "COMPLETED"))

        # Prepare segments
        segments, _, _, _ = _parse_and_align_segments(project_id, script_content)
        
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
            headers = getattr(self.request, "headers", {}) or {}
            _set_project_failed(
                project_id,
                task_name="generate_audio_task",
                step="generate_audio",
                task_id=getattr(self.request, "id", None),
                request_id=headers.get("request_id"),
                exc=e,
            )
            raise
        raise _retry_with_headers(self, exc=e, countdown=2 ** retries)

@celery_app.task(bind=True, max_retries=12)
def render_video_task(self, project_id: str, _timeline_assets: list, _audio_path: str, bgm_url: str = None):
    """
    Background task to render final video.
    """
    started = time.monotonic()
    try:
        _set_project_status(project_id, "RENDERING", skip_if_status_in=("COMPLETED",))

        # 1. Fetch Script
        conn = psycopg2.connect(Config.DB_DSN)
        script_content = ""
        house_info = {}
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT script_content, title, description FROM projects WHERE id = %s", (project_id,))
                    row = cursor.fetchone()
                    if row:
                        script_content = row[0]
                        house_info = {'title': row[1] or '', 'description': row[2] or ''}
        finally:
            conn.close()

        # 2. Re-generate aligned audio segments locally
        segments, timeline_assets_db, intro_text, intro_card = _parse_and_align_segments(project_id, script_content)
        
        # Download BGM if provided
        bgm_path = None
        if bgm_url:
            try:
                bgm_suffix = _infer_suffix_from_url(bgm_url, ".mp3")
                bgm_path = _download_to_temp(bgm_url, suffix=bgm_suffix)
            except Exception as e:
                logger.warning(f"Failed to download BGM: {e}")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate aligned segments
            audio_map = audio_gen.generate_aligned_audio_segments(segments, temp_dir)
            
            # 3. Render Video
            temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            temp_video.close()
            
            # Pass script_segments for subtitle rendering (P0 Feature)
            output_path = video_render.render_video(
                timeline_assets_db, 
                audio_map, 
                temp_video.name, 
                bgm_path=bgm_path,
                script_segments=segments,  # Enable subtitle generation
                house_info=house_info,  # Enable intelligent AI enhancement
                audio_gen=audio_gen,  # Enable intro voice generation
                intro_text=intro_text,  # Use user-edited intro text
                intro_card=intro_card  # Pass structured intro card data
            )

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
            if bgm_path and os.path.exists(bgm_path) and not (bgm_url or "").startswith("file://"):
                os.remove(bgm_path)
            
        return {"project_id": project_id, "video_url": final_video_url}

    except Exception as e:
        if isinstance(e, Retry): raise
        retries = int(getattr(self.request, "retries", 0) or 0)
        max_retries = int(getattr(self, "max_retries", 0) or 0)
        if retries >= max_retries:
            headers = getattr(self.request, "headers", {}) or {}
            _set_project_failed(
                project_id,
                task_name="render_video_task",
                step="render_video",
                task_id=getattr(self.request, "id", None),
                request_id=headers.get("request_id"),
                exc=e,
            )
            raise
        raise _retry_with_headers(self, exc=e, countdown=2 ** retries)

@celery_app.task(bind=True, max_retries=3)
def render_pipeline_task(self, project_id: str, script_content: str, _timeline_assets: list, bgm_url: str = None):
    started = time.monotonic()
    try:
        _set_project_status(project_id, "AUDIO_GENERATING", skip_if_status_in=("COMPLETED",))
        
        segments, timeline_assets_db, intro_text, intro_card = _parse_and_align_segments(project_id, script_content)
        
        # Fetch house info for intelligent AI enhancement
        conn = psycopg2.connect(Config.DB_DSN)
        house_info = {}
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT title, description FROM projects WHERE id = %s", (project_id,))
                    row = cursor.fetchone()
                    if row:
                        house_info = {'title': row[0] or '', 'description': row[1] or ''}
        finally:
            conn.close()
        
        # Phase 2-2: BGM Intelligent Selection (if enabled)
        bgm_metadata = None
        bgm_path = None  # Initialize bgm_path to avoid UnboundLocalError
        
        if Config.BGM_AUTO_SELECT_ENABLED and not bgm_url:
            try:
                logger.info(
                    "Using BGM intelligent selection",
                    extra={"event": "bgm.auto_select.enabled", "project_id": project_id}
                )
                
                # Detect video style and emotion distribution
                video_style = _detect_video_style(script_content, timeline_assets_db)
                script_keywords = _extract_keywords_from_script(script_content)
                emotion_distribution = _calculate_emotion_distribution(timeline_assets_db)
                
                # Select BGM
                selector = BGMSelector()
                bgm_metadata = selector.select_bgm(
                    video_style=video_style,
                    script_keywords=script_keywords,
                    emotion_distribution=emotion_distribution
                )
                
                if bgm_metadata:
                    bgm_url_selected = bgm_metadata.get('url')
                    if bgm_url_selected:
                        try:
                            bgm_suffix = _infer_suffix_from_url(bgm_url_selected, ".mp3")
                            bgm_path = _download_to_temp(bgm_url_selected, suffix=bgm_suffix)
                            
                            logger.info(
                                f"BGM auto-selected: {bgm_metadata.get('id')}",
                                extra={
                                    "event": "bgm.auto_select.success",
                                    "project_id": project_id,
                                    "bgm_id": bgm_metadata.get('id'),
                                    "video_style": video_style
                                }
                            )
                        except Exception as e:
                            logger.warning(f"Failed to download auto-selected BGM: {e}")
                            bgm_metadata = None
                else:
                    logger.info("No suitable BGM found, continuing without BGM")
                    
            except Exception as e:
                logger.warning(
                    f"BGM auto-selection failed: {e}",
                    extra={"event": "bgm.auto_select.failed", "project_id": project_id}
                )
        
        # Download BGM if manually specified
        if not bgm_path and bgm_url:
            try:
                bgm_suffix = _infer_suffix_from_url(bgm_url, ".mp3")
                bgm_path = _download_to_temp(bgm_url, suffix=bgm_suffix)
            except Exception as e:
                logger.warning(f"Failed to download BGM: {e}")

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
            
            # Pass script_segments for subtitle rendering (P0 Feature)
            output_path = video_render.render_video(
                timeline_assets_db, 
                audio_map, 
                temp_video.name, 
                bgm_path=bgm_path,
                script_segments=segments,  # Enable subtitle generation
                house_info=house_info,  # Enable intelligent AI enhancement
                audio_gen=audio_gen,  # Enable intro voice generation
                intro_text=intro_text,  # Use user-edited intro text
                intro_card=intro_card,  # Pass structured intro card data
                bgm_metadata=bgm_metadata  # Phase 2-2: Pass BGM metadata for dynamic volume curve
            )
            
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
            if bgm_path and os.path.exists(bgm_path) and not (bgm_url or "").startswith("file://"):
                os.remove(bgm_path)
            
        return {
            "project_id": project_id,
            "audio_url": audio_url,
            "video_url": final_video_url
        }

    except Exception as e:
        if isinstance(e, Retry): raise
        retries = int(getattr(self.request, "retries", 0) or 0)
        max_retries = int(getattr(self, "max_retries", 0) or 0)
        if retries >= max_retries:
            headers = getattr(self.request, "headers", {}) or {}
            _set_project_failed(
                project_id,
                task_name="render_pipeline_task",
                step="render_pipeline",
                task_id=getattr(self.request, "id", None),
                request_id=headers.get("request_id"),
                exc=e,
            )
            raise
        raise _retry_with_headers(self, exc=e, countdown=2 ** retries)

@celery_app.task(bind=True)
def enhance_video_task(self, project_id: str, asset_id: str, prompt: str):
    """
    Apply Aliyun Video Repainting to a specific asset to enhance its visual style.
    """
    # Fetch asset source
    asset_source = _fetch_asset_source(asset_id)
    if not asset_source:
        raise ValueError(f"Asset {asset_id} not found")
        
    video_url = asset_source.get("oss_url")
    if not video_url:
         raise ValueError(f"Asset {asset_id} has no URL")
         
    try:
        # Use Aliyun Client
        new_video_url = aliyun_client.video_repainting(video_url, prompt)
        enhanced_local = _download_to_temp(new_video_url, suffix=".mp4")
        try:
            object_key = f"enhanced/{project_id}/{asset_id}/{uuid.uuid4()}.mp4"
            enhanced_public_url = upload_to_s3(enhanced_local, object_key, content_type="video/mp4")
        finally:
            if os.path.exists(enhanced_local):
                os.remove(enhanced_local)

        conn = psycopg2.connect(Config.DB_DSN)
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE assets SET oss_url = %s WHERE id = %s",
                        (enhanced_public_url, asset_id),
                    )
        finally:
            conn.close()

        return {"project_id": project_id, "asset_id": asset_id, "new_url": enhanced_public_url}
        
    except Exception as e:
        logger.error(f"Enhancement failed: {e}")
        # Note: We don't necessarily fail the project if enhancement fails, 
        # but we should log it.
        raise
