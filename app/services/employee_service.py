"""员工与评价数据的查询服务。

所有评价数据都从数据库中读取，绝不由大模型生成。
"""

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import (
    Employee,
    PerformanceRecord,
    PotentialAssessment,
)


def list_employees(
    db: Session,
    department: str | None = None,
    job_level: str | None = None,
    keyword: str | None = None,
    status: str = "在职",
) -> list[Employee]:
    stmt = select(Employee).where(Employee.status == status)
    if department:
        stmt = stmt.where(Employee.department == department)
    if job_level:
        stmt = stmt.where(Employee.job_level == job_level)
    if keyword:
        stmt = stmt.where(
            (Employee.name.like(f"%{keyword}%"))
            | (Employee.position_title.like(f"%{keyword}%"))
        )
    return list(db.execute(stmt.order_by(Employee.id)).scalars().all())


def get_employee_by_name(db: Session, name: str) -> Employee | None:
    stmt = select(Employee).where(Employee.name == name)
    return db.execute(stmt).scalars().first()


def get_latest_period(db: Session) -> str | None:
    """最新考核周期，用于默认盘点周期。"""
    stmt = select(PerformanceRecord.period).distinct().order_by(desc(PerformanceRecord.period))
    return db.execute(stmt).scalars().first()


def get_performance(
    db: Session, employee_id: int, period: str | None = None
) -> PerformanceRecord | None:
    stmt = select(PerformanceRecord).where(
        PerformanceRecord.employee_id == employee_id
    )
    if period:
        stmt = stmt.where(PerformanceRecord.period == period)
    stmt = stmt.order_by(desc(PerformanceRecord.period))
    return db.execute(stmt).scalars().first()


def get_potential(
    db: Session, employee_id: int, period: str | None = None
) -> PotentialAssessment | None:
    stmt = select(PotentialAssessment).where(
        PotentialAssessment.employee_id == employee_id
    )
    if period:
        stmt = stmt.where(PotentialAssessment.period == period)
    stmt = stmt.order_by(desc(PotentialAssessment.period))
    return db.execute(stmt).scalars().first()


def list_departments(db: Session) -> list[str]:
    stmt = select(Employee.department).distinct().order_by(Employee.department)
    return list(db.execute(stmt).scalars().all())


def count_employees(db: Session, department: str | None = None) -> int:
    stmt = select(func.count(Employee.id)).where(Employee.status == "在职")
    if department:
        stmt = stmt.where(Employee.department == department)
    return int(db.execute(stmt).scalar() or 0)
