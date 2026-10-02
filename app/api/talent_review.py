"""人才盘点接口（不经过大模型，直接返回确定性计算结果）。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.tools import talent_review_tool

router = APIRouter(prefix="/api/talent", tags=["人才盘点"])


@router.get("/review")
def talent_review(
    department: str | None = Query(None, description="部门，为空表示全公司"),
    period: str | None = Query(None, description="考核周期，如 2025H1，为空取最新"),
    job_level: str | None = Query(None, description="职级，如 P6"),
    only_grid: list[str] | None = Query(None, description="只保留的格子，如 高-高"),
    db: Session = Depends(get_db),
):
    return talent_review_tool.run_talent_review(
        db,
        department=department,
        period=period,
        job_level=job_level,
        only_grid=only_grid,
    )


@router.get("/locate")
def locate(
    name: str = Query(..., description="员工姓名"),
    period: str | None = Query(None, description="考核周期"),
    db: Session = Depends(get_db),
):
    return talent_review_tool.run_locate_employee(db, name, period)
