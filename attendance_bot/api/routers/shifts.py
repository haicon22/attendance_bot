# attendance_bot/api/routers/shifts.py
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from api.middlewares.auth import get_current_user, require_role
from models import User, UserRole, Shift, ShiftException

router = APIRouter()


class ShiftCreate(BaseModel):
    name: str
    shift_type: str = Field(..., pattern="^(fixed|rotating|custom)$")
    start_time: str  # HH:MM format
    end_time: str
    break_duration: int = 60
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    allowed_radius: int = 500
    gps_required: bool = True


class ShiftUpdate(BaseModel):
    name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    break_duration: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    allowed_radius: Optional[int] = None
    gps_required: Optional[bool] = None
    is_active: Optional[bool] = None


@router.post("")
async def create_shift(
    request: ShiftCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    from datetime import datetime

    shift = Shift(
        name=request.name,
        type=request.shift_type,
        start_time=datetime.strptime(request.start_time, "%H:%M").time(),
        end_time=datetime.strptime(request.end_time, "%H:%M").time(),
        break_duration=request.break_duration,
        latitude=request.latitude,
        longitude=request.longitude,
        allowed_radius=request.allowed_radius,
        gps_required=request.gps_required,
    )
    db.add(shift)
    await db.flush()
    return shift.to_dict()


@router.get("")
async def list_shifts(
    is_active: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Shift)
    if is_active is not None:
        query = query.where(Shift.is_active == is_active)

    from sqlalchemy import func
    count_query = select(func.count(Shift.id))
    if is_active is not None:
        count_query = count_query.where(Shift.is_active == is_active)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    shifts = result.scalars().all()

    return {
        "items": [s.to_dict() for s in shifts],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{shift_id}")
async def get_shift(
    shift_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Shift).where(Shift.id == shift_id))
    shift = result.scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    return shift.to_dict()


@router.put("/{shift_id}")
async def update_shift(
    shift_id: int,
    request: ShiftUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Shift).where(Shift.id == shift_id))
    shift = result.scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    update_data = request.model_dump(exclude_unset=True)

    if "start_time" in update_data:
        from datetime import datetime
        update_data["start_time"] = datetime.strptime(update_data["start_time"], "%H:%M").time()
    if "end_time" in update_data:
        from datetime import datetime
        update_data["end_time"] = datetime.strptime(update_data["end_time"], "%H:%M").time()

    for key, value in update_data.items():
        setattr(shift, key, value)

    await db.flush()
    return shift.to_dict()


@router.delete("/{shift_id}")
async def delete_shift(
    shift_id: int,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(delete(Shift).where(Shift.id == shift_id))
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Shift not found")
    return {"message": "Shift deleted successfully"}
