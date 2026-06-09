# attendance_bot/bot/handlers/attendance.py
import logging
from datetime import date, datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, Location
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, and_

from core.database import AsyncSessionLocal
from core.security import SecurityManager
from models import User, AttendanceLog, Shift, UserTelegramBinding
from services.attendance_service import AttendanceService
from bot.keyboards.attendance_keyboard import (
    get_clock_keyboard,
    get_location_request_keyboard,
    get_attendance_summary_keyboard,
)

router = Router()
logger = logging.getLogger(__name__)


class AttendanceStates(StatesGroup):
    waiting_for_location = State()
    waiting_for_field_notes = State()


@router.message(Command("checkin"))
async def cmd_checkin(message: Message, state: FSMContext):
    telegram_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User)
            .join(User.telegram_bindings)
            .where(UserTelegramBinding.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("❌ 您尚未绑定账号，请先使用 /bind 进行绑定。")
            return

        # Check if already checked in today
        today = date.today()
        check_result = await session.execute(
            select(AttendanceLog).where(
                AttendanceLog.user_id == user.id,
                AttendanceLog.log_type == "check_in",
                AttendanceLog.log_date == today
            )
        )
        if check_result.scalar_one_or_none():
            await message.answer("⚠️ 您今天已经打过上班卡了！")
            return

        # Get shift info
        shift_result = await session.execute(
            select(Shift).where(Shift.id == user.shift_id)
        )
        shift = shift_result.scalar_one_or_none()

        if shift and shift.gps_required:
            await state.set_state(AttendanceStates.waiting_for_location)
            await state.update_data(action="checkin", user_id=user.id)
            await message.answer(
                f"📍 <b>上班打卡</b>\n"
                f"班次: {shift.name} ({shift.start_time.strftime('%H:%M')} - {shift.end_time.strftime('%H:%M')})\n\n"
                f"请发送您的位置信息以完成打卡：",
                reply_markup=get_location_request_keyboard()
            )
        else:
            # No GPS required, clock in directly
            service = AttendanceService(session)
            try:
                log = await service.clock_in(user.id)
                status_emoji = "✅" if log.status == "normal" else "⚠️"
                status_text = "正常" if log.status == "normal" else "迟到"
                await message.answer(
                    f"{status_emoji} <b>上班打卡成功</b>\n"
                    f"⏰ 时间: {log.log_time.strftime('%H:%M:%S')}\n"
                    f"📊 状态: {status_text}\n"
                    f"📅 日期: {log.log_date}"
                )
            except Exception as e:
                await message.answer(f"❌ 打卡失败: {str(e)}")


@router.message(AttendanceStates.waiting_for_location, F.location)
async def process_location(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("user_id")
    action = data.get("action")

    latitude = message.location.latitude
    longitude = message.location.longitude

    async with AsyncSessionLocal() as session:
        service = AttendanceService(session)
        try:
            if action == "checkin":
                log = await service.clock_in(
                    user_id=user_id,
                    latitude=latitude,
                    longitude=longitude,
                )
                status_emoji = "✅" if log.status == "normal" else "⚠️"
                status_text = "正常" if log.status == "normal" else "迟到"
                distance_text = f"\n📍 距离: {log.distance_from_office}m" if log.distance_from_office else ""

                await message.answer(
                    f"{status_emoji} <b>上班打卡成功</b>\n"
                    f"⏰ 时间: {log.log_time.strftime('%H:%M:%S')}\n"
                    f"📊 状态: {status_text}"
                    f"{distance_text}",
                    reply_markup=get_clock_keyboard()
                )
            elif action == "checkout":
                log = await service.clock_out(
                    user_id=user_id,
                    latitude=latitude,
                    longitude=longitude,
                )
                status_emoji = "✅" if log.status == "normal" else "⚠️"
                status_text = "正常" if log.status == "normal" else "早退"

                await message.answer(
                    f"{status_emoji} <b>下班打卡成功</b>\n"
                    f"⏰ 时间: {log.log_time.strftime('%H:%M:%S')}\n"
                    f"📊 状态: {status_text}",
                    reply_markup=get_clock_keyboard()
                )
            elif action == "field":
                await state.update_data(latitude=latitude, longitude=longitude)
                await state.set_state(AttendanceStates.waiting_for_field_notes)
                await message.answer("📝 请输入外勤备注信息（或发送 /skip 跳过）：")
                return
        except Exception as e:
            await message.answer(f"❌ 打卡失败: {str(e)}")

    await state.clear()


@router.message(Command("checkout"))
async def cmd_checkout(message: Message, state: FSMContext):
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

        # Check if checked in
        today = date.today()
        checkin_result = await session.execute(
            select(AttendanceLog).where(
                AttendanceLog.user_id == user.id,
                AttendanceLog.log_type == "check_in",
                AttendanceLog.log_date == today
            )
        )
        if not checkin_result.scalar_one_or_none():
            await message.answer("⚠️ 您今天还没有上班打卡，请先打卡后再下班。")
            return

        # Check if already checked out
        checkout_result = await session.execute(
            select(AttendanceLog).where(
                AttendanceLog.user_id == user.id,
                AttendanceLog.log_type == "check_out",
                AttendanceLog.log_date == today
            )
        )
        if checkout_result.scalar_one_or_none():
            await message.answer("⚠️ 您今天已经打过下班卡了！")
            return

        shift_result = await session.execute(
            select(Shift).where(Shift.id == user.shift_id)
        )
        shift = shift_result.scalar_one_or_none()

        if shift and shift.gps_required:
            await state.set_state(AttendanceStates.waiting_for_location)
            await state.update_data(action="checkout", user_id=user.id)
            await message.answer(
                f"📍 <b>下班打卡</b>\n"
                f"请发送您的位置信息：",
                reply_markup=get_location_request_keyboard()
            )
        else:
            service = AttendanceService(session)
            try:
                log = await service.clock_out(user.id)
                status_emoji = "✅" if log.status == "normal" else "⚠️"
                status_text = "正常" if log.status == "normal" else "早退"
                await message.answer(
                    f"{status_emoji} <b>下班打卡成功</b>\n"
                    f"⏰ 时间: {log.log_time.strftime('%H:%M:%S')}\n"
                    f"📊 状态: {status_text}"
                )
            except Exception as e:
                await message.answer(f"❌ 打卡失败: {str(e)}")


@router.message(Command("field"))
async def cmd_field_work(message: Message, state: FSMContext):
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

        await state.set_state(AttendanceStates.waiting_for_location)
        await state.update_data(action="field", user_id=user.id)
        await message.answer(
            "🌍 <b>外勤打卡</b>\n"
            "请发送您的当前位置：",
            reply_markup=get_location_request_keyboard()
        )


@router.message(AttendanceStates.waiting_for_field_notes)
async def process_field_notes(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("user_id")
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    notes = message.text if message.text != "/skip" else None

    async with AsyncSessionLocal() as session:
        service = AttendanceService(session)
        try:
            log = await service.field_work_clock(
                user_id=user_id,
                latitude=latitude,
                longitude=longitude,
                location_address=notes or "外勤地点",
                notes=notes,
            )
            await message.answer(
                f"✅ <b>外勤打卡成功</b>\n"
                f"⏰ 时间: {log.log_time.strftime('%H:%M:%S')}\n"
                f"📍 位置: {log.location_address or '已记录'}"
            )
        except Exception as e:
            await message.answer(f"❌ 打卡失败: {str(e)}")

    await state.clear()


@router.message(Command("attendance"))
async def cmd_attendance(message: Message):
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

        # Get recent attendance (last 7 days)
        from datetime import timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=6)

        service = AttendanceService(session)
        logs, _ = await service.get_attendance_logs(
            user_id=user.id,
            start_date=start_date,
            end_date=end_date,
            page_size=50
        )

        if not logs:
            await message.answer("📭 最近7天没有考勤记录。")
            return

        text = "📊 <b>最近7天考勤记录</b>\n\n"
        for log in logs:
            emoji = {
                "check_in": "🟢",
                "check_out": "🔴",
                "field_work": "🌍"
            }.get(log.log_type, "⚪")

            status_emoji = {
                "normal": "✅",
                "late": "⚠️",
                "early_leave": "⚠️",
                "overtime": "🔵",
                "field_work": "🌍"
            }.get(log.status, "⚪")

            type_text = {
                "check_in": "上班",
                "check_out": "下班",
                "field_work": "外勤"
            }.get(log.log_type, log.log_type)

            text += (
                f"{emoji} <b>{log.log_date}</b> {type_text}\n"
                f"   ⏰ {log.log_time.strftime('%H:%M:%S')} {status_emoji}\n"
            )

        await message.answer(text, reply_markup=get_attendance_summary_keyboard())
