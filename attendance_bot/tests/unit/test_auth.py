# attendance_bot/tests/unit/test_auth.py
import pytest
from datetime import timedelta

from services.auth_service import AuthService
from services.user_service import UserService
from models import User


@pytest.mark.asyncio
async def test_password_hashing(security_manager):
    password = "TestPassword123!"
    hashed = security_manager.hash_password(password)
    assert security_manager.verify_password(password, hashed)
    assert not security_manager.verify_password("wrongpassword", hashed)


@pytest.mark.asyncio
async def test_jwt_token_creation(security_manager):
    data = {"sub": "1", "role": "employee"}
    token = security_manager.create_access_token(data)
    assert token is not None

    payload = security_manager.decode_token(token)
    assert payload["sub"] == "1"
    assert payload["role"] == "employee"
    assert payload["type"] == "access"


@pytest.mark.asyncio
async def test_user_authentication(db_session, sample_user_data, security_manager):
    user_service = UserService(db_session)

    # Create user
    user = await user_service.create_user(
        employee_number=sample_user_data["employee_number"],
        full_name=sample_user_data["full_name"],
        username=sample_user_data["username"],
        email=sample_user_data["email"],
        password=sample_user_data["password"],
    )
    await db_session.commit()

    # Test authentication
    auth_service = AuthService(db_session)
    authenticated_user = await auth_service.authenticate_user(
        sample_user_data["username"],
        sample_user_data["password"]
    )

    assert authenticated_user is not None
    assert authenticated_user.id == user.id
    assert authenticated_user.username == sample_user_data["username"]


@pytest.mark.asyncio
async def test_invalid_authentication(db_session, sample_user_data):
    auth_service = AuthService(db_session)

    # Test with non-existent user
    user = await auth_service.authenticate_user("nonexistent", "password")
    assert user is None


@pytest.mark.asyncio
async def test_role_permissions(security_manager):
    assert security_manager.check_permission("super_admin", "admin")
    assert security_manager.check_permission("admin", "manager")
    assert security_manager.check_permission("manager", "employee")
    assert not security_manager.check_permission("employee", "admin")
    assert not security_manager.check_permission("manager", "super_admin")
