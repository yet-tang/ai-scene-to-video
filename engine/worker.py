from celery import Celery, signals
from config import Config
import logging
import contextvars

# Context Var to hold Request ID and User ID
request_id_var = contextvars.ContextVar("request_id", default="-")
user_id_var = contextvars.ContextVar("user_id", default="-")

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        try:
            record.request_id = request_id_var.get()
            record.user_id = user_id_var.get()
        except LookupError:
            record.request_id = "-"
            record.user_id = "-"
        return True

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
    # Extract request_id from headers
    # Celery populates task.request.headers from the message headers
    headers = getattr(task.request, 'headers', {}) or {}
    req_id = headers.get('request_id', '-')
    request_id_var.set(req_id)

@signals.after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    logger.addFilter(RequestIdFilter())
    for handler in logger.handlers:
        handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [trace_id=%(request_id)s] %(name)s: %(message)s'))

@signals.after_setup_task_logger.connect
def setup_task_loggers(logger, *args, **kwargs):
    logger.addFilter(RequestIdFilter())
    for handler in logger.handlers:
        handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [trace_id=%(request_id)s] %(name)s: %(message)s'))

if __name__ == '__main__':
    celery_app.start()
