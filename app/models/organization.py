"""核心域 · 组织发展（Organization Development）模型。

组织发展关注"组织如何长得好"，覆盖四类事实：
    OrgUnit           组织单元：隶属关系、层级、负责人、编制与在编
    OrgEffectiveness  组织效能：部门营收、人工成本、离职率与管理幅度
    JobArchitecture   岗位职级体系：职族职级的人数、晋升率与薪酬带宽
    OrgChange         组织变革方案：类型、影响人数与成本影响
"""

from datetime import date

from sqlalchemy import Date, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class OrgUnit(Base, TimestampMixin):
    """组织单元：部门、中心、团队等管理实体。"""

    __tablename__ = "org_unit"

    name: Mapped[str] = mapped_column(String(64))
    department: Mapped[str] = mapped_column(String(64))
    parent_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=1)  # 1=公司，2=中心，3=部门，4=团队
    unit_type: Mapped[str] = mapped_column(String(16), default="部门")  # 中心/部门/团队/小组
    manager_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    planned_headcount: Mapped[int] = mapped_column(Integer, default=0)
    actual_headcount: Mapped[int] = mapped_column(Integer, default=0)
    period: Mapped[str] = mapped_column(String(16), default="2025H1")


class OrgEffectiveness(Base, TimestampMixin):
    """组织效能：以部门为单位的产出与成本数据。"""

    __tablename__ = "org_effectiveness"

    department: Mapped[str] = mapped_column(String(64))
    period: Mapped[str] = mapped_column(String(16))
    headcount: Mapped[int] = mapped_column(Integer, default=0)
    revenue: Mapped[float] = mapped_column(Float, default=0.0)  # 营收（万元）
    labor_cost: Mapped[float] = mapped_column(Float, default=0.0)  # 人工成本（万元）
    attrition_rate: Mapped[float] = mapped_column(Float, default=0.0)
    span_of_control: Mapped[float] = mapped_column(Float, default=0.0)  # 平均管理幅度


class JobArchitecture(Base, TimestampMixin):
    """岗位职级体系：职族职级的人数结构、晋升率与薪酬带宽。"""

    __tablename__ = "job_architecture"

    department: Mapped[str] = mapped_column(String(64))
    job_family: Mapped[str] = mapped_column(String(32))  # 技术/产品/销售/职能
    job_level: Mapped[str] = mapped_column(String(8))  # P4-P8 / M1-M3
    headcount: Mapped[int] = mapped_column(Integer, default=0)
    target_ratio: Mapped[float] = mapped_column(Float, default=0.0)  # 规划占比
    avg_tenure: Mapped[float] = mapped_column(Float, default=0.0)  # 平均司龄（年）
    promotion_rate: Mapped[float] = mapped_column(Float, default=0.0)  # 年晋升率
    salary_min: Mapped[int] = mapped_column(Integer, default=0)  # 带宽下限（元/月）
    salary_mid: Mapped[int] = mapped_column(Integer, default=0)
    salary_max: Mapped[int] = mapped_column(Integer, default=0)


class OrgChange(Base, TimestampMixin):
    """组织变革方案：合并 / 拆分 / 扩编 / 缩编 / 新设 / 调整。"""

    __tablename__ = "org_change"

    name: Mapped[str] = mapped_column(String(128))
    department: Mapped[str] = mapped_column(String(64))
    change_type: Mapped[str] = mapped_column(String(16))  # 合并/拆分/扩编/缩编/新设/调整
    source_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    affected_headcount: Mapped[int] = mapped_column(Integer, default=0)
    cost_impact: Mapped[float] = mapped_column(Float, default=0.0)  # 成本影响（万元/年）
    status: Mapped[str] = mapped_column(String(16), default="待审批")
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")


__all__ = ["JobArchitecture", "OrgChange", "OrgEffectiveness", "OrgUnit"]
