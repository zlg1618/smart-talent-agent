"""核心域 · 人才发展 Tool：把自然语言请求转成确定性计算调用。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Employee
from app.services import talent_development_service

POOL_TYPE_KEYWORDS = {
    "高潜": ["高潜"],
    "后备": ["后备", "接班"],
    "专家": ["专家"],
    "新锐": ["新锐", "应届", "新人"],
}

PROGRAM_TYPE_KEYWORDS = {
    "培养项目": ["培养项目", "人才项目"],
    "行动学习": ["行动学习"],
    "训练营": ["训练营", "集训"],
    "轮岗": ["轮岗"],
}


def _find_department(db: Session, message: str) -> str | None:
    departments = [
        d[0] for d in db.execute(select(Employee.department).distinct()).all() if d[0]
    ]
    departments.sort(key=len, reverse=True)
    for dep in departments:
        if dep in message:
            return dep
    return None


def run_competency_profile(
    db: Session,
    message: str,
    employee_name: str | None = None,
    department: str | None = None,
) -> dict:
    return talent_development_service.competency_profile(
        db,
        employee_name=employee_name,
        department=department or _find_department(db, message),
    )


def run_talent_standard_match(
    db: Session,
    message: str,
    employee_name: str | None = None,
    department: str | None = None,
    job_level: str | None = None,
) -> dict:
    return talent_development_service.talent_standard_match(
        db,
        employee_name=employee_name,
        department=department or _find_department(db, message),
        job_level=job_level,
    )


def run_talent_pool(
    db: Session, message: str, department: str | None = None
) -> dict:
    pool_type = None
    for key, words in POOL_TYPE_KEYWORDS.items():
        if any(w in message for w in words):
            pool_type = key
            break
    return talent_development_service.talent_pool_view(
        db, department=department or _find_department(db, message), pool_type=pool_type
    )


def run_development_program(db: Session, message: str) -> dict:
    program_type = None
    for key, words in PROGRAM_TYPE_KEYWORDS.items():
        if any(w in message for w in words):
            program_type = key
            break
    return talent_development_service.development_program_tracking(
        db, program_type=program_type
    )


def run_mentorship(
    db: Session, message: str, department: str | None = None
) -> dict:
    return talent_development_service.mentorship_view(
        db, department=department or _find_department(db, message)
    )


__all__ = [
    "run_competency_profile",
    "run_development_program",
    "run_mentorship",
    "run_talent_pool",
    "run_talent_standard_match",
]
