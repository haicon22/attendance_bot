# attendance_bot/services/attendance_service.py
from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import SecurityManager
from core.redis_client import RedisClient
from models import (
    User, AttendanceLog, Shift, ShiftException, Holiday, 
    LeaveRequest, AttendanceSummary
)


class AttendanceService:
    def __init__(self, db: AsyncSession, redis: Optional[RedisClient] = None):
        self.db = db
        self.redis = redis
        self.security = SecurityManager()

    async def get_user_shift(self, user_id: int, check_date: date = None) -> Optional[Shift]:
        if check_date is None:
            check_date = date.today()

        # Get user's assigned shift for the date
        from models import UserShift
        result = await self.db.execute(
            select(Shift)
            .join(UserShift)
            .where(
                UserShift.user_id == user_id,
                UserShift.is_active == True,
                UserShift.effective_from <= check_date,
                (UserShift.effective_to >= check_date) | (UserShift.effective_to.is_(None))
            )
            .order_by(UserShift.effective_from.desc())
        )
        shift = result.scalar_one_or_none()

        if not shift:
            # Fallback to user's default shift
            result = await self.db.execute(
                select(Shift)
                .join(User)
                .where(User.id == user_id)
            )
            shift = result.scalar_one_or_none()

        return shift

    async def check_shift_exception(self, shift_id: int, check_date: date) -> Optional[ShiftException]:
        result = await self.db.execute(
            select(ShiftException).where(
                ShiftException.shift_id == shift_id,
                ShiftException.exception_date == check_date
            )
        )
        return result.scalar_one_or_none()

    async def is_holiday(self, check_date: date) -> bool:
        result = await self.db.execute(
            select(Holiday).where(Holiday.holiday_date == check_date)
        )
        return result.scalar_one_or_none() is not None

    async def is_on_leave(self, user_id: int, check_date: date) -> bool:
        result = await self.db.execute(
            select(LeaveRequest).where(
                LeaveRequest.user_id == user_id,
                LeaveRequest.status == "approved",
                LeaveRequest.start_date <= check_date,
                LeaveRequest.end_date >= check_date
            )
        )
        return result.scalar_one_or_none() is not None

    async def calculate_distance_from_office(
        self, 
        user_lat: float, 
        user_lon: float, 
        shift: Shift
    ) -> float:
        if not shift.latitude or not shift.longitude:
            return 0
        return self.security.calculate_distance(
            user_lat, user_lon, float(shift.latitude), float(shift.longitude)
        )

    async def check_duplicate_clock_in(self, user_id: int, log_type: str, check_date: date) -> bool:
        result = await self.db.execute(
            select(AttendanceLog).where(
                AttendanceLog.user_id == user_id,
                AttendanceLog.log_type == log_type,
                AttendanceLog.log_date == check_date
            )
        )
        return result.scalar_one_or_none() is not None

    async def clock_in(
        self,
        user_id: int,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        location_address: Optional[str] = None,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        photo_url: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> AttendanceLog:
        today = date.today()
        now = datetime.now()

        # Check if already clocked in today
        if await self.check_duplicate_clock_in(user_id, "check_in", today):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already checked in today"
            )

        # Check if on leave
        if await self.is_on_leave(user_id, today):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are on leave today"
            )

        # Get user's shift
        shift = await self.get_user_shift(user_id, today)
        if not shift:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No shift assigned for today"
            )

        # Check shift exception
        exception = await self.check_shift_exception(shift.id, today)
        if exception and not exception.is_working_day:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Today is a non-working day for your shift"
            )

        # Determine shift times
        start_time = exception.custom_start_time if exception and exception.custom_start_time else shift.start_time

        # GPS validation
        distance = None
        if shift.gps_required and latitude and longitude:
            distance = await self.calculate_distance_from_office(latitude, longitude, shift)
            if distance > shift.allowed_radius:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"You are {distance:.0f}m away from office. Allowed radius: {shift.allowed_radius}m"
                )

        # Determine status (normal, late)
        status = "normal"
        current_time = now.time()
        late_threshold = timedelta(minutes=15)  # Configurable

        if current_time > start_time:
            # Calculate lateness
            start_datetime = datetime.combine(today, start_time)
            current_datetime = datetime.combine(today, current_time)
            if (current_datetime - start_datetime) > late_threshold:
                status = "late"

        log = AttendanceLog(
            user_id=user_id,
            log_type="check_in",
            log_date=today,
            log_time=now,
            latitude=latitude,
            longitude=longitude,
            location_address=location_address,
            distance_from_office=int(distance) if distance else None,
            status=status,
            device_info=device_info,
            ip_address=ip_address,
            photo_url=photo_url,
            notes=notes,
        )

        self.db.add(log)
        await self.db.flush()
        return log

    async def clock_out(
        self,
        user_id: int,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        location_address: Optional[str] = None,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> AttendanceLog:
        today = date.today()
        now = datetime.now()

        # Check if already clocked out
        if await self.check_duplicate_clock_in(user_id, "check_out", today):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already checked out today"
            )

        # Check if checked in
        if not await self.check_duplicate_clock_in(user_id, "check_in", today):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You need to check in before checking out"
            )

        # Get user's shift
        shift = await self.get_user_shift(user_id, today)
        end_time = shift.end_time if shift else time(18, 0)

        # Determine status
        status = "normal"
        current_time = now.time()
        early_threshold = timedelta(minutes=15)

        if current_time < end_time:
            end_datetime = datetime.combine(today, end_time)
            current_datetime = datetime.combine(today, current_time)
            if (end_datetime - current_datetime) > early_threshold:
                status = "early_leave"
        else:
            status = "overtime"

        log = AttendanceLog(
            user_id=user_id,
            log_type="check_out",
            log_date=today,
            log_time=now,
            latitude=latitude,
            longitude=longitude,
            location_address=location_address,
            status=status,
            device_info=device_info,
            ip_address=ip_address,
            notes=notes,
        )

        self.db.add(log)
        await self.db.flush()
        return log

    async def field_work_clock(
        self,
        user_id: int,
        latitude: float,
        longitude: float,
        location_address: str,
        notes: Optional[str] = None,
    ) -> AttendanceLog:
        today = date.today()
        now = datetime.now()

        log = AttendanceLog(
            user_id=user_id,
            log_type="field_work",
            log_date=today,
            log_time=now,
            latitude=latitude,
            longitude=longitude,
            location_address=location_address,
            status="field_work",
            notes=notes,
        )

        self.db.add(log)
        await self.db.flush()
        return log

    async def get_attendance_logs(
        self,
        user_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        department_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AttendanceLog], int]:
        query = select(AttendanceLog)
        count_query = select(func.count(AttendanceLog.id))

        if user_id:
            query = query.where(AttendanceLog.user_id == user_id)
            count_query = count_query.where(AttendanceLog.user_id == user_id)
        if start_date:
            query = query.where(AttendanceLog.log_date >= start_date)
            count_query = count_query.where(AttendanceLog.log_date >= start_date)
        if end_date:
            query = query.where(AttendanceLog.log_date <= end_date)
            count_query = count_query.where(AttendanceLog.log_date <= end_date)
        if status:
            query = query.where(AttendanceLog.status == status)
            count_query = count_query.where(AttendanceLog.status == status)

        if department_id:
            query = query.join(User).where(User.department_id == department_id)
            count_query = count_query.join(User).where(User.department_id == department_id)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        offset = (page - 1) * page_size
        query = query.order_by(AttendanceLog.log_date.desc(), AttendanceLog.log_time.desc())
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def generate_daily_summary(self, user_id: int, summary_date: date) -> dict:
        # Get all logs for the day
        result = await self.db.execute(
            select(AttendanceLog).where(
                AttendanceLog.user_id == user_id,
                AttendanceLog.log_date == summary_date
            )
        )
        logs = result.scalars().all()

        check_in = next((l for l in logs if l.log_type == "check_in"), None)
        check_out = next((l for l in logs if l.log_type == "check_out"), None)
        field_work = [l for l in logs if l.log_type == "field_work"]

        return {
            "date": summary_date.isoformat(),
            "user_id": user_id,
            "check_in": check_in.log_time if check_in else None,
            "check_out": check_out.log_time if check_out else None,
            "check_in_status": check_in.status if check_in else "absent",
            "check_out_status": check_out.status if check_out else "absent",
            "field_work_count": len(field_work),
            "is_present": check_in is not None,
            "is_late": check_in.status == "late" if check_in else False,
            "is_early_leave": check_out.status == "early_leave" if check_out else False,
        }
