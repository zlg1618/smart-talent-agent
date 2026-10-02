"""个人发展计划、学习资源与组织诊断指标。"""

from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Course(Base, TimestampMixin):
    """学习资源。form 对应 70-20-10 发展法则：项目历练 / 导师辅导 / 培训课程。"""

    __tablename__ = "course"

    name: Mapped[str] = mapped_column(String(128))
    competency_id: Mapped[int] = mapped_column(ForeignKey("competency.id"))
    target_level: Mapped[int] = mapped_column(Integer)
    duration_hours: Mapped[int] = mapped_column(Integer, default=8)
    form: Mapped[str] = mapped_column(String(16))  # 项目 / 导师 / 线上 / 线下

    competency: Mapped["Competency"] = relationship()


class IDP(Base, TimestampMixin):
    """个人发展计划（Individual Development Plan）。"""

    __tablename__ = "idp"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    period: Mapped[str] = mapped_column(String(16))
    goal: Mapped[str] = mapped_column(String(255))
    competency_id: Mapped[int | None] = mapped_column(
        ForeignKey("competency.id"), nullable=True
    )
    action_type: Mapped[str] = mapped_column(String(16))  # 项目 / 导师 / 培训 / 轮岗
    action_name: Mapped[str] = mapped_column(String(128))
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="未开始")

    employee: Mapped["Employee"] = relationship()
    competency: Mapped["Competency"] = relationship()


class DepartmentMetric(Base, TimestampMixin):
    """部门级组织诊断指标。"""

    __tablename__ = "department_metric"

    department: Mapped[str] = mapped_column(String(64))
    period: Mapped[str] = mapped_column(String(16))
    headcount: Mapped[int] = mapped_column(Integer)
    avg_tenure: Mapped[float] = mapped_column(Float)  # 平均司龄（年）
    turnover_rate: Mapped[float] = mapped_column(Float)  # 离职率
    avg_performance: Mapped[float] = mapped_column(Float)
    high_potential_ratio: Mapped[float] = mapped_column(Float)  # 高潜占比
    span_of_control: Mapped[float] = mapped_column(Float)  # 平均管理幅度
    headcount_change: Mapped[int] = mapped_column(Integer, default=0)  # 人数净变化


__all__ = ["Course", "DepartmentMetric", "IDP"]
