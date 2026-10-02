"""HRIS · 员工关系管理域（Employee Relations）模型。

对齐 SuccessFactors Employee Central / Time Off 的核心实体：
请假申请、考勤记录、员工关系事件、敬业度调查。
"""

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
    """每日考勤记录。"""

    __tablename__ = "attendance_record"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    date: Mapped[date] = mapped_column(Date)
    check_in: Mapped[time | None] = mapped_column(Time, nullable=True)
    check_out: Mapped[time | None] = mapped_column(Time, nullable=True)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)
    is_absent: Mapped[bool] = mapped_column(Boolean, default=False)
    hours: Mapped[float] = mapped_column(Float, default=0.0)

    employee: Mapped["Employee"] = relationship()


class RelationCase(Base, TimestampMixin):
    """员工关系事件：纠纷、申诉、关怀、合规调查等。"""

    __tablename__ = "relation_case"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    case_type: Mapped[str] = mapped_column(String(32))
    # dispute 劳动争议 / grievance 申诉 / harassment 骚扰举报 /
    # care 关怀访谈 / compliance 合规调查
    severity: Mapped[str] = mapped_column(String(16), default="medium")  # low/medium/high
    opened_at: Mapped[date] = mapped_column(Date)
    closed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    owner: Mapped[str] = mapped_column(String(32), default="")  # 处理负责人
    description: Mapped[str] = mapped_column(Text, default="")
    resolution: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="open")  # open / closed
    escalation_risk: Mapped[float] = mapped_column(Float, default=0.0)  # 0-1 升级风险

    employee: Mapped["Employee"] = relationship()


class EngagementSurvey(Base, TimestampMixin):
    """敬业度 / 满意度调查得分。"""

    __tablename__ = "engagement_survey"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    period: Mapped[str] = mapped_column(String(16))
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)  # 1-5
    # 分项得分
    score_work: Mapped[float] = mapped_column(Float, default=0.0)  # 工作本身
    score_manager: Mapped[float] = mapped_column(Float, default=0.0)  # 直属上级
    score_growth: Mapped[float] = mapped_column(Float, default=0.0)  # 成长发展
    score_reward: Mapped[float] = mapped_column(Float, default=0.0)  # 薪酬回报
    score_balance: Mapped[float] = mapped_column(Float, default=0.0)  # 工作生活平衡
    is_promoter: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否推荐者 eNPS
    comment: Mapped[str] = mapped_column(Text, default="")

    employee: Mapped["Employee"] = relationship()


__all__ = [
    "AttendanceRecord",
    "EngagementSurvey",
    "LeaveRequest",
    "RelationCase",
]
