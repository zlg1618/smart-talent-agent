"""组织诊断 Tool。"""

from sqlalchemy.orm import Session

from app.services import diagnosis_service


def run_org_diagnosis(
    db: Session, department: str | None = None, period: str | None = None
) -> dict:
    """生成组织诊断结果。"""
    return diagnosis_service.build_org_diagnosis(db, department=department, period=period)
