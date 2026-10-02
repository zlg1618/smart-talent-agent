"""继任与梯队 Tool。"""

from sqlalchemy.orm import Session

from app.services import succession_service


def run_succession_map(
    db: Session,
    department: str | None = None,
    criticality: str | None = None,
    exclude_readiness: list[str] | None = None,
) -> dict:
    """生成关键岗位继任地图。"""
    return succession_service.build_succession_map(
        db,
        department=department,
        criticality=criticality,
        exclude_readiness=exclude_readiness,
    )


def run_talent_pipeline(db: Session, department: str | None = None) -> dict:
    """生成人才梯队分析。"""
    return succession_service.build_talent_pipeline(db, department=department)
