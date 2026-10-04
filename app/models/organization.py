"""核心域 · 组织发展（Organization Development）模型。

组织发展的对象是组织、团队、架构、机制与文化，关注"组织能力"，覆盖六类工作：

    组织诊断        OrgHealthSurvey / OrgScan（7S、6-BOX、五维框架）
    架构与管控设计  OrgUnit（含管控模式、分权授权、定岗定编）
    战略解码        StrategicGoal（公司战略 → 组织目标 → 部门目标）
    组织变革管理    OrgChange（含变革阻力与推进阶段）
    文化与氛围      CultureSurvey（文化建设、组织氛围、员工敬业度）
    组织效能        OrgEffectiveness / JobArchitecture（人效与人力成本）
"""

from datetime import date

from sqlalchemy import Date, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class OrgUnit(Base, TimestampMixin):
    """组织单元：部门、中心、团队等管理实体，含管控模式与权责划分。"""

    __tablename__ = "org_unit"

    name: Mapped[str] = mapped_column(String(64))
    department: Mapped[str] = mapped_column(String(64))
    parent_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=1)  # 1=公司，2=中心，3=部门，4=团队
    unit_type: Mapped[str] = mapped_column(String(16), default="部门")  # 中心/部门/团队/小组
    manager_name: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # ---- 架构与管控设计 ----
    org_model: Mapped[str] = mapped_column(String(16), default="职能制")
    # 职能制 / 事业部制 / 矩阵制 / 项目制 / 平台制
    control_mode: Mapped[str] = mapped_column(String(16), default="战略管控")
    # 战略管控 / 财务管控 / 操作管控
    authority: Mapped[str] = mapped_column(String(16), default="分权")
    # 集权 / 分权 / 混合
    decision_rights: Mapped[str] = mapped_column(Text, default="")  # 权责划分说明

    planned_headcount: Mapped[int] = mapped_column(Integer, default=0)
    actual_headcount: Mapped[int] = mapped_column(Integer, default=0)
    period: Mapped[str] = mapped_column(String(16), default="2025H1")


class OrgHealthSurvey(Base, TimestampMixin):
    """组织健康度调研：按维度收集员工主观评分，识别组织痛点。"""

    __tablename__ = "org_health_survey"

    department: Mapped[str] = mapped_column(String(64))
    period: Mapped[str] = mapped_column(String(16))
    dimension: Mapped[str] = mapped_column(String(32))
    # 战略清晰 / 组织架构 / 流程效率 / 人才供给 / 文化氛围 / 激励机制 / 协同效率
    score: Mapped[float] = mapped_column(Float, default=0.0)  # 1-5 分
    benchmark: Mapped[float] = mapped_column(Float, default=3.6)  # 行业参考值
    sample: Mapped[int] = mapped_column(Integer, default=0)


class OrgScan(Base, TimestampMixin):
    """组织扫描：按诊断框架逐维度打分，定位瓶颈。

    framework:
        seven_s    麦肯锡 7S：战略/结构/制度/共同价值观/风格/人员/技能
        six_box    Weisbord 6-BOX：使命目标/组织/关系/激励/领导/支持
        five_dim   五维诊断框架：战略/组织/人才/机制/文化
    """

    __tablename__ = "org_scan"

    department: Mapped[str] = mapped_column(String(64))
    period: Mapped[str] = mapped_column(String(16))
    framework: Mapped[str] = mapped_column(String(16))  # seven_s / six_box / five_dim
    dimension: Mapped[str] = mapped_column(String(32))
    current_score: Mapped[float] = mapped_column(Float, default=0.0)  # 1-5
    target_score: Mapped[float] = mapped_column(Float, default=4.0)
    issue: Mapped[str] = mapped_column(Text, default="")  # 已识别的痛点描述
    owner: Mapped[str] = mapped_column(String(32), default="")  # 责任方


class StrategicGoal(Base, TimestampMixin):
    """战略解码：公司战略逐层拆解为组织目标与部门目标。"""

    __tablename__ = "strategic_goal"

    level: Mapped[str] = mapped_column(String(16))  # 公司 / 组织 / 部门
    parent_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(128))
    owner_department: Mapped[str] = mapped_column(String(64), default="")
    metric: Mapped[str] = mapped_column(String(64), default="")  # 衡量指标
    target_value: Mapped[float] = mapped_column(Float, default=0.0)
    current_value: Mapped[float] = mapped_column(Float, default=0.0)
    weight: Mapped[float] = mapped_column(Float, default=0.0)  # 权重 0-1
    period: Mapped[str] = mapped_column(String(16), default="2025H1")
    status: Mapped[str] = mapped_column(String(16), default="进行中")


class CultureSurvey(Base, TimestampMixin):
    """企业文化与组织氛围调研：价值观落地、氛围感知与敬业度。"""

    __tablename__ = "culture_survey"

    department: Mapped[str] = mapped_column(String(64))
    period: Mapped[str] = mapped_column(String(16))
    dimension: Mapped[str] = mapped_column(String(32))
    # 价值观认同 / 协作氛围 / 心理安全 / 管理风格 / 成长空间 / 敬业度
    score: Mapped[float] = mapped_column(Float, default=0.0)  # 1-5
    sample: Mapped[int] = mapped_column(Integer, default=0)
    initiative: Mapped[str] = mapped_column(Text, default="")  # 对应文化举措


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
    """组织变革方案：业务扩张 / 并购 / 转型过程中的变革推进。

    stage 用于变革管理：宣贯 → 试点 → 推广 → 固化；
    resistance 记录变革阻力等级与来源，是变革管理的核心输入。
    """

    __tablename__ = "org_change"

    name: Mapped[str] = mapped_column(String(128))
    department: Mapped[str] = mapped_column(String(64))
    change_type: Mapped[str] = mapped_column(String(16))  # 合并/拆分/扩编/缩编/新设/调整/并购/转型
    source_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    affected_headcount: Mapped[int] = mapped_column(Integer, default=0)
    cost_impact: Mapped[float] = mapped_column(Float, default=0.0)  # 成本影响（万元/年）
    status: Mapped[str] = mapped_column(String(16), default="待审批")
    stage: Mapped[str] = mapped_column(String(16), default="宣贯")  # 宣贯/试点/推广/固化
    resistance: Mapped[str] = mapped_column(String(16), default="中")  # 高/中/低 变革阻力
    resistance_source: Mapped[str] = mapped_column(Text, default="")
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")


__all__ = [
    "CultureSurvey",
    "JobArchitecture",
    "OrgChange",
    "OrgEffectiveness",
    "OrgHealthSurvey",
    "OrgScan",
    "OrgUnit",
    "StrategicGoal",
]
