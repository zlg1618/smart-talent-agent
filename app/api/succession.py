"""继任地图与人才梯队接口。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.tools import succession_tool

router = APIRouter(prefix="/api/succession", tags=["继任与梯队"])


@router.get("/map")
def succession_map(
    department: str | None = Query(None, description="部门"),
    criticality: str | None = Query(None, description="重要级别：高 / 中 / 低"),
    exclude_readiness: list[str] | None = Query(
        None, description="排除的准备度，如 not_ready"
    ),
    db: Session = Depends(get_db),
):
    return succession_tool.run_succession_map(
        db,
        department=department,
        criticality=criticality,
        exclude_readiness=exclude_readiness,
    )


@router.get("/pipeline")
def pipeline(
    department: str | None = Query(None, description="部门"),
    db: Session = Depends(get_db),
):
    return succession_tool.run_talent_pipeline(db, department=department)
