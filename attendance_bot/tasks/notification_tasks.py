# attendance_bot/tasks/notification_tasks.py
import logging

from tasks.celery_app import celery_app
from core.database import AsyncSessionLocal
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)


@celery_app.task
def send_work_start_reminders():
    """Send work start reminders to all users."""
    import asyncio

    async def _send():
        async with AsyncSessionLocal() as session:
            service = NotificationService(session)
            await service.send_reminder_notifications()

    asyncio.run(_send())
    return {"status": "success"}


@celery_app.task
def send_daily_summaries():
    """Send daily attendance summaries to managers."""
    import asyncio

    async def _send():
        async with AsyncSessionLocal() as session:
            service = NotificationService(session)
            await service.send_daily_summary()

    asyncio.run(_send())
    return {"status": "success"}


@celery_app.task
def send_late_notifications():
    """Send late notifications to users who are late."""
    import asyncio
    from datetime import date, datetime, timedelta
    from sqlalchemy import select
    from models import AttendanceLog, User

    async def _send():
        async with AsyncSessionLocal() as session:
            today = date.today()
            now = datetime.now()

            # Get users who checked in late today
            result = await session.execute(
                select(AttendanceLog, User).join(User).where(
                    AttendanceLog.log_date == today,
                    AttendanceLog.status == "late"
                )
            )

            service = NotificationService(session)
            for log, user in result.all():
                message = (
                    f"⚠️ <b>迟到提醒</b>\n"
                    f"您今天于 {log.log_time.strftime('%H:%M:%S')} 打卡，已迟到。\n"
                    f"请注意准时上班。"
                )
                await service.create_notification(
                    user_id=user.id,
                    notification_type="alert",
                    title="迟到提醒",
                    content=message,
                )
                await service.send_telegram_notification(user.id, message)

    asyncio.run(_send())
    return {"status": "success"}
