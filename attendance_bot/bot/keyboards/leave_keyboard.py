# attendance_bot/bot/keyboards/leave_keyboard.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from models import LeaveType


def get_leave_type_keyboard(leave_types: list[LeaveType]) -> InlineKeyboardMarkup:
    buttons = []
    for lt in leave_types:
        buttons.append([
            InlineKeyboardButton(
                text=f"{lt.name} ({lt.default_days}天)",
                callback_data=f"leave_type:{lt.id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="❌ 取消", callback_data="leave:cancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_leave_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ 确认提交", callback_data="leave:confirm"),
            InlineKeyboardButton(text="❌ 取消", callback_data="leave:cancel"),
        ],
    ])


def get_leave_list_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 新申请", callback_data="leave:new"),
            InlineKeyboardButton(text="🔄 刷新", callback_data="leave:refresh"),
        ],
    ])
