"""数据库引擎与会话。

同时支持 SQLite 与 MySQL，通过 settings.database_url 切换。
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config.settings import get_settings


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


def _build_engine():
    settings = get_settings()
    url = settings.database_url

    kwargs = {"echo": settings.db_echo, "future": True}
    if url.startswith("sqlite"):
        # SQLite 在 FastAPI 多线程下需要关闭同线程检查
        kwargs["connect_args"] = {"check_same_thread": False}

    return create_engine(url, **kwargs)


engine = _build_engine()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    """FastAPI 依赖项：请求级数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """建表。导入所有模型后再调用，否则表不会被创建。"""
    from app.models import (  # noqa: F401
        Application,
        AttendanceRecord,
        Candidate,
        CandidateSkill,
        Competency,
        Course,
        DepartmentMetric,
        Employee,
        EmployeeCompetency,
        IDP,
        InterviewSchedule,
        JobPost,
        KeyPosition,
        LeaveRequest,
        OfferRecord,
        PerformanceRecord,
        PotentialAssessment,
        SuccessionPlan,
    )

    Base.metadata.create_all(bind=engine)
