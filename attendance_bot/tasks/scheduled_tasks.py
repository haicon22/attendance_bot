# attendance_bot/tasks/scheduled_tasks.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from tasks.celery_app import celery_app
from config.settings import get_settings

settings = get_settings()


def setup_scheduler():
    scheduler = AsyncIOScheduler(timezone=settings.TZ)

    # Work start reminder (8:30 AM)
    scheduler.add_job(
        lambda: celery_app.send_task("tasks.notification_tasks.send_work_start_reminders"),
        CronTrigger(hour=8, minute=30),
        id="work_start_reminder",
        replace_existing=True,
    )

    # Work end reminder (5:30 PM)
    scheduler.add_job(
        lambda: celery_app.send_task("tasks.notification_tasks.send_work_end_reminders"),
        CronTrigger(hour=17, minute=30),
        id="work_end_reminder",
        replace_existing=True,
    )

    # Late notifications (9:30 AM)
    scheduler.add_job(
        lambda: celery_app.send_task("tasks.notification_tasks.send_late_notifications"),
        CronTrigger(hour=9, minute=30),
        id="late_notifications",
        replace_existing=True,
    )

    # Daily summary to managers (6:00 PM)
    scheduler.add_job(
        lambda: celery_app.send_task("tasks.notification_tasks.send_daily_summaries"),
        CronTrigger(hour=18, minute=0),
        id="daily_summary",
        replace_existing=True,
    )

    # Generate daily summaries (midnight)
    scheduler.add_job(
        lambda: celery_app.send_task("tasks.attendance_tasks.generate_daily_summaries"),
        CronTrigger(hour=0, minute=5),
        id="daily_summaries",
        replace_existing=True,
    )

    # Mark absent users (11:59 PM)
    scheduler.add_job(
        lambda: celery_app.send_task("tasks.attendance_tasks.mark_absent_users"),
        CronTrigger(hour=23, minute=59),
        id="mark_absent",
        replace_existing=True,
    )

    # Cleanup old reports (weekly, Sunday at 3 AM)
    scheduler.add_job(
        lambda: celery_app.send_task("tasks.report_tasks.cleanup_old_reports"),
        CronTrigger(day_of_week="sun", hour=3, minute=0),
        id="cleanup_reports",
        replace_existing=True,
    )

    return scheduler
