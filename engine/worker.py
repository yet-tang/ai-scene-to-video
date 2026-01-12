from celery import Celery, signals
from config import Config
from kombu import Queue
import logging
import contextvars
import json
from datetime import datetime, timezone

# Context Var to hold Request ID and User ID
request_id_var = contextvars.ContextVar("request_id", default="-")
user_id_var = contextvars.ContextVar("user_id", default="-")
task_id_var = contextvars.ContextVar("task_id", default="-")

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        try:
            record.request_id = request_id_var.get()
            record.user_id = user_id_var.get()
            record.task_id = task_id_var.get()
        except LookupError:
            record.request_id = "-"
            record.user_id = "-"
            record.task_id = "-"
        return True

_request_id_filter = RequestIdFilter()

class JsonFormatter(logging.Formatter):
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "trace_id": getattr(record, "request_id", "-"),
            "user_id": getattr(record, "user_id", "-"),
            "task_id": getattr(record, "task_id", "-"),
            "logger": record.name,
            "message": record.getMessage(),
        }

        for k in (
            "event",
            "step",
            "task_name",
            "project_id",
            "asset_id",
            "duration_ms",
            "status",
            "attempt",
            "retries",
            "tts_engine",
            "tts_model",
            "voice",
            "tts_enable_ssml",
            "segments_count",
            "shot_count",
            "frame_count",
            "video_duration_sec",
            "min_duration_sec",
            "strategy",
            "reason",
            "model",
            "bucket",
            "object_key",
            "url_host",
            "bytes",
            "audio_path",
            "countdown_sec",
            "remaining_assets",
        ):
            if hasattr(record, k):
                payload[k] = getattr(record, k)

        if record.exc_info:
            payload["stacktrace"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)

celery_app = Celery(
    'ai_engine',
    broker=Config.REDIS_URL,
    backend=Config.REDIS_URL,
    include=['tasks']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_default_queue=Config.CELERY_QUEUE_NAME,
    task_queues=(Queue(Config.CELERY_QUEUE_NAME),),
    task_create_missing_queues=True,
)

@signals.task_prerun.connect
def on_task_prerun(sender=None, task_id=None, task=None, args=None, kwargs=None, **extras):
    t = task or sender
    req = getattr(t, "request", None)
    headers = getattr(req, "headers", None) or {}
    if not headers and hasattr(req, "get"):
        try:
            headers = req.get("headers") or {}
        except Exception:
            headers = {}
    request_id = (
        headers.get("request_id")
        or getattr(req, "request_id", None)
        or headers.get("correlation_id")
        or getattr(req, "correlation_id", None)
        or "-"
    )
    user_id = headers.get("user_id") or getattr(req, "user_id", None) or "-"
    request_id_var.set(request_id)
    user_id_var.set(user_id)
    task_id_var.set(task_id or getattr(req, "id", "-") or "-")

@signals.after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    for handler in logger.handlers:
        handler.addFilter(_request_id_filter)
        handler.setFormatter(JsonFormatter("ai-scene-engine"))

@signals.after_setup_task_logger.connect
def setup_task_loggers(logger, *args, **kwargs):
    for handler in logger.handlers:
        handler.addFilter(_request_id_filter)
        handler.setFormatter(JsonFormatter("ai-scene-engine"))

# Validate configuration on startup
try:
    from config import Config
    Config.validate()
except Exception as e:
    import logging
    logging.error(f"Configuration validation failed: {e}")

# Configure MoviePy to use ImageMagick for TextClip rendering
try:
    from moviepy.config import change_settings
    import subprocess
    import os
    
    # Try to find ImageMagick binary
    imagemagick_binary = None
    for cmd in ['magick', 'convert']:
        try:
            result = subprocess.run(['which', cmd], capture_output=True, text=True)
            if result.returncode == 0:
                imagemagick_binary = result.stdout.strip()
                break
        except Exception:
            pass
    
    if imagemagick_binary:
        change_settings({"IMAGEMAGICK_BINARY": imagemagick_binary})
        logging.info(f"MoviePy ImageMagick configured: {imagemagick_binary}")
    else:
        logging.warning("ImageMagick not found - subtitle rendering may fail")
except Exception as e:
    import logging
    logging.warning(f"Failed to configure MoviePy ImageMagick: {e}")

# Print version info on startup
import os
image_tag = os.getenv('IMAGE_TAG', 'unknown')
git_commit = os.getenv('GIT_COMMIT', 'unknown')
build_time = os.getenv('BUILD_TIME', 'unknown')
logging.info("=== Engine Version Info ===")
logging.info(f"Image Tag: {image_tag}")
logging.info(f"Git Commit: {git_commit}")
logging.info(f"Build Time: {build_time}")
logging.info("===========================")

if __name__ == '__main__':
    celery_app.start()
