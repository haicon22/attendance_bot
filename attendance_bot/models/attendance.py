# attendance_bot/models/attendance.py
from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, String, Text, DECIMAL, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    log_type: Mapped[str] = mapped_column(String(20), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    log_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latitude: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 8), nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(DECIMAL(11, 8), nullable=True)
    location_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    distance_from_office: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    device_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="attendance_logs")

    def __repr__(self) -> str:
        return f"<AttendanceLog(user_id={self.user_id}, type={self.log_type}, date={self.log_date})>"


class AttendanceSummary(Base):
    __tablename__ = "attendance_summaries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    total_working_days: Mapped[int] = mapped_column(Integer, default=0)
    present_days: Mapped[int] = mapped_column(Integer, default=0)
    late_days: Mapped[int] = mapped_column(Integer, default=0)
    early_leave_days: Mapped[int] = mapped_column(Integer, default=0)
    absent_days: Mapped[int] = mapped_column(Integer, default=0)
    field_work_days: Mapped[int] = mapped_column(Integer, default=0)
    overtime_hours: Mapped[float] = mapped_column(DECIMAL(8, 2), default=0)
    leave_days: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<AttendanceSummary(user_id={self.user_id}, year={self.year}, month={self.month})>"
