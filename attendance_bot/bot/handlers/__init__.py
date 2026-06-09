# attendance_bot/bot/handlers/__init__.py
from .start import router as start_router
from .attendance import router as attendance_router
from .leave import router as leave_router
from .profile import router as profile_router
from .admin import router as admin_router

__all__ = [
    "start_router",
    "attendance_router",
    "leave_router",
    "profile_router",
    "admin_router",
]
