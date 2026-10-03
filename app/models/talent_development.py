"""核心域 · 人才发展（Talent Development）模型。

人才发展关注"人如何长起来"，回答四个问题：
    标准是否清晰    各职族职级的任职资格要求与达标线
    池子是否活跃    人才池进出、分层与活跃度
    项目是否有效    培养项目的覆盖率、完成率与满意度
    带教是否落地    导师制的配对率、带教频次与覆盖

注意：本域不包含人才盘点九宫格、继任地图、人才梯队与个人发展计划（IDP），
这些能力已从系统中移除，人才发展聚焦"标准 - 池子 - 项目 - 带教"四条主线。
"""

from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class TalentStandard(Base, TimestampMixin):
    """任职资格标准：某职族某职级在某维度上的要求与权重。"""

    __tablename__ = "talent_standard"

    job_family: Mapped[str] = mapped_column(String(32))
    job_level: Mapped[str] = mapped_column(String(8))
    dimension: Mapped[str] = mapped_column(String(32))  # 专业能力/业务贡献/领导力/文化契合
    requirement: Mapped[str] = mapped_column(Text, default="")  # 达标行为描述
    weight: Mapped[float] = mapped_column(Float, default=0.25)  # 维度权重，合计 1.0
    pass_score: Mapped[float] = mapped_column(Float, default=3.0)  # 达标线（1-5 分制）


class TalentPool(Base, TimestampMixin):
    """人才池成员：入池、分层、流动与出池。"""

    __tablename__ = "talent_pool"

    pool_name: Mapped[str] = mapped_column(String(64))  # 高潜池 / 管理后备池 / 专家池
    pool_type: Mapped[str] = mapped_column(String(16))  # 高潜 / 后备 / 专家 / 新锐
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    stage: Mapped[str] = mapped_column(String(16), default="在池")  # 在池 / 观察 / 已出池
    tag: Mapped[str] = mapped_column(String(32), default="")  # 标签：跨部门 / 国际化 等
    score: Mapped[float] = mapped_column(Float, default=0.0)  # 入池评估分（0-100）
    entered_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    employee: Mapped["Employee"] = relationship()


class DevelopmentProgram(Base, TimestampMixin):
    """发展项目：培养项目 / 行动学习 / 训练营的运行数据。"""

    __tablename__ = "development_program"

    name: Mapped[str] = mapped_column(String(128))
    program_type: Mapped[str] = mapped_column(String(16))  # 培养项目/行动学习/训练营/轮岗
    audience: Mapped[str] = mapped_column(String(64), default="")  # 目标人群
    capacity: Mapped[int] = mapped_column(Integer, default=0)  # 计划容量
    enrolled: Mapped[int] = mapped_column(Integer, default=0)  # 实际入学
    completed: Mapped[int] = mapped_column(Integer, default=0)  # 完成人数
    satisfaction: Mapped[float] = mapped_column(Float, default=0.0)  # 满意度（1-5）
    budget: Mapped[float] = mapped_column(Float, default=0.0)  # 预算（万元）
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class Mentorship(Base, TimestampMixin):
    """导师带教：一对一带教关系的运行记录。"""

    __tablename__ = "mentorship"

    mentor_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    mentee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    topic: Mapped[str] = mapped_column(String(128), default="")
    session_count: Mapped[int] = mapped_column(Integer, default=0)  # 已完成带教次数
    planned_sessions: Mapped[int] = mapped_column(Integer, default=6)
    status: Mapped[str] = mapped_column(String(16), default="进行中")  # 进行中/已完成/已中止
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    mentor: Mapped["Employee"] = relationship(foreign_keys=[mentor_id])
    mentee: Mapped["Employee"] = relationship(foreign_keys=[mentee_id])


__all__ = ["DevelopmentProgram", "Mentorship", "TalentPool", "TalentStandard"]
