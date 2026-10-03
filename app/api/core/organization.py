"""核心域 · 组织发展接口：架构编制、组织效能、职级体系、变革模拟。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.tools import organization_tool

router = APIRouter(prefix="/organization-development", tags=["核心-组织发展"])


@router.get("/structure")
def structure(
    department: str | None = Query(None),
    period: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """组织架构与编制总览：层级深度、管理幅度、编制达成。"""
    return organization_tool.run_org_structure(
        db, message="组织架构", department=department, period=period
    )


@router.get("/effectiveness")
def effectiveness(
    department: str | None = Query(None),
    period: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """组织效能分析：人均产出、人工成本率、人效排名。"""
    return organization_tool.run_org_effectiveness(
        db, message="组织效能", department=department, period=period
    )


@router.get("/job-architecture")
def job_architecture(
    department: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """岗位职级体系：金字塔分布、晋升率与职级拥堵。"""
    return organization_tool.run_job_architecture(
        db, message="职级体系", department=department
    )


@router.get("/change")
def change(
    department: str | None = Query(None),
    change_type: str | None = Query(
        None, description="合并 / 拆分 / 扩编 / 缩编 / 新设 / 调整"
    ),
    db: Session = Depends(get_db),
):
    """组织变革模拟：影响人数与成本测算。"""
    return organization_tool.run_org_change(
        db, message=change_type or "组织变革", department=department
    )
