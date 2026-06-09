# attendance_bot/tasks/__init__.py
from .celery_app import celery_app
from .scheduled_tasks import setup_scheduler

__all__ = ["celery_app", "setup_scheduler"]
