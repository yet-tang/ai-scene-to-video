from celery import Celery, signals
from config import Config
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
)

@signals.task_prerun.connect
def on_task_prerun(task_id, task, *args, **kwargs):
    headers = getattr(task.request, 'headers', {}) or {}
    request_id_var.set(headers.get('request_id', '-'))
    user_id_var.set(headers.get('user_id', '-'))
    task_id_var.set(task_id or getattr(task.request, "id", "-") or "-")

@signals.after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    logger.addFilter(RequestIdFilter())
    for handler in logger.handlers:
        handler.setFormatter(JsonFormatter("ai-scene-engine"))

@signals.after_setup_task_logger.connect
def setup_task_loggers(logger, *args, **kwargs):
    logger.addFilter(RequestIdFilter())
    for handler in logger.handlers:
        handler.setFormatter(JsonFormatter("ai-scene-engine"))

if __name__ == '__main__':
    celery_app.start()
