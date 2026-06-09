# attendance_bot/models/leave.py
from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class LeaveType(Base):
    __tablename__ = "leave_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    default_days: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    approval_levels: Mapped[int] = mapped_column(Integer, default=1)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<LeaveType(id={self.id}, name={self.name}, code={self.code})>"


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    leave_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("leave_types.id"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_days: Mapped[float] = mapped_column(DECIMAL(5, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    current_approval_level: Mapped[int] = mapped_column(Integer, default=1)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="leave_requests")
    approvals: Mapped[list["Approval"]] = relationship(
        "Approval", back_populates="leave_request", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<LeaveRequest(id={self.id}, user_id={self.user_id}, status={self.status})>"


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    leave_request_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("leave_requests.id", ondelete="CASCADE"), nullable=False
    )
    approver_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    approval_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    leave_request: Mapped["LeaveRequest"] = relationship("LeaveRequest", back_populates="approvals")

    def __repr__(self) -> str:
        return f"<Approval(request_id={self.leave_request_id}, level={self.approval_level}, status={self.status})>"
