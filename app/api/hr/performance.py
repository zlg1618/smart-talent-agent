"""HRIS · 绩效管理域接口：目标达成、评价偏差、强制分布、改进计划。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.tools import performance_tool

router = APIRouter(prefix="/performance", tags=["HRIS-绩效管理"])


@router.get("/goals")
def goals(
    department: str | None = Query(None),
    period: str | None = Query(None),
    db: Session = Depends(get_db),
):
    return performance_tool.run_goal_achievement(
        db, message="目标达成", department=department, period=period
    )


@router.get("/deviation")
def deviation(
    department: str | None = Query(None),
    period: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """自评与主管评的认知偏差。"""
    return performance_tool.run_review_deviation(
        db, message="评价偏差", department=department, period=period
    )


@router.get("/distribution")
def distribution(
    department: str | None = Query(None),
    period: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """强制分布校验。"""
    return performance_tool.run_distribution_check(
        db, message="强制分布", department=department, period=period
    )


@router.get("/improvement")
def improvement(
    department: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """绩效改进计划 PIP 跟进。"""
    return performance_tool.run_improvement_tracking(
        db, message="改进计划", department=department
    )
