# attendance_bot/api/routers/attendance.py
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.attendance_service import AttendanceService
from api.middlewares.auth import get_current_user, require_role
from models import User, UserRole

router = APIRouter()


class ClockInRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_address: Optional[str] = None
    notes: Optional[str] = None


class ClockOutRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_address: Optional[str] = None
    notes: Optional[str] = None


@router.post("/checkin")
async def clock_in(
    request: ClockInRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = AttendanceService(db)
    log = await service.clock_in(
        user_id=current_user.id,
        latitude=request.latitude,
        longitude=request.longitude,
        location_address=request.location_address,
        notes=request.notes,
    )
    await db.commit()
    return log.to_dict()


@router.post("/checkout")
async def clock_out(
    request: ClockOutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = AttendanceService(db)
    log = await service.clock_out(
        user_id=current_user.id,
        latitude=request.latitude,
        longitude=request.longitude,
        location_address=request.location_address,
        notes=request.notes,
    )
    await db.commit()
    return log.to_dict()


@router.get("/logs")
async def get_attendance_logs(
    user_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    department_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Regular users can only see their own logs
    if current_user.role == UserRole.EMPLOYEE and user_id and user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    if current_user.role == UserRole.EMPLOYEE:
        user_id = current_user.id

    service = AttendanceService(db)
    logs, total = await service.get_attendance_logs(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        department_id=department_id,
        status=status,
        page=page,
        page_size=page_size,
    )

    return {
        "items": [log.to_dict() for log in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/summary/{user_id}")
async def get_user_summary(
    user_id: int,
    summary_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role == UserRole.EMPLOYEE and user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    if summary_date is None:
        summary_date = date.today()

    service = AttendanceService(db)
    summary = await service.generate_daily_summary(user_id, summary_date)
    return summary
