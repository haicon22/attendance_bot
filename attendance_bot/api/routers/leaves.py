# attendance_bot/api/routers/leaves.py
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.leave_service import LeaveService
from api.middlewares.auth import get_current_user, require_role
from models import User, UserRole

router = APIRouter()


class LeaveRequestCreate(BaseModel):
    leave_type_id: int
    start_date: date
    end_date: date
    reason: str
    attachment_url: Optional[str] = None


class ApprovalAction(BaseModel):
    status: str  # approved or rejected
    comment: Optional[str] = None


@router.post("/requests")
async def create_leave_request(
    request: LeaveRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = LeaveService(db)
    leave_request = await service.create_leave_request(
        user_id=current_user.id,
        leave_type_id=request.leave_type_id,
        start_date=request.start_date,
        end_date=request.end_date,
        reason=request.reason,
        attachment_url=request.attachment_url,
    )
    await db.commit()
    return leave_request.to_dict()


@router.get("/requests")
async def list_leave_requests(
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role == UserRole.EMPLOYEE:
        user_id = current_user.id

    service = LeaveService(db)
    requests, total = await service.get_leave_requests(
        user_id=user_id,
        status=status,
        page=page,
        page_size=page_size,
    )

    return {
        "items": [req.to_dict() for req in requests],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/approvals/{approval_id}")
async def process_approval(
    approval_id: int,
    action: ApprovalAction,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = LeaveService(db)
    approval = await service.approve_leave(
        approval_id=approval_id,
        approver_id=current_user.id,
        status=action.status,
        comment=action.comment,
    )
    await db.commit()
    return approval.to_dict()


@router.post("/requests/{request_id}/cancel")
async def cancel_leave_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = LeaveService(db)
    request = await service.cancel_leave_request(request_id, current_user.id)
    await db.commit()
    return request.to_dict()
