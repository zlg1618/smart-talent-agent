"""HRIS · 绩效管理域（Performance Management）模型。

对齐 SuccessFactors Performance & Goals / Calibration 的核心实体：
绩效目标、绩效评估记录、校准会议结论、绩效改进计划 PIP。
"""

from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class PerformanceGoal(Base, TimestampMixin):
    """绩效目标（OKR / KPI 条目）。"""

    __tablename__ = "performance_goal"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    period: Mapped[str] = mapped_column(String(16))  # 2025H1
    title: Mapped[str] = mapped_column(String(128))
    goal_type: Mapped[str] = mapped_column(String(16))  # OKR / KPI
    weight: Mapped[float] = mapped_column(Float, default=1.0)  # 权重 0-1
    target_value: Mapped[float] = mapped_column(Float, default=100.0)
    actual_value: Mapped[float] = mapped_column(Float, default=0.0)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="in_progress")
    # in_progress / completed / at_risk / missed

    employee: Mapped["Employee"] = relationship()


class PerformanceReview(Base, TimestampMixin):
    """绩效评估：自评、主管评、校准后终评。"""

    __tablename__ = "performance_review"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("employee.id"), nullable=True)
    period: Mapped[str] = mapped_column(String(16))
    self_score: Mapped[float] = mapped_column(Float, default=0.0)  # 1-5
    manager_score: Mapped[float] = mapped_column(Float, default=0.0)  # 1-5
    calibrated_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 校准后
    rating_label: Mapped[str] = mapped_column(String(16), default="")  # S/A/B/C/D
    review_date: Mapped[date] = mapped_column(Date)
    comment: Mapped[str] = mapped_column(Text, default="")

    employee: Mapped["Employee"] = relationship(foreign_keys=[employee_id])


class CalibrationSession(Base, TimestampMixin):
    """绩效校准会：记录部门级的分布调整。"""

    __tablename__ = "calibration_session"

    department: Mapped[str] = mapped_column(String(64))
    period: Mapped[str] = mapped_column(String(16))
    held_at: Mapped[date] = mapped_column(Date)
    participant_count: Mapped[int] = mapped_column(Integer, default=0)
    before_distribution: Mapped[str] = mapped_column(Text, default="")  # JSON
    after_distribution: Mapped[str] = mapped_column(Text, default="")  # JSON
    adjusted_count: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(Text, default="")


class ImprovementPlan(Base, TimestampMixin):
    """绩效改进计划 PIP：针对低绩效员工的辅导方案。"""

    __tablename__ = "improvement_plan"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    period: Mapped[str] = mapped_column(String(16))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(Text, default="")
    target_score: Mapped[float] = mapped_column(Float, default=3.0)
    mentor_id: Mapped[int | None] = mapped_column(ForeignKey("employee.id"), nullable=True)
    outcome: Mapped[str] = mapped_column(String(16), default="ongoing")
    # ongoing / passed / failed / extended

    employee: Mapped["Employee"] = relationship(foreign_keys=[employee_id])


__all__ = [
    "CalibrationSession",
    "ImprovementPlan",
    "PerformanceGoal",
    "PerformanceReview",
]
