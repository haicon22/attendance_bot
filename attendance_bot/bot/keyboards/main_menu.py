# attendance_bot/bot/keyboards/main_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from models import UserRole


def get_main_menu_keyboard(role: str = UserRole.EMPLOYEE) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="🟢 上班打卡", callback_data="menu:checkin"),
            InlineKeyboardButton(text="🔴 下班打卡", callback_data="menu:checkout"),
        ],
        [
            InlineKeyboardButton(text="🌍 外勤打卡", callback_data="menu:field"),
            InlineKeyboardButton(text="📝 请假申请", callback_data="menu:leave"),
        ],
        [
            InlineKeyboardButton(text="📊 考勤记录", callback_data="menu:attendance"),
            InlineKeyboardButton(text="👤 个人中心", callback_data="menu:profile"),
        ],
    ]

    if role in [UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        buttons.append([
            InlineKeyboardButton(text="📋 审批管理", callback_data="menu:approvals"),
            InlineKeyboardButton(text="👥 团队管理", callback_data="menu:team"),
        ])

    if role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        buttons.append([
            InlineKeyboardButton(text="⚙️ 系统管理", callback_data="menu:admin"),
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
