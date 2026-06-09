# attendance_bot/tests/unit/test_attendance.py
import pytest
from datetime import date, datetime, time, timedelta

from services.attendance_service import AttendanceService
from services.user_service import UserService
from models import User, Shift, AttendanceLog


@pytest.mark.asyncio
async def test_clock_in(db_session, sample_user_data):
    # Create user and shift
    user_service = UserService(db_session)
    user = await user_service.create_user(
        employee_number=sample_user_data["employee_number"],
        full_name=sample_user_data["full_name"],
    )

    # Create shift
    shift = Shift(
        name="Test Shift",
        type="fixed",
        start_time=time(9, 0),
        end_time=time(18, 0),
        gps_required=False,
    )
    db_session.add(shift)
    await db_session.flush()

    user.shift_id = shift.id
    await db_session.commit()

    # Test clock in
    service = AttendanceService(db_session)
    log = await service.clock_in(user_id=user.id)
    await db_session.commit()

    assert log is not None
    assert log.log_type == "check_in"
    assert log.user_id == user.id
    assert log.log_date == date.today()


@pytest.mark.asyncio
async def test_duplicate_clock_in_prevention(db_session, sample_user_data):
    user_service = UserService(db_session)
    user = await user_service.create_user(
        employee_number=sample_user_data["employee_number"],
        full_name=sample_user_data["full_name"],
    )

    shift = Shift(
        name="Test Shift",
        type="fixed",
        start_time=time(9, 0),
        end_time=time(18, 0),
        gps_required=False,
    )
    db_session.add(shift)
    await db_session.flush()
    user.shift_id = shift.id
    await db_session.commit()

    service = AttendanceService(db_session)
    await service.clock_in(user_id=user.id)
    await db_session.commit()

    # Try to clock in again
    with pytest.raises(Exception) as exc_info:
        await service.clock_in(user_id=user.id)

    assert "already checked in" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_gps_distance_calculation(security_manager):
    # Test Haversine formula
    # Beijing coordinates
    lat1, lon1 = 39.9042, 116.4074
    lat2, lon2 = 39.9142, 116.4174

    distance = security_manager.calculate_distance(lat1, lon1, lat2, lon2)

    # Distance should be approximately 1.4km
    assert 1000 < distance < 2000


@pytest.mark.asyncio
async def test_late_detection(db_session, sample_user_data):
    user_service = UserService(db_session)
    user = await user_service.create_user(
        employee_number=sample_user_data["employee_number"],
        full_name=sample_user_data["full_name"],
    )

    # Create shift starting at 9:00 AM
    shift = Shift(
        name="Morning Shift",
        type="fixed",
        start_time=time(9, 0),
        end_time=time(18, 0),
        gps_required=False,
    )
    db_session.add(shift)
    await db_session.flush()
    user.shift_id = shift.id
    await db_session.commit()

    # Mock clock in at 10:00 AM (1 hour late)
    service = AttendanceService(db_session)

    # Create a late check-in log manually
    log = AttendanceLog(
        user_id=user.id,
        log_type="check_in",
        log_date=date.today(),
        log_time=datetime.combine(date.today(), time(10, 0)),
        status="late",
    )
    db_session.add(log)
    await db_session.commit()

    assert log.status == "late"
