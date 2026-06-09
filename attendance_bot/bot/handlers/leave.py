# attendance_bot/bot/handlers/leave.py
import logging
from datetime import date, datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select

from core.database import AsyncSessionLocal
from models import User, LeaveType, LeaveRequest, UserTelegramBinding
from services.leave_service import LeaveService
from bot.keyboards.leave_keyboard import (
    get_leave_type_keyboard,
    get_leave_confirm_keyboard,
    get_leave_list_keyboard,
)

router = Router()
logger = logging.getLogger(__name__)


class LeaveStates(StatesGroup):
    selecting_type = State()
    entering_start_date = State()
    entering_end_date = State()
    entering_reason = State()
    confirming = State()


@router.message(Command("leave"))
async def cmd_leave(message: Message, state: FSMContext):
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

        # Get leave types
        leave_types_result = await session.execute(
            select(LeaveType).where(LeaveType.is_active == True)
        )
        leave_types = leave_types_result.scalars().all()

        await state.set_state(LeaveStates.selecting_type)
        await message.answer(
            "📝 <b>提交请假申请</b>\n\n"
            "请选择请假类型：",
            reply_markup=get_leave_type_keyboard(leave_types)
        )


@router.callback_query(LeaveStates.selecting_type, F.data.startswith("leave_type:"))
async def process_leave_type(callback: CallbackQuery, state: FSMContext):
    leave_type_id = int(callback.data.split(":")[1])
    await state.update_data(leave_type_id=leave_type_id)
    await state.set_state(LeaveStates.entering_start_date)
    await callback.message.edit_text(
        "📅 请输入开始日期（格式: YYYY-MM-DD）：\n"
        "例如: 2024-06-15"
    )
    await callback.answer()


@router.message(LeaveStates.entering_start_date)
async def process_start_date(message: Message, state: FSMContext):
    try:
        start_date = datetime.strptime(message.text, "%Y-%m-%d").date()
        if start_date < date.today():
            await message.answer("❌ 开始日期不能是过去日期，请重新输入：")
            return

        await state.update_data(start_date=start_date)
        await state.set_state(LeaveStates.entering_end_date)
        await message.answer(
            "📅 请输入结束日期（格式: YYYY-MM-DD）：\n"
            "例如: 2024-06-17"
        )
    except ValueError:
        await message.answer("❌ 日期格式错误，请使用 YYYY-MM-DD 格式：")


@router.message(LeaveStates.entering_end_date)
async def process_end_date(message: Message, state: FSMContext):
    try:
        end_date = datetime.strptime(message.text, "%Y-%m-%d").date()
        data = await state.get_data()
        start_date = data.get("start_date")

        if end_date < start_date:
            await message.answer("❌ 结束日期不能早于开始日期，请重新输入：")
            return

        await state.update_data(end_date=end_date)
        await state.set_state(LeaveStates.entering_reason)
        await message.answer("📝 请输入请假原因：")
    except ValueError:
        await message.answer("❌ 日期格式错误，请使用 YYYY-MM-DD 格式：")


@router.message(LeaveStates.entering_reason)
async def process_reason(message: Message, state: FSMContext):
    await state.update_data(reason=message.text)
    data = await state.get_data()

    async with AsyncSessionLocal() as session:
        leave_type_result = await session.execute(
            select(LeaveType).where(LeaveType.id == data["leave_type_id"])
        )
        leave_type = leave_type_result.scalar_one()

        # Calculate working days
        from services.leave_service import LeaveService
        service = LeaveService(session)
        total_days = service._calculate_working_days(data["start_date"], data["end_date"])

        summary = (
            f"📋 <b>请假申请确认</b>\n\n"
            f"类型: {leave_type.name}\n"
            f"开始: {data['start_date']}\n"
            f"结束: {data['end_date']}\n"
            f"天数: {total_days} 天\n"
            f"原因: {data['reason']}\n\n"
            f"确认提交吗？"
        )

        await state.set_state(LeaveStates.confirming)
        await message.answer(summary, reply_markup=get_leave_confirm_keyboard())


@router.callback_query(LeaveStates.confirming, F.data == "leave:confirm")
async def confirm_leave(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    telegram_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User)
            .join(User.telegram_bindings)
            .where(UserTelegramBinding.telegram_id == telegram_id)
        )
        user = result.scalar_one()

        service = LeaveService(session)
        try:
            request = await service.create_leave_request(
                user_id=user.id,
                leave_type_id=data["leave_type_id"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                reason=data["reason"],
            )
            await callback.message.edit_text(
                f"✅ <b>请假申请已提交</b>\n"
                f"申请编号: #{request.id}\n"
                f"状态: 待审批\n"
                f"您可以通过 /myleaves 查看申请状态。"
            )
        except Exception as e:
            await callback.message.edit_text(f"❌ 提交失败: {str(e)}")

    await state.clear()
    await callback.answer()


@router.callback_query(LeaveStates.confirming, F.data == "leave:cancel")
async def cancel_leave(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ 请假申请已取消。")
    await state.clear()
    await callback.answer()


@router.message(Command("myleaves"))
async def cmd_my_leaves(message: Message):
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

        service = LeaveService(session)
        requests, total = await service.get_leave_requests(
            user_id=user.id,
            page_size=10
        )

        if not requests:
            await message.answer("📭 您没有请假记录。")
            return

        text = "📋 <b>我的请假记录</b>\n\n"
        for req in requests:
            status_emoji = {
                "pending": "⏳",
                "approved": "✅",
                "rejected": "❌",
                "cancelled": "🚫"
            }.get(req.status, "⚪")

            text += (
                f"{status_emoji} <b>#{req.id}</b> {req.leave_type.name}\n"
                f"   📅 {req.start_date} ~ {req.end_date} ({req.total_days}天)\n"
                f"   状态: {req.status}\n\n"
            )

        await message.answer(text, reply_markup=get_leave_list_keyboard())
