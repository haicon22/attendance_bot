# attendance_bot/api/routers/departments.py
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from api.middlewares.auth import get_current_user, require_role
from models import User, UserRole, Department

router = APIRouter()


class DepartmentCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    manager_id: Optional[int] = None
    parent_id: Optional[int] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    manager_id: Optional[int] = None
    parent_id: Optional[int] = None
    is_active: Optional[bool] = None


@router.post("")
async def create_department(
    request: DepartmentCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    dept = Department(
        name=request.name,
        code=request.code,
        description=request.description,
        manager_id=request.manager_id,
        parent_id=request.parent_id,
    )
    db.add(dept)
    await db.flush()
    return dept.to_dict()


@router.get("")
async def list_departments(
    parent_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Department)
    if parent_id is not None:
        query = query.where(Department.parent_id == parent_id)
    if is_active is not None:
        query = query.where(Department.is_active == is_active)

    result = await db.execute(query)
    departments = result.scalars().all()
    return [d.to_dict() for d in departments]


@router.get("/{dept_id}")
async def get_department(
    dept_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept.to_dict()


@router.put("/{dept_id}")
async def update_department(
    dept_id: int,
    request: DepartmentUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(dept, key, value)

    await db.flush()
    return dept.to_dict()
