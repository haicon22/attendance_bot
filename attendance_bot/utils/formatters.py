# attendance_bot/utils/formatters.py
from datetime import datetime, timedelta


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime object to string."""
    if dt is None:
        return ""
    return dt.strftime(format_str)


def format_duration(seconds: int) -> str:
    """Format duration in seconds to human readable string."""
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}分钟"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}小时{minutes}分钟"


def format_leave_balance(days: float) -> str:
    """Format leave balance with proper decimal."""
    if days == int(days):
        return f"{int(days)}天"
    return f"{days:.1f}天"
