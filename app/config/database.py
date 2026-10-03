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
    AttritionRisk,
    AttendanceRecord,
    BenefitPlan,
    CalibrationSession,
    Candidate,
    CandidateSkill,
    Competency,
    DevelopmentProgram,
    Employee,
    EmployeeBenefit,
    EmployeeCompensation,
    EmployeeCompetency,
    EngagementSurvey,
    HeadcountPlan,
    ImprovementPlan,
    InterviewSchedule,
    JobArchitecture,
    JobPost,
    LeaveRequest,
    Mentorship,
    OfferRecord,
    OrgChange,
    OrgEffectiveness,
    OrgUnit,
    PerformanceGoal,
    PerformanceRecord,
    PerformanceReview,
    PotentialAssessment,
    RelationCase,
    SalaryBand,
    TalentPool,
    TalentStandard,
    TrainingCourse,
    TrainingEnrollment,
    WorkforceForecast,
)

    Base.metadata.create_all(bind=engine)
    _sync_sqlite_columns()


def _sync_sqlite_columns() -> None:
    """SQLite 不会自动加列，建表后补齐模型新增的列。"""
    try:
        from app.config.migrate import add_missing_columns

        added = add_missing_columns(engine)
        if added:
            print(f"[schema] 已补齐 {len(added)} 个列")
    except Exception as exc:  # 迁移失败不应阻断启动
        print(f"[schema] 列同步跳过：{exc}")
