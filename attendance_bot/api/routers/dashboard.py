# attendance_bot/api/routers/dashboard.py
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from api.middlewares.auth import get_current_user, require_role
from models import User, UserRole, AttendanceLog, Department, LeaveRequest

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(require_role(UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db)
):
    today = date.today()

    # Total employees
    total_result = await db.execute(select(func.count(User.id)).where(User.status == "active"))
    total_employees = total_result.scalar()

    # Today's check-ins
    checkin_result = await db.execute(
        select(func.count(func.distinct(AttendanceLog.user_id))).where(
            AttendanceLog.log_date == today,
            AttendanceLog.log_type == "check_in"
        )
    )
    today_checkins = checkin_result.scalar()

    # Today's late arrivals
    late_result = await db.execute(
        select(func.count(func.distinct(AttendanceLog.user_id))).where(
            AttendanceLog.log_date == today,
            AttendanceLog.status == "late"
        )
    )
    today_late = late_result.scalar()

    # Pending leave requests
    pending_leave_result = await db.execute(
        select(func.count(LeaveRequest.id)).where(LeaveRequest.status == "pending")
    )
    pending_leaves = pending_leave_result.scalar()

    # Absent today (active employees - checkins)
    absent_today = max(0, total_employees - today_checkins)

    return {
        "total_employees": total_employees,
        "today_checkins": today_checkins,
        "today_late": today_late,
        "absent_today": absent_today,
        "pending_leaves": pending_leaves,
        "attendance_rate": round(today_checkins / total_employees * 100, 2) if total_employees > 0 else 0,
    }


@router.get("/department-stats")
async def get_department_stats(
    current_user: User = Depends(require_role(UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db)
):
    today = date.today()

    result = await db.execute(
        select(
            Department.name,
            func.count(User.id).label("total"),
        )
        .join(User, User.department_id == Department.id)
        .where(User.status == "active")
        .group_by(Department.id)
    )
    dept_stats = []
    for row in result.all():
        dept_name, total = row

        # Get checkins for this department
        checkin_result = await db.execute(
            select(func.count(func.distinct(AttendanceLog.user_id))).where(
                AttendanceLog.log_date == today,
                AttendanceLog.log_type == "check_in"
            ).join(User).where(User.department_id == Department.id)
        )
        checkins = checkin_result.scalar()

        dept_stats.append({
            "department": dept_name,
            "total_employees": total,
            "today_checkins": checkins or 0,
            "attendance_rate": round((checkins or 0) / total * 100, 2) if total > 0 else 0,
        })

    return dept_stats
