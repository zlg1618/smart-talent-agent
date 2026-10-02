"""HRIS · 人力资源规划域接口：编制审查、供需预测、离职风险、继任联动。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.tools import workforce_tool

router = APIRouter(prefix="/workforce", tags=["HRIS-人力资源规划"])


@router.get("/headcount")
def headcount(
    department: str | None = Query(None),
    period: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """编制达成审查。"""
    return workforce_tool.run_headcount_review(
        db, message="编制审查", department=department, period=period
    )


@router.get("/forecast")
def forecast(
    department: str | None = Query(None),
    scenario: str = Query("baseline", description="conservative / baseline / aggressive"),
    db: Session = Depends(get_db),
):
    """人力供需预测。"""
    label = {"conservative": "保守", "baseline": "基准", "aggressive": "激进"}.get(
        scenario, "基准"
    )
    return workforce_tool.run_supply_demand_forecast(
        db, message=f"{label}情景", department=department
    )


@router.get("/attrition-risk")
def attrition_risk(
    department: str | None = Query(None),
    only_high: bool = Query(False, description="只看高风险"),
    db: Session = Depends(get_db),
):
    return workforce_tool.run_attrition_risk(
        db, message="高风险" if only_high else "离职风险", department=department
    )


@router.get("/succession-link")
def succession_link(db: Session = Depends(get_db)):
    """离职风险 × 继任覆盖的交叉分析。"""
    return workforce_tool.run_succession_coverage_link(db, message="")
