"""HRIS · 薪酬与福利域接口：公平性、调薪模拟、福利覆盖、个人薪酬单。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.tools import compensation_tool

router = APIRouter(prefix="/compensation", tags=["HRIS-薪酬与福利"])


@router.get("/compa-ratio")
def compa_ratio(
    department: str | None = Query(None),
    job_level: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """全员 compa-ratio 与外部竞争力分析。"""
    return compensation_tool.run_compa_ratio(
        db, message="薪酬公平性", department=department, job_level=job_level
    )


@router.get("/adjustment")
def adjustment(
    department: str | None = Query(None),
    budget_pct: float = Query(5.0, description="调薪池比例（百分数）"),
    db: Session = Depends(get_db),
):
    """调薪预算模拟，优先补齐低于带宽下限的人。"""
    return compensation_tool.run_salary_adjustment(
        db, message=f"{budget_pct}% 调薪", department=department
    )


@router.get("/benefits")
def benefits(
    department: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """福利参保覆盖与人均成本。"""
    return compensation_tool.run_benefits(db, message="福利", department=department)


@router.get("/summary")
def summary(
    name: str = Query(..., description="员工姓名"),
    db: Session = Depends(get_db),
):
    """单人薪酬总览：TCC / TDC / 带宽位置 / 福利清单。"""
    return compensation_tool.run_compensation_summary(db, message=name)
