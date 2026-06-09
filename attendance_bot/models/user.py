# attendance_bot/models/user.py
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    employee_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    shift_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True
    )

    role: Mapped[str] = mapped_column(String(20), nullable=False, default=UserRole.EMPLOYEE)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=UserStatus.ACTIVE)

    annual_leave_balance: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0)
    sick_leave_balance: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    department: Mapped[Optional["Department"]] = relationship("Department", back_populates="users")
    shift: Mapped[Optional["Shift"]] = relationship("Shift", back_populates="users")
    telegram_bindings: Mapped[list["UserTelegramBinding"]] = relationship(
        "UserTelegramBinding", back_populates="user", cascade="all, delete-orphan"
    )
    attendance_logs: Mapped[list["AttendanceLog"]] = relationship(
        "AttendanceLog", back_populates="user", cascade="all, delete-orphan"
    )
    leave_requests: Mapped[list["LeaveRequest"]] = relationship(
        "LeaveRequest", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, employee_number={self.employee_number}, full_name={self.full_name})>"


class UserTelegramBinding(Base):
    __tablename__ = "user_telegram_bindings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    bound_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_interaction: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="telegram_bindings")

    def __repr__(self) -> str:
        return f"<UserTelegramBinding(telegram_id={self.telegram_id}, user_id={self.user_id})>"
