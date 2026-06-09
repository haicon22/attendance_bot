# attendance_bot/tasks/attendance_tasks.py
import logging
from datetime import date, datetime, timedelta

from sqlalchemy import select, func, and_

from tasks.celery_app import celery_app
from core.database import AsyncSessionLocal
from models import User, AttendanceLog, AttendanceSummary, Shift, Holiday, LeaveRequest

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def generate_daily_summaries(self, target_date: str = None):
    """Generate attendance summaries for all users for a given date."""
    import asyncio

    async def _generate():
        if target_date:
            summary_date = date.fromisoformat(target_date)
        else:
            summary_date = date.today() - timedelta(days=1)

        async with AsyncSessionLocal() as session:
            # Get all active users
            result = await session.execute(
                select(User).where(User.status == "active")
            )
            users = result.scalars().all()

            for user in users:
                # Check if on leave
                leave_result = await session.execute(
                    select(LeaveRequest).where(
                        LeaveRequest.user_id == user.id,
                        LeaveRequest.status == "approved",
                        LeaveRequest.start_date <= summary_date,
                        LeaveRequest.end_date >= summary_date
                    )
                )
                is_on_leave = leave_result.scalar_one_or_none() is not None

                # Get attendance logs
                logs_result = await session.execute(
                    select(AttendanceLog).where(
                        AttendanceLog.user_id == user.id,
                        AttendanceLog.log_date == summary_date
                    )
                )
                logs = logs_result.scalars().all()

                check_in = next((l for l in logs if l.log_type == "check_in"), None)
                check_out = next((l for l in logs if l.log_type == "check_out"), None)
                field_work = [l for l in logs if l.log_type == "field_work"]

                # Determine status
                is_present = check_in is not None or len(field_work) > 0
                is_late = check_in and check_in.status == "late"
                is_early_leave = check_out and check_out.status == "early_leave"
                is_absent = not is_present and not is_on_leave

                # Update or create monthly summary
                month_summary_result = await session.execute(
                    select(AttendanceSummary).where(
                        AttendanceSummary.user_id == user.id,
                        AttendanceSummary.year == summary_date.year,
                        AttendanceSummary.month == summary_date.month
                    )
                )
                summary = month_summary_result.scalar_one_or_none()

                if not summary:
                    summary = AttendanceSummary(
                        user_id=user.id,
                        year=summary_date.year,
                        month=summary_date.month,
                    )
                    session.add(summary)

                # Update counts
                if is_present:
                    summary.present_days += 1
                if is_late:
                    summary.late_days += 1
                if is_early_leave:
                    summary.early_leave_days += 1
                if is_absent:
                    summary.absent_days += 1
                if field_work:
                    summary.field_work_days += 1
                if is_on_leave:
                    summary.leave_days += 1

                # Calculate overtime
                if check_out and check_out.status == "overtime":
                    shift_result = await session.execute(
                        select(Shift).where(Shift.id == user.shift_id)
                    )
                    shift = shift_result.scalar_one_or_none()
                    if shift:
                        from datetime import datetime
                        end_datetime = datetime.combine(summary_date, shift.end_time)
                        actual_end = check_out.log_time
                        overtime = (actual_end - end_datetime).total_seconds() / 3600
                        if overtime > 0:
                            summary.overtime_hours += round(overtime, 2)

            await session.commit()
            logger.info(f"Generated daily summaries for {len(users)} users on {summary_date}")

    try:
        asyncio.run(_generate())
        return {"status": "success", "date": target_date}
    except Exception as exc:
        logger.error(f"Failed to generate summaries: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task
def mark_absent_users(target_date: str = None):
    """Mark users as absent if they didn't check in by end of day."""
    import asyncio

    async def _mark():
        if target_date:
            check_date = date.fromisoformat(target_date)
        else:
            check_date = date.today() - timedelta(days=1)

        async with AsyncSessionLocal() as session:
            # Get active users who didn't check in
            result = await session.execute(
                select(User).where(
                    User.status == "active",
                    ~User.id.in_(
                        select(AttendanceLog.user_id).where(
                            AttendanceLog.log_date == check_date,
                            AttendanceLog.log_type.in_(["check_in", "field_work"])
                        )
                    )
                )
            )
            absent_users = result.scalars().all()

            for user in absent_users:
                # Check if on leave
                leave_result = await session.execute(
                    select(LeaveRequest).where(
                        LeaveRequest.user_id == user.id,
                        LeaveRequest.status == "approved",
                        LeaveRequest.start_date <= check_date,
                        LeaveRequest.end_date >= check_date
                    )
                )
                if leave_result.scalar_one_or_none():
                    continue  # Skip if on leave

                # Check if holiday
                holiday_result = await session.execute(
                    select(Holiday).where(Holiday.holiday_date == check_date)
                )
                if holiday_result.scalar_one_or_none():
                    continue  # Skip if holiday

                # Create absent record
                absent_log = AttendanceLog(
                    user_id=user.id,
                    log_type="check_in",
                    log_date=check_date,
                    log_time=datetime.combine(check_date, datetime.min.time()),
                    status="absent",
                )
                session.add(absent_log)

            await session.commit()
            logger.info(f"Marked {len(absent_users)} users as absent on {check_date}")

    asyncio.run(_mark())
    return {"status": "success", "date": target_date}
