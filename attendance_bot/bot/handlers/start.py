# attendance_bot/bot/handlers/start.py
import logging

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from core.database import AsyncSessionLocal
from models import User, UserTelegramBinding
from bot.keyboards.main_menu import get_main_menu_keyboard
from bot.keyboards.auth_keyboard import get_binding_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    telegram_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User)
            .join(UserTelegramBinding)
            .where(
                UserTelegramBinding.telegram_id == telegram_id,
                UserTelegramBinding.is_active == True
            )
        )
        user = result.scalar_one_or_none()

        if user:
            # Update last interaction
            binding_result = await session.execute(
                select(UserTelegramBinding).where(
                    UserTelegramBinding.telegram_id == telegram_id
                )
            )
            binding = binding_result.scalar_one()
            from datetime import datetime
            binding.last_interaction = datetime.utcnow()
            await session.commit()

            await message.answer(
                f"👋 欢迎回来，<b>{user.full_name}</b>！\n"
                f"📋 工号: {user.employee_number}\n"
                f"🏢 部门: {user.department.name if user.department else '未分配'}\n\n"
                f"请选择您要进行的操作：",
                reply_markup=get_main_menu_keyboard(user.role)
            )
        else:
            await message.answer(
                "👋 欢迎使用企业考勤管理系统！\n\n"
                "🔐 您需要先绑定您的员工账号才能使用考勤功能。\n"
                "请点击下方按钮进行绑定：",
                reply_markup=get_binding_keyboard()
            )


@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "📖 <b>考勤机器人使用指南</b>\n\n"
        "<b>🕐 打卡功能</b>\n"
        "• /checkin - 上班打卡\n"
        "• /checkout - 下班打卡\n"
        "• /field - 外勤打卡\n\n"
        "<b>📋 请假功能</b>\n"
        "• /leave - 提交请假申请\n"
        "• /myleaves - 查看我的请假\n"
        "• /approvals - 审批请假（管理员）\n\n"
        "<b>👤 个人中心</b>\n"
        "• /profile - 查看个人信息\n"
        "• /attendance - 查看考勤记录\n"
        "• /summary - 考勤汇总\n\n"
        "<b>⚙️ 其他</b>\n"
        "• /start - 开始/主菜单\n"
        "• /help - 显示此帮助信息\n"
        "• /bind - 绑定/重新绑定账号"
    )
    await message.answer(help_text)
