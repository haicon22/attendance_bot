# attendance_bot/tests/unit/test_leave.py
import pytest
from datetime import date, timedelta

from services.leave_service import LeaveService
from services.user_service import UserService
from models import LeaveType, LeaveRequest


@pytest.mark.asyncio
async def test_create_leave_request(db_session, sample_user_data):
    # Setup
    user_service = UserService(db_session)
    user = await user_service.create_user(
        employee_number=sample_user_data["employee_number"],
        full_name=sample_user_data["full_name"],
    )

    leave_type = LeaveType(
        name="Annual Leave",
        code="annual_leave",
        default_days=10,
        requires_approval=True,
        approval_levels=1,
    )
    db_session.add(leave_type)
    await db_session.flush()

    # Create leave request
    service = LeaveService(db_session)
    start_date = date.today() + timedelta(days=1)
    end_date = start_date + timedelta(days=2)

    request = await service.create_leave_request(
        user_id=user.id,
        leave_type_id=leave_type.id,
        start_date=start_date,
        end_date=end_date,
        reason="Personal vacation",
    )
    await db_session.commit()

    assert request is not None
    assert request.status == "pending"
    assert request.user_id == user.id
    assert request.total_days > 0


@pytest.mark.asyncio
async def test_past_date_leave_rejection(db_session, sample_user_data):
    user_service = UserService(db_session)
    user = await user_service.create_user(
        employee_number=sample_user_data["employee_number"],
        full_name=sample_user_data["full_name"],
    )

    leave_type = LeaveType(name="Sick Leave", code="sick_leave")
    db_session.add(leave_type)
    await db_session.flush()

    service = LeaveService(db_session)

    with pytest.raises(Exception) as exc_info:
        await service.create_leave_request(
            user_id=user.id,
            leave_type_id=leave_type.id,
            start_date=date.today() - timedelta(days=1),
            end_date=date.today(),
            reason="Test",
        )

    assert "past dates" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_working_days_calculation(db_session):
    service = LeaveService(db_session)

    # Monday to Friday (5 working days)
    start = date(2024, 6, 3)  # Monday
    end = date(2024, 6, 7)   # Friday
    days = service._calculate_working_days(start, end)
    assert days == 5

    # Including weekend (should exclude Saturday and Sunday)
    start = date(2024, 6, 3)  # Monday
    end = date(2024, 6, 9)   # Sunday
    days = service._calculate_working_days(start, end)
    assert days == 5
