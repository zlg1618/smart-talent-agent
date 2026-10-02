"""个人发展计划 Tool。"""

from sqlalchemy.orm import Session

from app.services import idp_service


def run_idp(
    db: Session,
    name: str | None = None,
    employee_id: int | None = None,
    period: str | None = None,
    max_gaps: int = 3,
) -> dict:
    """生成员工个人发展计划建议。"""
    return idp_service.build_idp(
        db,
        name=name,
        employee_id=employee_id,
        period=period,
        max_gaps=max_gaps,
    )
