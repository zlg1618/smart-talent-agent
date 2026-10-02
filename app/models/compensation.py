"""HRIS · 薪酬与福利域（Compensation & Benefits）模型。

对齐 SuccessFactors Compensation / Variable Pay / Benefits 的核心实体：
职级薪酬带宽、员工薪酬包、福利计划、员工参保明细。
"""

from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class SalaryBand(Base, TimestampMixin):
    """职级薪酬带宽：每个职级在每个城市的中位值与上下限。"""

    __tablename__ = "salary_band"

    job_level: Mapped[str] = mapped_column(String(16))  # P4-P8 / M1-M3
    city: Mapped[str] = mapped_column(String(32))
    median: Mapped[int] = mapped_column(Integer)
    minimum: Mapped[int] = mapped_column(Integer)
    maximum: Mapped[int] = mapped_column(Integer)
    effective_date: Mapped[date] = mapped_column(Date)


class EmployeeCompensation(Base, TimestampMixin):
    """员工薪酬包：固定薪 + 浮动薪 + 长期激励。"""

    __tablename__ = "employee_compensation"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    employee_no: Mapped[str] = mapped_column(String(32), default="")  # 外部 HRIS 工号
    effective_date: Mapped[date] = mapped_column(Date)
    base_salary: Mapped[int] = mapped_column(Integer)  # 年度固定薪（元）
    target_bonus_pct: Mapped[float] = mapped_column(Float, default=0.0)  # 目标奖金比例
    equity_value: Mapped[int] = mapped_column(Integer, default=0)  # 年度股权/长期激励
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    pay_grade: Mapped[str] = mapped_column(String(16), default="")
    last_adjust_pct: Mapped[float] = mapped_column(Float, default=0.0)  # 上次调薪幅度
    last_adjust_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    employee: Mapped["Employee"] = relationship()


class BenefitPlan(Base, TimestampMixin):
    """福利计划：公司提供的福利项目与其覆盖规则。"""

    __tablename__ = "benefit_plan"

    name: Mapped[str] = mapped_column(String(64))  # 补充医疗、年度体检、企业年金…
    category: Mapped[str] = mapped_column(String(32))
    # insurance 保险 / health 健康 / allowance 津贴 / leave 假期 / equity 股权
    annual_cost: Mapped[int] = mapped_column(Integer)  # 人均年成本（元）
    is_core: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否全员核心福利
    eligible_levels: Mapped[str] = mapped_column(String(128), default="")  # 适用职级，逗号分隔
    description: Mapped[str] = mapped_column(Text, default="")


class EmployeeBenefit(Base, TimestampMixin):
    """员工参保 / 享受某福利计划的明细。"""

    __tablename__ = "employee_benefit"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    plan_id: Mapped[int] = mapped_column(ForeignKey("benefit_plan.id"))
    enrolled_at: Mapped[date] = mapped_column(Date)
    employee_contribution: Mapped[int] = mapped_column(Integer, default=0)  # 个人承担部分
    status: Mapped[str] = mapped_column(String(16), default="active")  # active / waived

    employee: Mapped["Employee"] = relationship()
    plan: Mapped["BenefitPlan"] = relationship()


__all__ = [
    "BenefitPlan",
    "EmployeeBenefit",
    "EmployeeCompensation",
    "SalaryBand",
]
