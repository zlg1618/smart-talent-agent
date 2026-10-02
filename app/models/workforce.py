"""HRIS · 人力资源规划域（Workforce Planning）模型。

覆盖编制规划、人力需求预测、离职风险预测三大规划动作。
"""

from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class HeadcountPlan(Base, TimestampMixin):
    """部门编制计划：规划编制数与实际在编数对比。"""

    __tablename__ = "headcount_plan"

    department: Mapped[str] = mapped_column(String(64))
    period: Mapped[str] = mapped_column(String(16))  # 2025H1
    planned_headcount: Mapped[int] = mapped_column(Integer)
    actual_headcount: Mapped[int] = mapped_column(Integer, default=0)
    open_reqs: Mapped[int] = mapped_column(Integer, default=0)  # 在招需求数
    budget_amount: Mapped[int] = mapped_column(Integer, default=0)  # 人力预算（元/年）
    actual_cost: Mapped[int] = mapped_column(Integer, default=0)  # 实际人力成本
    approved_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")


class WorkforceForecast(Base, TimestampMixin):
    """人力需求预测：按部门与职级的未来需求测算。"""

    __tablename__ = "workforce_forecast"

    department: Mapped[str] = mapped_column(String(64))
    job_level: Mapped[str] = mapped_column(String(16))
    period: Mapped[str] = mapped_column(String(16))  # 预测所属周期
    current_supply: Mapped[int] = mapped_column(Integer, default=0)  # 当前供给
    natural_attrition: Mapped[float] = mapped_column(Float, default=0.0)  # 自然流失数
    demand_growth: Mapped[float] = mapped_column(Float, default=0.0)  # 业务增长带来的增量需求
    internal_supply: Mapped[int] = mapped_column(Integer, default=0)  # 内部可供给人数
    external_hire_need: Mapped[int] = mapped_column(Integer, default=0)  # 需外部招聘
    scenario: Mapped[str] = mapped_column(String(16), default="baseline")
    # conservative 保守 / baseline 基准 / aggressive 激进


class AttritionRisk(Base, TimestampMixin):
    """员工离职风险预测因子与评分。"""

    __tablename__ = "attrition_risk"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    period: Mapped[str] = mapped_column(String(16))
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    risk_level: Mapped[str] = mapped_column(String(16), default="low")  # low/medium/high
    # 风险因子（0-1）
    factor_tenure: Mapped[float] = mapped_column(Float, default=0.0)  # 司龄因子
    factor_performance: Mapped[float] = mapped_column(Float, default=0.0)  # 绩效因子
    factor_compensation: Mapped[float] = mapped_column(Float, default=0.0)  # 薪酬竞争力
    factor_promotion: Mapped[float] = mapped_column(Float, default=0.0)  # 晋升停滞
    factor_engagement: Mapped[float] = mapped_column(Float, default=0.0)  # 敬业度
    factor_market: Mapped[float] = mapped_column(Float, default=0.0)  # 市场热度
    key_reason: Mapped[str] = mapped_column(String(64), default="")
    retention_action: Mapped[str] = mapped_column(Text, default="")

    employee: Mapped["Employee"] = relationship()


__all__ = [
    "AttritionRisk",
    "HeadcountPlan",
    "WorkforceForecast",
]
