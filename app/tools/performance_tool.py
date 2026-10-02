"""HRIS · 绩效管理域 Tool：目标达成、评价偏差、强制分布、改进计划。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Employee
from app.services import performance_service


def _find_department(db: Session, message: str) -> str | None:
    departments = [
        d[0] for d in db.execute(select(Employee.department).distinct()).all() if d[0]
    ]
    departments.sort(key=len, reverse=True)
    for dep in departments:
        if dep in message:
            return dep
    return None


def run_goal_achievement(
    db: Session, message: str, department: str | None = None, period: str | None = None
) -> dict:
    return performance_service.goal_achievement(
        db, department=department or _find_department(db, message), period=period
    )


def run_review_deviation(
    db: Session, message: str, department: str | None = None, period: str | None = None
) -> dict:
    return performance_service.review_deviation(
        db, department=department or _find_department(db, message), period=period
    )


def run_distribution_check(
    db: Session, message: str, department: str | None = None, period: str | None = None
) -> dict:
    return performance_service.distribution_check(
        db, department=department or _find_department(db, message), period=period
    )


def run_improvement_tracking(
    db: Session, message: str, department: str | None = None
) -> dict:
    return performance_service.improvement_tracking(
        db, department=department or _find_department(db, message)
    )


__all__ = [
    "run_distribution_check",
    "run_goal_achievement",
    "run_improvement_tracking",
    "run_review_deviation",
]
