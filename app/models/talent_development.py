"""核心域 · 人才发展（Talent Development）模型。

人才发展的对象是人、个体与人才梯队，关注"人的能力"，覆盖七类工作：

    人才盘点      Review360（360 度评估）+ 绩效/潜力数据 → 九宫格与高潜识别
    胜任力模型    CompetencyLevel / PositionCompetency（等级行为 + 岗位要求）
    任职资格      TalentStandard（职族职级四维达标线）
    继任与梯队    KeyPosition / SuccessionCandidate
    高潜培养      DevelopmentProgram（训练营 / 管理者训练营 / 行动学习）
    学习发展体系  DevelopmentPlan（IDP）/ Mentorship（导师制）/ 轮岗
    人才任用      由盘点 + 任职资格 + 离职风险综合输出建议
"""

from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class CompetencyLevel(Base, TimestampMixin):
    """胜任力模型的等级行为描述：每一级"做到什么算达到"。"""

    __tablename__ = "competency_level"

    competency_id: Mapped[int] = mapped_column(ForeignKey("competency.id"))
    level: Mapped[int] = mapped_column(Integer)  # 1-5
    behavior: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[str] = mapped_column(Text, default="")  # 可观察的行为证据

    competency: Mapped["Competency"] = relationship()


class PositionCompetency(Base, TimestampMixin):
    """岗位能力要求：某职族某职级对各能力项的要求等级与权重。"""

    __tablename__ = "position_competency"

    job_family: Mapped[str] = mapped_column(String(32))
    job_level: Mapped[str] = mapped_column(String(8))
    competency_id: Mapped[int] = mapped_column(ForeignKey("competency.id"))
    required_level: Mapped[int] = mapped_column(Integer, default=3)
    weight: Mapped[float] = mapped_column(Float, default=0.2)

    competency: Mapped["Competency"] = relationship()


class Review360(Base, TimestampMixin):
    """360 度评估记录：不同评价角色对同一员工的同一维度打分。"""

    __tablename__ = "review_360"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    period: Mapped[str] = mapped_column(String(16))
    rater_role: Mapped[str] = mapped_column(String(16))  # 上级/同级/下级/自评
    dimension: Mapped[str] = mapped_column(String(32))  # 专业能力/协作沟通/领导力/执行力
    score: Mapped[float] = mapped_column(Float, default=0.0)  # 1-5

    employee: Mapped["Employee"] = relationship()


class KeyPosition(Base, TimestampMixin):
    """关键岗位：空缺风险越高，继任梯队建设优先级越高。"""

    __tablename__ = "key_position"

    title: Mapped[str] = mapped_column(String(64))
    department: Mapped[str] = mapped_column(String(64))
    job_level: Mapped[str] = mapped_column(String(8))
    incumbent_id: Mapped[int | None] = mapped_column(
        ForeignKey("employee.id"), nullable=True
    )
    criticality: Mapped[str] = mapped_column(String(8))  # 高 / 中 / 低
    vacancy_risk: Mapped[str] = mapped_column(String(8), default="中")  # 高/中/低

    successors: Mapped[list["SuccessionCandidate"]] = relationship(
        back_populates="key_position", cascade="all, delete-orphan"
    )


class SuccessionCandidate(Base, TimestampMixin):
    """继任候选人：关键岗位的接班人及其准备度。

    readiness:
        ready_now  立即就绪
        ready_1y   1 年内就绪
        ready_2y   2 年内就绪
        not_ready  尚未就绪
    """

    __tablename__ = "succession_candidate"

    key_position_id: Mapped[int] = mapped_column(ForeignKey("key_position.id"))
    candidate_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    readiness: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(16), default="内部")  # 内部 / 外部储备
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    key_position: Mapped["KeyPosition"] = relationship(back_populates="successors")
    candidate: Mapped["Employee"] = relationship()


class TalentStandard(Base, TimestampMixin):
    """任职资格标准：某职族某职级在某维度上的要求与权重。"""

    __tablename__ = "talent_standard"

    job_family: Mapped[str] = mapped_column(String(32))
    job_level: Mapped[str] = mapped_column(String(8))
    dimension: Mapped[str] = mapped_column(String(32))  # 专业能力/业务贡献/领导力/学习敏锐
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
    tag: Mapped[str] = mapped_column(String(32), default="")
    score: Mapped[float] = mapped_column(Float, default=0.0)  # 入池评估分（0-100）
    entered_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    employee: Mapped["Employee"] = relationship()


class DevelopmentProgram(Base, TimestampMixin):
    """发展项目：高潜人才项目、管理者训练营、行动学习、轮岗等。"""

    __tablename__ = "development_program"

    name: Mapped[str] = mapped_column(String(128))
    program_type: Mapped[str] = mapped_column(String(16))
    # 高潜项目 / 管理者训练营 / 培养项目 / 行动学习 / 训练营 / 轮岗 / 内训
    audience: Mapped[str] = mapped_column(String(64), default="")
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    enrolled: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[int] = mapped_column(Integer, default=0)
    satisfaction: Mapped[float] = mapped_column(Float, default=0.0)
    budget: Mapped[float] = mapped_column(Float, default=0.0)  # 预算（万元）
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class DevelopmentPlan(Base, TimestampMixin):
    """个人发展计划 IDP：70-20-10 发展法则下的行动项。

    bucket: 70 在职历练 / 20 他人辅导 / 10 正式培训
    """

    __tablename__ = "development_plan"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    period: Mapped[str] = mapped_column(String(16))
    goal: Mapped[str] = mapped_column(String(255))
    competency_id: Mapped[int | None] = mapped_column(
        ForeignKey("competency.id"), nullable=True
    )
    bucket: Mapped[str] = mapped_column(String(8), default="70")  # 70 / 20 / 10
    action_type: Mapped[str] = mapped_column(String(16))  # 项目 / 轮岗 / 导师 / 培训
    action_name: Mapped[str] = mapped_column(String(128))
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="未开始")
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100

    employee: Mapped["Employee"] = relationship()
    competency: Mapped["Competency"] = relationship()


class Mentorship(Base, TimestampMixin):
    """导师带教：一对一带教关系的运行记录。"""

    __tablename__ = "mentorship"

    mentor_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    mentee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    topic: Mapped[str] = mapped_column(String(128), default="")
    session_count: Mapped[int] = mapped_column(Integer, default=0)
    planned_sessions: Mapped[int] = mapped_column(Integer, default=6)
    status: Mapped[str] = mapped_column(String(16), default="进行中")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    mentor: Mapped["Employee"] = relationship(foreign_keys=[mentor_id])
    mentee: Mapped["Employee"] = relationship(foreign_keys=[mentee_id])


__all__ = [
    "CompetencyLevel",
    "DevelopmentPlan",
    "DevelopmentProgram",
    "KeyPosition",
    "Mentorship",
    "PositionCompetency",
    "Review360",
    "SuccessionCandidate",
    "TalentPool",
    "TalentStandard",
]
