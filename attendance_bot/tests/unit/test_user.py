# attendance_bot/tests/unit/test_user.py
import pytest

from services.user_service import UserService
from models import User


@pytest.mark.asyncio
async def test_create_user(db_session, sample_user_data):
    service = UserService(db_session)

    user = await service.create_user(
        employee_number=sample_user_data["employee_number"],
        full_name=sample_user_data["full_name"],
        username=sample_user_data["username"],
        email=sample_user_data["email"],
        password=sample_user_data["password"],
    )
    await db_session.commit()

    assert user is not None
    assert user.employee_number == sample_user_data["employee_number"]
    assert user.full_name == sample_user_data["full_name"]
    assert user.username == sample_user_data["username"]
    assert user.email == sample_user_data["email"]
    assert user.password_hash is not None
    assert user.status == "active"


@pytest.mark.asyncio
async def test_duplicate_employee_number(db_session, sample_user_data):
    service = UserService(db_session)

    await service.create_user(
        employee_number=sample_user_data["employee_number"],
        full_name=sample_user_data["full_name"],
    )
    await db_session.commit()

    with pytest.raises(Exception) as exc_info:
        await service.create_user(
            employee_number=sample_user_data["employee_number"],
            full_name="Another User",
        )

    assert "already exists" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_telegram_binding(db_session, sample_user_data):
    service = UserService(db_session)

    user = await service.create_user(
        employee_number=sample_user_data["employee_number"],
        full_name=sample_user_data["full_name"],
    )
    await db_session.commit()

    binding = await service.bind_telegram(
        user_id=user.id,
        telegram_id=123456789,
        telegram_username="testuser",
    )
    await db_session.commit()

    assert binding is not None
    assert binding.user_id == user.id
    assert binding.telegram_id == 123456789
    assert binding.is_active is True


@pytest.mark.asyncio
async def test_list_users_pagination(db_session):
    service = UserService(db_session)

    # Create multiple users
    for i in range(25):
        await service.create_user(
            employee_number=f"EMP{i:03d}",
            full_name=f"User {i}",
        )
    await db_session.commit()

    # Test pagination
    users, total = await service.list_users(page=1, page_size=10)
    assert len(users) == 10
    assert total == 25

    users, total = await service.list_users(page=3, page_size=10)
    assert len(users) == 5
    assert total == 25
