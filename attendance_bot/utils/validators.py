# attendance_bot/utils/validators.py
import re


def validate_employee_number(employee_number: str) -> bool:
    """Validate employee number format."""
    pattern = r"^[A-Z0-9]{3,20}$"
    return bool(re.match(pattern, employee_number.upper()))


def validate_phone(phone: str) -> bool:
    """Validate phone number format (China)."""
    pattern = r"^1[3-9]\d{9}$"
    return bool(re.match(pattern, phone))


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))
