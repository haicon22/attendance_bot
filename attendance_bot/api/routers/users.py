# attendance_bot/api/routers/users.py
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.user_service import UserService
from api.middlewares.auth import get_current_user, require_role
from models import User, UserRole

router = APIRouter()


class UserCreateRequest(BaseModel):
    employee_number: str
    full_name: str
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    phone: Optional[str] = None
    department_id: Optional[int] = None
    shift_id: Optional[int] = None
    role: str = UserRole.EMPLOYEE
    annual_leave_balance: float = 0
    sick_leave_balance: float = 0


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    department_id: Optional[int] = None
    shift_id: Optional[int] = None
    role: Optional[str] = None
    status: Optional[str] = None
    annual_leave_balance: Optional[float] = None
    sick_leave_balance: Optional[float] = None


class UserResponse(BaseModel):
    id: int
    employee_number: str
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    department_id: Optional[int]
    shift_id: Optional[int]
    role: str
    status: str
    annual_leave_balance: float
    sick_leave_balance: float
    created_at: str

    class Config:
        from_attributes = True


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreateRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    service = UserService(db)
    user = await service.create_user(
        employee_number=request.employee_number,
        full_name=request.full_name,
        username=request.username,
        email=request.email,
        password=request.password,
        phone=request.phone,
        department_id=request.department_id,
        shift_id=request.shift_id,
        role=request.role,
        created_by=current_user.id,
    )
    await db.commit()
    return user


@router.get("")
async def list_users(
    department_id: Optional[int] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = UserService(db)
    users, total = await service.list_users(
        department_id=department_id,
        role=role,
        status=status,
        search=search,
        page=page,
        page_size=page_size,
    )

    return {
        "items": [u.to_dict() for u in users],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = UserService(db)
    user = await service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UserUpdateRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    service = UserService(db)
    update_data = request.model_dump(exclude_unset=True)
    user = await service.update_user(user_id, **update_data)
    await db.commit()
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    service = UserService(db)
    success = await service.delete_user(user_id)
    await db.commit()
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}
