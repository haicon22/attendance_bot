# attendance_bot/utils/helpers.py
import os
import random
import string
import re


def generate_random_password(length: int = 12) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = "".join(random.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in "!@#$%^&*" for c in password)):
            return password


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal."""
    filename = os.path.basename(filename)
    filename = re.sub(r"[^\w\.\-]", "_", filename)
    return filename


def chunk_list(lst, chunk_size):
    """Split list into chunks."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]


def calculate_overtime(start_time, end_time, shift_end_time) -> float:
    """Calculate overtime hours."""
    from datetime import datetime, timedelta

    if end_time <= shift_end_time:
        return 0.0

    overtime = end_time - shift_end_time
    return round(overtime.total_seconds() / 3600, 2)
