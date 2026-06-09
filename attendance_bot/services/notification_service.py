# attendance_bot/services/notification_service.py
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, Notification, UserTelegramBinding, AttendanceLog, Shift
from core.redis_client import RedisClient

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db: AsyncSession, redis: Optional[RedisClient] = None):
        self.db = db
        self.redis = redis

    async def create_notification(
        self,
        user_id: int,
        notification_type: str,
        title: str,
        content: str,
        channel: str = "telegram",
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            content=content,
            channel=channel,
            sent_at=datetime.utcnow(),
        )
        self.db.add(notification)
        await self.db.flush()
        return notification

    async def send_telegram_notification(
        self,
        user_id: int,
        message: str,
    ) -> bool:
        try:
            result = await self.db.execute(
                select(UserTelegramBinding).where(
                    UserTelegramBinding.user_id == user_id,
                    UserTelegramBinding.is_active == True
                )
            )
            binding = result.scalar_one_or_none()

            if not binding:
                logger.warning(f"No active Telegram binding for user {user_id}")
                return False

            # In production, use aiogram Bot to send message
            # from aiogram import Bot
            # bot = Bot(token=settings.BOT_TOKEN)
            # await bot.send_message(binding.telegram_id, message, parse_mode="HTML")

            logger.info(f"Would send to Telegram {binding.telegram_id}: {message[:100]}")
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False

    async def send_reminder_notifications(self):
        """Send daily reminders to users."""
        now = datetime.now()

        # Get users who haven't checked in yet and it's past their shift start time
        result = await self.db.execute(
            select(User, Shift).join(Shift).where(
                User.status == "active",
                Shift.start_time <= (now + timedelta(minutes=30)).time(),
                Shift.start_time > now.time(),
            )
        )

        for user, shift in result.all():
            # Check if already checked in
            today = now.date()
            checkin_result = await self.db.execute(
                select(AttendanceLog).where(
                    AttendanceLog.user_id == user.id,
                    AttendanceLog.log_type == "check_in",
                    AttendanceLog.log_date == today
                )
            )

            if not checkin_result.scalar_one_or_none():
                message = (
                    f"⏰ <b>上班提醒</b>\n"
                    f"您的班次 {shift.name} 将于 {shift.start_time.strftime('%H:%M')} 开始，\n"
                    f"请记得打卡！"
                )
                await self.create_notification(
                    user_id=user.id,
                    notification_type="reminder",
                    title="上班提醒",
                    content=message,
                )
                await self.send_telegram_notification(user.id, message)

    async def send_daily_summary(self):
        """Send daily attendance summary to managers."""
        from models import UserRole

        now = datetime.now()
        today = now.date()

        # Get all managers
        result = await self.db.execute(
            select(User).where(User.role.in_([UserRole.MANAGER, UserRole.ADMIN]))
        )
        managers = result.scalars().all()

        for manager in managers:
            if not manager.department_id:
                continue

            # Get department stats
            from sqlalchemy import func
            dept_result = await self.db.execute(
                select(
                    func.count(User.id).label("total"),
                ).where(
                    User.department_id == manager.department_id,
                    User.status == "active"
                )
            )
            total_employees = dept_result.scalar()

            checkin_result = await self.db.execute(
                select(func.count(func.distinct(AttendanceLog.user_id))).where(
                    AttendanceLog.log_date == today,
                    AttendanceLog.log_type == "check_in"
                ).join(User).where(User.department_id == manager.department_id)
            )
            checkins = checkin_result.scalar()

            absent = total_employees - (checkins or 0)

            message = (
                f"📊 <b>今日考勤汇总</b>\n"
                f"部门: {manager.department.name if manager.department else 'N/A'}\n"
                f"日期: {today}\n"
                f"总人数: {total_employees}\n"
                f"已打卡: {checkins or 0}\n"
                f"未打卡: {absent}\n"
                f"出勤率: {round((checkins or 0) / total_employees * 100, 1)}%"
            )

            await self.create_notification(
                user_id=manager.id,
                notification_type="summary",
                title="每日考勤汇总",
                content=message,
            )
            await self.send_telegram_notification(manager.id, message)

    async def send_approval_notification(self, leave_request_id: int):
        """Send notification to approver about pending leave request."""
        from models import LeaveRequest, Approval

        result = await self.db.execute(
            select(LeaveRequest, User, Approval).join(User).join(Approval)\
            .where(LeaveRequest.id == leave_request_id)
        )
        row = result.first()
        if not row:
            return

        request, requester, approval = row

        message = (
            f"📋 <b>新的请假申请待审批</b>\n\n"
            f"申请人: {requester.full_name}\n"
            f"类型: {request.leave_type.name}\n"
            f"时间: {request.start_date} ~ {request.end_date}\n"
            f"天数: {request.total_days} 天\n"
            f"原因: {request.reason[:100]}...\n\n"
            f"请使用 /approvals 查看详情。"
        )

        await self.create_notification(
            user_id=approval.approver_id,
            notification_type="approval",
            title="请假审批通知",
            content=message,
        )
        await self.send_telegram_notification(approval.approver_id, message)
