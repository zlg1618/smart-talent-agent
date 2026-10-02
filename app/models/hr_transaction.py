"""HRIS 事务模型：请假、考勤、入转调离（员工服务的核心事务）。"""

from datetime import date, time

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class LeaveRequest(Base, TimestampMixin):
    """请假申请。"""

    __tablename__ = "leave_request"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    leave_type: Mapped[str] = mapped_column(String(16))
    # annual 年假 / sick 病假 / personal 事假 / compensatory 调休 / maternity 产假
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    days: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="pending")
    # pending / approved / rejected / canceled
    approver_id: Mapped[int | None] = mapped_column(
        ForeignKey("employee.id"), nullable=True
    )

    employee: Mapped["Employee"] = relationship(foreign_keys=[employee_id])


class AttendanceRecord(Base, TimestampMixin):
    """每日考勤记录（简化版，演示用）。"""

    __tablename__ = "attendance_record"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    date: Mapped[date] = mapped_column(Date)
    check_in: Mapped[time | None] = mapped_column(Time, nullable=True)
    check_out: Mapped[time | None] = mapped_column(Time, nullable=True)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)
    is_absent: Mapped[bool] = mapped_column(Boolean, default=False)
    hours: Mapped[float] = mapped_column(Float, default=0.0)

    employee: Mapped["Employee"] = relationship()


__all__ = ["AttendanceRecord", "LeaveRequest"]