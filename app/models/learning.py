"""HRIS · 培训与开发域（Learning & Development）模型。

对齐 SuccessFactors Learning / Career Development 的核心实体：
培训课程、报名与完成记录、讲师、学习路径。
"""

from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class TrainingCourse(Base, TimestampMixin):
    """培训课程 / 学习资源。"""

    __tablename__ = "training_course"

    code: Mapped[str] = mapped_column(String(32), default="")
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(32))
    # leadership 领导力 / professional 专业力 / general 通用力 / compliance 合规
    delivery_mode: Mapped[str] = mapped_column(String(16), default="online")
    # online 线上 / classroom 面授 / workshop 工作坊 / mentoring 导师制
    duration_hours: Mapped[float] = mapped_column(Float, default=0.0)
    cost_per_head: Mapped[int] = mapped_column(Integer, default=0)
    target_competency_id: Mapped[int | None] = mapped_column(
        ForeignKey("competency.id"), nullable=True
    )
    target_level: Mapped[int] = mapped_column(Integer, default=3)  # 结业可达的能力等级
    provider: Mapped[str] = mapped_column(String(64), default="内训")
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否必修
    description: Mapped[str] = mapped_column(Text, default="")

    target_competency: Mapped["Competency"] = relationship()


class TrainingEnrollment(Base, TimestampMixin):
    """员工报名与完成记录。"""

    __tablename__ = "training_enrollment"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    course_id: Mapped[int] = mapped_column(ForeignKey("training_course.id"))
    enrolled_at: Mapped[date] = mapped_column(Date)
    completed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="enrolled")
    # enrolled 已报名 / completed 已完成 / dropped 未完成 / failed 未通过
    score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    hours_spent: Mapped[float] = mapped_column(Float, default=0.0)
    feedback_score: Mapped[float] = mapped_column(Float, default=0.0)  # 学员满意度 1-5

    employee: Mapped["Employee"] = relationship()
    course: Mapped["TrainingCourse"] = relationship()


__all__ = ["TrainingCourse", "TrainingEnrollment"]
