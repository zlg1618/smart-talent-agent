"""HRIS · 培训与开发域 Tool：培训总览、必修合规、课程推荐、效果评估。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Employee
from app.services import learning_service


def _find_employee(db: Session, message: str) -> Employee | None:
    rows = db.execute(select(Employee).distinct()).scalars().all()
    for emp in rows:
        if emp.name and emp.name in message:
            return emp
    return None


def _find_department(db: Session, message: str) -> str | None:
    departments = [
        d[0] for d in db.execute(select(Employee.department).distinct()).all() if d[0]
    ]
    departments.sort(key=len, reverse=True)
    for dep in departments:
        if dep in message:
            return dep
    return None


def run_training_overview(db: Session, message: str, department: str | None = None) -> dict:
    return learning_service.training_overview(
        db, department=department or _find_department(db, message)
    )


def run_mandatory_compliance(
    db: Session, message: str, department: str | None = None
) -> dict:
    return learning_service.mandatory_compliance(
        db, department=department or _find_department(db, message)
    )


def run_recommend_courses(
    db: Session, message: str, employee_name: str | None = None, top: int = 5
) -> dict:
    if not employee_name:
        emp = _find_employee(db, message)
        if not emp:
            return {"error": "请指定员工姓名，例如：给李伟推荐培训"}
        employee_name = emp.name
    return learning_service.recommend_courses(db, employee_name, top=top)


def run_learning_effectiveness(
    db: Session, message: str, department: str | None = None
) -> dict:
    return learning_service.learning_effectiveness(
        db, department=department or _find_department(db, message)
    )


__all__ = [
    "run_learning_effectiveness",
    "run_mandatory_compliance",
    "run_recommend_courses",
    "run_training_overview",
]
