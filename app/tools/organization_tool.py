"""核心域 · 组织发展 Tool：把自然语言请求转成确定性计算调用。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Employee
from app.services import organization_service

CHANGE_TYPE_KEYWORDS = {
    "合并": ["合并"],
    "拆分": ["拆分", "分拆"],
    "扩编": ["扩编", "扩招", "增加编制"],
    "缩编": ["缩编", "裁员", "减少编制"],
    "新设": ["新设", "新建"],
    "调整": ["调整", "重组", "变革"],
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


def run_org_structure(
    db: Session, message: str, department: str | None = None, period: str | None = None
) -> dict:
    return organization_service.org_structure(
        db, department=department or _find_department(db, message), period=period
    )


def run_org_effectiveness(
    db: Session, message: str, department: str | None = None, period: str | None = None
) -> dict:
    return organization_service.org_effectiveness(
        db, department=department or _find_department(db, message), period=period
    )


def run_job_architecture(
    db: Session, message: str, department: str | None = None
) -> dict:
    return organization_service.job_architecture(
        db, department=department or _find_department(db, message)
    )


def run_org_change(
    db: Session, message: str, department: str | None = None
) -> dict:
    change_type = None
    for key, words in CHANGE_TYPE_KEYWORDS.items():
        if any(w in message for w in words):
            change_type = key
            break
    return organization_service.org_change_simulation(
        db,
        department=department or _find_department(db, message),
        change_type=change_type,
    )


__all__ = [
    "run_job_architecture",
    "run_org_change",
    "run_org_effectiveness",
    "run_org_structure",
]
