# attendance_bot/api/routers/__init__.py
from .auth import router as auth_router
from .users import router as users_router
from .attendance import router as attendance_router
from .leaves import router as leave_router
from .shifts import router as shift_router
from .reports import router as report_router
from .departments import router as department_router
from .dashboard import router as dashboard_router

__all__ = [
    "auth_router",
    "users_router",
    "attendance_router",
    "leave_router",
    "shift_router",
    "report_router",
    "department_router",
    "dashboard_router",
]
