# attendance_bot/services/user_service.py
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import SecurityManager
from models import User, UserTelegramBinding, Department, UserRole


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.security = SecurityManager()

    async def create_user(
        self,
        employee_number: str,
        full_name: str,
        username: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        phone: Optional[str] = None,
        department_id: Optional[int] = None,
        shift_id: Optional[int] = None,
        role: str = UserRole.EMPLOYEE,
        created_by: Optional[int] = None,
    ) -> User:
        # Check if employee number exists
        result = await self.db.execute(
            select(User).where(User.employee_number == employee_number)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee number {employee_number} already exists"
            )

        password_hash = None
        if password:
            password_hash = self.security.hash_password(password)

        user = User(
            employee_number=employee_number,
            username=username,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            phone=phone,
            department_id=department_id,
            shift_id=shift_id,
            role=role,
            status="active",
            updated_at=datetime.utcnow(),
            created_by=created_by,
        )

        self.db.add(user)
        await self.db.flush()
        return user

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_employee_number(self, employee_number: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.employee_number == employee_number)
        )
        return result.scalar_one_or_none()

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self.db.execute(
            select(User)
            .join(UserTelegramBinding)
            .where(
                UserTelegramBinding.telegram_id == telegram_id,
                UserTelegramBinding.is_active == True
            )
        )
        return result.scalar_one_or_none()

    async def bind_telegram(
        self,
        user_id: int,
        telegram_id: int,
        telegram_username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> UserTelegramBinding:
        # Check if telegram_id already bound
        result = await self.db.execute(
            select(UserTelegramBinding).where(UserTelegramBinding.telegram_id == telegram_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This Telegram account is already bound to another user"
            )

        binding = UserTelegramBinding(
            user_id=user_id,
            telegram_id=telegram_id,
            telegram_username=telegram_username,
            first_name=first_name,
            last_name=last_name,
            is_active=True,
            bound_at=datetime.utcnow(),
            last_interaction=datetime.utcnow(),
        )

        self.db.add(binding)
        await self.db.flush()
        return binding

    async def update_user(self, user_id: int, **kwargs) -> User:
        allowed_fields = {
            "full_name", "email", "phone", "department_id", 
            "shift_id", "role", "status", "annual_leave_balance", "sick_leave_balance"
        }
        update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )

        update_data["updated_at"] = datetime.utcnow()

        await self.db.execute(
            update(User).where(User.id == user_id).values(**update_data)
        )

        return await self.get_user_by_id(user_id)

    async def delete_user(self, user_id: int) -> bool:
        result = await self.db.execute(delete(User).where(User.id == user_id))
        return result.rowcount > 0

    async def list_users(
        self,
        department_id: Optional[int] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[User], int]:
        query = select(User)
        count_query = select(func.count(User.id))

        if department_id:
            query = query.where(User.department_id == department_id)
            count_query = count_query.where(User.department_id == department_id)
        if role:
            query = query.where(User.role == role)
            count_query = count_query.where(User.role == role)
        if status:
            query = query.where(User.status == status)
            count_query = count_query.where(User.status == status)
        if search:
            query = query.where(
                (User.full_name.ilike(f"%{search}%")) |
                (User.employee_number.ilike(f"%{search}%"))
            )
            count_query = count_query.where(
                (User.full_name.ilike(f"%{search}%")) |
                (User.employee_number.ilike(f"%{search}%"))
            )

        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        users = result.scalars().all()

        return list(users), total
