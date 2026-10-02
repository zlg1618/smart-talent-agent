"""ATS（招聘管理系统）模型：招聘需求、候选人、申请、面试、Offer。"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class JobPost(Base, TimestampMixin):
    """招聘需求 / JD。"""

    __tablename__ = "job_post"

    title: Mapped[str] = mapped_column(String(64))
    department: Mapped[str] = mapped_column(String(64))
    headcount: Mapped[int] = mapped_column(Integer, default=1)
    jd_text: Mapped[str] = mapped_column(Text)
    required_skills: Mapped[str] = mapped_column(String(255))  # 逗号分隔
    min_degree: Mapped[str] = mapped_column(String(16))  # bachelor / master / phd
    min_years: Mapped[float] = mapped_column(Float, default=0.0)
    salary_min: Mapped[int] = mapped_column(Integer)
    salary_max: Mapped[int] = mapped_column(Integer)
    hiring_manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("employee.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), default="open")  # open/closed/on_hold
    opened_at: Mapped[date] = mapped_column(Date)


class Candidate(Base, TimestampMixin):
    """候选人主数据。"""

    __tablename__ = "candidate"

    name: Mapped[str] = mapped_column(String(32))
    email: Mapped[str] = mapped_column(String(64))
    phone: Mapped[str] = mapped_column(String(32))
    current_title: Mapped[str] = mapped_column(String(64))
    current_company: Mapped[str] = mapped_column(String(64))
    years_exp: Mapped[float] = mapped_column(Float, default=0.0)
    degree: Mapped[str] = mapped_column(String(16))  # bachelor/master/phd
    expected_salary_min: Mapped[int] = mapped_column(Integer)
    expected_salary_max: Mapped[int] = mapped_column(Integer)
    resume_text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(32), default="direct")


class CandidateSkill(Base, TimestampMixin):
    """候选人技能明细。"""

    __tablename__ = "candidate_skill"

    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate.id"))
    skill: Mapped[str] = mapped_column(String(64))
    proficiency: Mapped[int] = mapped_column(Integer, default=3)  # 1-5
    years_used: Mapped[float] = mapped_column(Float, default=0.0)

    candidate: Mapped["Candidate"] = relationship()


class Application(Base, TimestampMixin):
    """候选人投递某职位的申请记录（招聘漏斗的一个环节）。"""

    __tablename__ = "application"

    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate.id"))
    job_post_id: Mapped[int] = mapped_column(ForeignKey("job_post.id"))
    applied_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(16), default="screening")
    # 漏斗阶段：screening / interview / offer / hired / rejected
    current_round: Mapped[str] = mapped_column(String(32), default="简历筛选")
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)

    candidate: Mapped["Candidate"] = relationship()
    job_post: Mapped["JobPost"] = relationship()


class InterviewSchedule(Base, TimestampMixin):
    """面试安排记录。"""

    __tablename__ = "interview_schedule"

    application_id: Mapped[int] = mapped_column(ForeignKey("application.id"))
    round_name: Mapped[str] = mapped_column(String(32))  # HR面 / 技术面 / 终面
    interviewer_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime)
    mode: Mapped[str] = mapped_column(String(16), default="onsite")  # onsite / online
    score: Mapped[int] = mapped_column(Integer, default=0)  # 1-5
    feedback: Mapped[str] = mapped_column(Text, default="")
    decision: Mapped[str] = mapped_column(String(16), default="pending")  # pass/fail/pending

    application: Mapped["Application"] = relationship()
    interviewer: Mapped["Employee"] = relationship()


class OfferRecord(Base, TimestampMixin):
    """Offer 记录，包含智能定薪建议与候选人最终接受的薪资结构。"""

    __tablename__ = "offer_record"

    application_id: Mapped[int] = mapped_column(ForeignKey("application.id"))
    base_salary: Mapped[int] = mapped_column(Integer)
    bonus: Mapped[int] = mapped_column(Integer, default=0)
    equity: Mapped[int] = mapped_column(Integer, default=0)
    total_package: Mapped[int] = mapped_column(Integer)  # 自动计算
    compa_ratio: Mapped[float] = mapped_column(Float)  # base / 岗位中位值
    start_date: Mapped[date] = mapped_column(Date)
    expires_at: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    # pending / accepted / declined / withdrawn
    decision_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    application: Mapped["Application"] = relationship()


__all__ = [
    "Application",
    "Candidate",
    "CandidateSkill",
    "InterviewSchedule",
    "JobPost",
    "OfferRecord",
]