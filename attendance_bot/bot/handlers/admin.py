# attendance_bot/bot/handlers/admin.py
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func

from core.database import AsyncSessionLocal
from models import User, LeaveRequest, Approval, UserRole, UserTelegramBinding
from services.leave_service import LeaveService
from services.user_service import UserService

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("approvals"))
async def cmd_approvals(message: Message):
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

        if user.role not in [UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            await message.answer("❌ 您没有审批权限。")
            return

        # Get pending approvals for this user
        approval_result = await session.execute(
            select(Approval, LeaveRequest, User)
            .join(LeaveRequest, Approval.leave_request_id == LeaveRequest.id)
            .join(User, LeaveRequest.user_id == User.id)
            .where(
                Approval.approver_id == user.id,
                Approval.status == "pending"
            )
        )
        approvals = approval_result.all()

        if not approvals:
            await message.answer("📭 没有待审批的请假申请。")
            return

        text = "📋 <b>待审批请假申请</b>\n\n"
        for approval, request, requester in approvals:
            text += (
                f"📝 <b>#{request.id}</b> {requester.full_name}\n"
                f"   类型: {request.leave_type.name}\n"
                f"   时间: {request.start_date} ~ {request.end_date}\n"
                f"   天数: {request.total_days} 天\n"
                f"   原因: {request.reason[:50]}...\n"
                f"   审批级别: 第{approval.approval_level}级\n\n"
            )

        await message.answer(text)


@router.message(Command("team"))
async def cmd_team(message: Message):
    telegram_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User)
            .join(User.telegram_bindings)
            .where(UserTelegramBinding.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user or not user.department_id:
            await message.answer("❌ 您没有管理的部门。")
            return

        if user.role not in [UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            await message.answer("❌ 您没有查看团队权限。")
            return

        # Get team members
        service = UserService(session)
        members, total = await service.list_users(
            department_id=user.department_id,
            page_size=100
        )

        text = f"👥 <b>{user.department.name} - 团队成员</b> ({total}人)\n\n"
        for member in members:
            status_emoji = "🟢" if member.status == "active" else "🔴"
            text += f"{status_emoji} {member.full_name} ({member.employee_number})\n"

        await message.answer(text)
