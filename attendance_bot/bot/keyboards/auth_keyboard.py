# attendance_bot/bot/keyboards/auth_keyboard.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_binding_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔗 绑定账号", callback_data="auth:bind"),
        ],
        [
            InlineKeyboardButton(text="❓ 帮助", callback_data="auth:help"),
        ],
    ])
