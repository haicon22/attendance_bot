# attendance_bot/bot/keyboards/attendance_keyboard.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def get_clock_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 上班打卡", callback_data="clock:checkin"),
            InlineKeyboardButton(text="🔴 下班打卡", callback_data="clock:checkout"),
        ],
        [
            InlineKeyboardButton(text="🌍 外勤打卡", callback_data="clock:field"),
        ],
        [
            InlineKeyboardButton(text="📊 查看记录", callback_data="clock:records"),
        ],
    ])


def get_location_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 发送位置", request_location=True)],
            [KeyboardButton(text="❌ 取消")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_attendance_summary_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 本月", callback_data="attendance:month"),
            InlineKeyboardButton(text="📆 上月", callback_data="attendance:last_month"),
        ],
        [
            InlineKeyboardButton(text="📈 汇总", callback_data="attendance:summary"),
        ],
    ])
