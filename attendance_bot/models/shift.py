# attendance_bot/models/shift.py
from datetime import time
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Time, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    break_duration: Mapped[int] = mapped_column(Integer, default=60)
    latitude: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 8), nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(DECIMAL(11, 8), nullable=True)
    allowed_radius: Mapped[int] = mapped_column(Integer, default=500)
    gps_required: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="shift")
    exceptions: Mapped[list["ShiftException"]] = relationship(
        "ShiftException", back_populates="shift", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Shift(id={self.id}, name={self.name}, type={self.type})>"


class ShiftException(Base):
    __tablename__ = "shift_exceptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shift_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False
    )
    exception_date: Mapped[Date] = mapped_column(Date, nullable=False)
    custom_start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    custom_end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    is_working_day: Mapped[bool] = mapped_column(Boolean, default=True)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    shift: Mapped["Shift"] = relationship("Shift", back_populates="exceptions")

    def __repr__(self) -> str:
        return f"<ShiftException(shift_id={self.shift_id}, date={self.exception_date})>"


class UserShift(Base):
    __tablename__ = "user_shifts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    shift_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False
    )
    effective_from: Mapped[Date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<UserShift(user_id={self.user_id}, shift_id={self.shift_id})>"
