# attendance_bot/bot/handlers/profile.py
import logging
from datetime import date

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func, and_

from core.database import AsyncSessionLocal
from models import User, AttendanceLog, LeaveRequest, UserTelegramBinding
from services.attendance_service import AttendanceService

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    telegram_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User)
            .join(User.telegram_bindings)
            .where(UserTelegramBinding.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("❌ 您尚未绑定账号。")
            return

        # Get this month's attendance stats
        today = date.today()

        # Count attendance records
        attendance_result = await session.execute(
            select(func.count(AttendanceLog.id)).where(
                AttendanceLog.user_id == user.id,
                AttendanceLog.log_date >= date(today.year, today.month, 1)
            )
        )
        total_records = attendance_result.scalar()

        # Count late days
        late_result = await session.execute(
            select(func.count(func.distinct(AttendanceLog.log_date))).where(
                AttendanceLog.user_id == user.id,
                AttendanceLog.status == "late",
                AttendanceLog.log_date >= date(today.year, today.month, 1)
            )
        )
        late_days = late_result.scalar()

        # Count approved leaves
        leave_result = await session.execute(
            select(func.sum(LeaveRequest.total_days)).where(
                LeaveRequest.user_id == user.id,
                LeaveRequest.status == "approved",
                LeaveRequest.start_date >= date(today.year, today.month, 1)
            )
        )
        leave_days = leave_result.scalar() or 0

        text = (
            f"👤 <b>个人信息</b>\n\n"
            f"📋 工号: {user.employee_number}\n"
            f"👤 姓名: {user.full_name}\n"
            f"📧 邮箱: {user.email or '未设置'}\n"
            f"📱 电话: {user.phone or '未设置'}\n"
            f"🏢 部门: {user.department.name if user.department else '未分配'}\n"
            f"🕐 班次: {user.shift.name if user.shift else '未分配'}\n"
            f"🎭 角色: {user.role}\n\n"
            f"📊 <b>本月统计</b>\n"
            f"📝 考勤记录: {total_records} 条\n"
            f"⚠️ 迟到天数: {late_days} 天\n"
            f"🏖️ 请假天数: {leave_days} 天\n\n"
            f"🌴 年假余额: {user.annual_leave_balance} 天\n"
            f"🏥 病假余额: {user.sick_leave_balance} 天"
        )

        await message.answer(text)


@router.message(Command("summary"))
async def cmd_summary(message: Message):
    telegram_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User)
            .join(User.telegram_bindings)
            .where(UserTelegramBinding.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("❌ 您尚未绑定账号。")
            return

        today = date.today()
        service = AttendanceService(session)

        # Get last 5 days summary
        from datetime import timedelta
        text = f"📊 <b>考勤汇总 ({today.year}年{today.month}月)</b>\n\n"

        for i in range(4, -1, -1):
            check_date = today - timedelta(days=i)
            summary = await service.generate_daily_summary(user.id, check_date)

            emoji = "✅" if summary["is_present"] else "❌"
            if summary["is_late"]:
                emoji = "⚠️"

            check_in_time = summary["check_in"].strftime("%H:%M") if summary["check_in"] else "--:--"
            check_out_time = summary["check_out"].strftime("%H:%M") if summary["check_out"] else "--:--"

            text += (
                f"{emoji} <b>{check_date.strftime('%m-%d')}</b> "
                f"{check_in_time}-{check_out_time}\n"
            )

        await message.answer(text)
