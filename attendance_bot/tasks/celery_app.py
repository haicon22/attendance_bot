# attendance_bot/tasks/celery_app.py
from celery import Celery
from config.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "attendance_bot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["tasks.attendance_tasks", "tasks.report_tasks", "tasks.notification_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.TZ,
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)
