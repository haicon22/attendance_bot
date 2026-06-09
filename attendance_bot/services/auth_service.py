# attendance_bot/services/auth_service.py
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import SecurityManager
from models import User, UserRole


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.security = SecurityManager()

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(
                (User.username == username) | (User.email == username),
                User.status == "active"
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        if not self.security.verify_password(password, user.password_hash):
            return None
        return user

    async def login(self, username: str, password: str) -> dict:
        user = await self.authenticate_user(username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        user.last_login = datetime.utcnow()
        await self.db.commit()

        access_token = self.security.create_access_token(
            {"sub": str(user.id), "role": user.role, "employee_number": user.employee_number}
        )
        refresh_token = self.security.create_refresh_token({"sub": str(user.id)})

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 3600 * 24,
            "user": {
                "id": user.id,
                "employee_number": user.employee_number,
                "full_name": user.full_name,
                "role": user.role,
                "department_id": user.department_id,
            }
        }

    async def refresh_token(self, refresh_token: str) -> dict:
        payload = self.security.decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        user_id = int(payload["sub"])
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        new_access_token = self.security.create_access_token(
            {"sub": str(user.id), "role": user.role, "employee_number": user.employee_number}
        )

        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": 3600 * 24,
        }

    def check_permission(self, user_role: str, required_role: str) -> bool:
        role_hierarchy = {
            UserRole.SUPER_ADMIN: 4,
            UserRole.ADMIN: 3,
            UserRole.MANAGER: 2,
            UserRole.EMPLOYEE: 1,
        }
        return role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0)
