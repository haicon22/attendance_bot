# attendance_bot/services/leave_service.py
from datetime import date, datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    User, LeaveType, LeaveRequest, Approval, ApprovalFlow, 
    UserRole, AttendanceLog
)


class LeaveService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_leave_request(
        self,
        user_id: int,
        leave_type_id: int,
        start_date: date,
        end_date: date,
        reason: str,
        attachment_url: Optional[str] = None,
    ) -> LeaveRequest:
        # Validate dates
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date cannot be after end date"
            )

        if start_date < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot request leave for past dates"
            )

        # Calculate total days (excluding weekends and holidays)
        total_days = self._calculate_working_days(start_date, end_date)

        # Get leave type
        result = await self.db.execute(
            select(LeaveType).where(LeaveType.id == leave_type_id)
        )
        leave_type = result.scalar_one_or_none()
        if not leave_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave type not found"
            )

        # Check balance for annual leave
        if leave_type.code == "annual_leave":
            user_result = await self.db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one()
            if user.annual_leave_balance < total_days:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient annual leave balance. Available: {user.annual_leave_balance}, Required: {total_days}"
                )

        # Create request
        request = LeaveRequest(
            user_id=user_id,
            leave_type_id=leave_type_id,
            start_date=start_date,
            end_date=end_date,
            total_days=total_days,
            reason=reason,
            attachment_url=attachment_url,
            status="pending",
            current_approval_level=1,
            submitted_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(request)
        await self.db.flush()

        # Create approval records based on flow
        await self._create_approvals(request)

        return request

    def _calculate_working_days(self, start_date: date, end_date: date) -> float:
        days = 0
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                days += 1
            current += datetime.timedelta(days=1)
        return float(days)

    async def _create_approvals(self, request: LeaveRequest):
        # Get approval flow for leave type
        result = await self.db.execute(
            select(ApprovalFlow).where(
                ApprovalFlow.leave_type_id == request.leave_type_id,
                ApprovalFlow.is_active == True
            ).order_by(ApprovalFlow.approval_level)
        )
        flows = result.scalars().all()

        if not flows:
            # Default single-level approval
            flows = [ApprovalFlow(approval_level=1, approver_role="manager")]

        for flow in flows:
            # Find approver based on role
            approver_id = await self._find_approver(request.user_id, flow.approver_role)

            approval = Approval(
                leave_request_id=request.id,
                approver_id=approver_id,
                approval_level=flow.approval_level,
                status="pending",
            )
            self.db.add(approval)

        await self.db.flush()

    async def _find_approver(self, user_id: int, role: str) -> Optional[int]:
        # Get user's department manager
        result = await self.db.execute(
            select(User.department_id).where(User.id == user_id)
        )
        department_id = result.scalar()

        if role == "manager" and department_id:
            result = await self.db.execute(
                select(User.id).where(
                    User.department_id == department_id,
                    User.role == UserRole.MANAGER
                )
            )
            manager = result.scalar_one_or_none()
            if manager:
                return manager

        # Fallback to admin
        result = await self.db.execute(
            select(User.id).where(User.role == UserRole.ADMIN).limit(1)
        )
        return result.scalar_one_or_none()

    async def approve_leave(
        self,
        approval_id: int,
        approver_id: int,
        status: str,
        comment: Optional[str] = None,
    ) -> Approval:
        result = await self.db.execute(
            select(Approval).where(Approval.id == approval_id)
        )
        approval = result.scalar_one_or_none()

        if not approval:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval record not found"
            )

        if approval.approver_id != approver_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to approve this request"
            )

        if approval.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This request has already been processed"
            )

        approval.status = status
        approval.comment = comment
        approval.action_at = datetime.utcnow()

        # Update leave request
        request_result = await self.db.execute(
            select(LeaveRequest).where(LeaveRequest.id == approval.leave_request_id)
        )
        request = request_result.scalar_one()

        if status == "rejected":
            request.status = "rejected"
            request.resolved_at = datetime.utcnow()
        elif status == "approved":
            # Check if this is the final approval level
            max_level_result = await self.db.execute(
                select(func.max(Approval.approval_level)).where(
                    Approval.leave_request_id == request.id
                )
            )
            max_level = max_level_result.scalar()

            if approval.approval_level >= max_level:
                request.status = "approved"
                request.resolved_at = datetime.utcnow()

                # Deduct leave balance for annual leave
                leave_type_result = await self.db.execute(
                    select(LeaveType).where(LeaveType.id == request.leave_type_id)
                )
                leave_type = leave_type_result.scalar_one()

                if leave_type.code == "annual_leave":
                    await self.db.execute(
                        update(User).where(User.id == request.user_id).values(
                            annual_leave_balance=User.annual_leave_balance - request.total_days
                        )
                    )
            else:
                request.current_approval_level = approval.approval_level + 1

        request.updated_at = datetime.utcnow()
        await self.db.flush()

        return approval

    async def get_leave_requests(
        self,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[LeaveRequest], int]:
        query = select(LeaveRequest)
        count_query = select(func.count(LeaveRequest.id))

        if user_id:
            query = query.where(LeaveRequest.user_id == user_id)
            count_query = count_query.where(LeaveRequest.user_id == user_id)
        if status:
            query = query.where(LeaveRequest.status == status)
            count_query = count_query.where(LeaveRequest.status == status)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        offset = (page - 1) * page_size
        query = query.order_by(LeaveRequest.submitted_at.desc())
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def cancel_leave_request(self, request_id: int, user_id: int) -> LeaveRequest:
        result = await self.db.execute(
            select(LeaveRequest).where(LeaveRequest.id == request_id)
        )
        request = result.scalar_one_or_none()

        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave request not found"
            )

        if request.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only cancel your own requests"
            )

        if request.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only cancel pending requests"
            )

        request.status = "cancelled"
        request.updated_at = datetime.utcnow()
        await self.db.flush()

        return request
