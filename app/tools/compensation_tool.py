"""HRIS · 薪酬与福利域 Tool：外部公平性、调薪模拟、福利覆盖、个人薪酬单。"""

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Employee
from app.services import compensation_service

_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")


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


def run_compa_ratio(
    db: Session, message: str, department: str | None = None, job_level: str | None = None
) -> dict:
    department = department or _find_department(db, message)
    return compensation_service.compa_ratio_analysis(
        db, department=department, job_level=job_level
    )


def run_salary_adjustment(
    db: Session, message: str, department: str | None = None
) -> dict:
    department = department or _find_department(db, message)
    m = _PCT_RE.search(message)
    budget_pct = float(m.group(1)) if m else 5.0
    if budget_pct <= 0 or budget_pct > 50:
        budget_pct = 5.0
    return compensation_service.salary_adjustment_simulation(
        db, department=department, budget_pct=budget_pct
    )


def run_benefits(db: Session, message: str, department: str | None = None) -> dict:
    department = department or _find_department(db, message)
    return compensation_service.benefits_analysis(db, department=department)


def run_compensation_summary(
    db: Session, message: str, employee_name: str | None = None
) -> dict:
    if not employee_name:
        emp = _find_employee(db, message)
        if not emp:
            return {"error": "请指定员工姓名，例如：查一下张伟的薪酬总览"}
        employee_name = emp.name
    return compensation_service.compensation_summary(db, employee_name)


__all__ = [
    "run_benefits",
    "run_compa_ratio",
    "run_compensation_summary",
    "run_salary_adjustment",
]
