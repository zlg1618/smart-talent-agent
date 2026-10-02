"""员工主数据与人才评价数据。"""

from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Employee(Base, TimestampMixin):
    """员工。"""

    __tablename__ = "employee"

    employee_no: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(32))
    department: Mapped[str] = mapped_column(String(64))
    position_title: Mapped[str] = mapped_column(String(64))
    job_family: Mapped[str] = mapped_column(String(32))  # 职族：技术 / 产品 / 销售 / 职能
    job_level: Mapped[str] = mapped_column(String(8))  # P4-P8、M1-M3
    hire_date: Mapped[date] = mapped_column(Date)
    city: Mapped[str] = mapped_column(String(32))
    manager_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="在职")

    performances: Mapped[list["PerformanceRecord"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    potentials: Mapped[list["PotentialAssessment"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    competencies: Mapped[list["EmployeeCompetency"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )


class PerformanceRecord(Base, TimestampMixin):
    """绩效考核记录。score 为 1-5 分。"""

    __tablename__ = "performance_record"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    period: Mapped[str] = mapped_column(String(16))  # 如 2025H1
    score: Mapped[float] = mapped_column(Float)
    grade: Mapped[str] = mapped_column(String(8))  # A / B+ / B / C

    employee: Mapped["Employee"] = relationship(back_populates="performances")


class PotentialAssessment(Base, TimestampMixin):
    """潜力评估记录。"""

    __tablename__ = "potential_assessment"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    period: Mapped[str] = mapped_column(String(16))
    potential_score: Mapped[float] = mapped_column(Float)
    learning_agility: Mapped[float] = mapped_column(Float, nullable=True)
    leadership: Mapped[float] = mapped_column(Float, nullable=True)
    mobility: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否接受轮岗 / 异地

    employee: Mapped["Employee"] = relationship(back_populates="potentials")


class Competency(Base, TimestampMixin):
    """能力模型项。"""

    __tablename__ = "competency"

    name: Mapped[str] = mapped_column(String(64), unique=True)
    category: Mapped[str] = mapped_column(String(16))  # 专业 / 管理 / 通用


class EmployeeCompetency(Base, TimestampMixin):
    """员工能力现状与目标等级，用于计算能力差距。"""

    __tablename__ = "employee_competency"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    competency_id: Mapped[int] = mapped_column(ForeignKey("competency.id"))
    current_level: Mapped[int] = mapped_column(Integer)  # 1-5
    required_level: Mapped[int] = mapped_column(Integer)  # 1-5

    employee: Mapped["Employee"] = relationship(back_populates="competencies")
    competency: Mapped["Competency"] = relationship()


__all__ = [
    "Competency",
    "Employee",
    "EmployeeCompetency",
    "PerformanceRecord",
    "PotentialAssessment",
]
