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
        None, description="合并 / 拆分 / 扩编 / 缩编 / 新设 / 调整 / 并购 / 转型"
    ),
    db: Session = Depends(get_db),
):
    """组织变革管理：影响人数、成本、阶段与变革阻力。"""
    return organization_tool.run_org_change(
        db, message=change_type or "组织变革", department=department
    )


@router.get("/diagnosis")
def diagnosis(
    department: str | None = Query(None),
    period: str | None = Query(None),
    framework: str | None = Query(None, description="seven_s / six_box / five_dim"),
    db: Session = Depends(get_db),
):
    """组织诊断：健康度调研 + 组织扫描（7S / 6-BOX / 五维框架）。"""
    label = {"seven_s": "7S", "six_box": "6-BOX", "five_dim": "五维"}.get(
        framework or "", "组织诊断"
    )
    return organization_tool.run_org_diagnosis(
        db, message=label, department=department, period=period
    )


@router.get("/strategy")
def strategy(
    department: str | None = Query(None),
    period: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """战略解码：公司目标 → 组织目标 → 部门目标的拆解与达成追踪。"""
    return organization_tool.run_strategy_decode(
        db, message="战略解码", department=department, period=period
    )


@router.get("/culture")
def culture(
    department: str | None = Query(None),
    period: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """企业文化与组织氛围：价值观落地、氛围感知与员工敬业度。"""
    return organization_tool.run_org_culture(
        db, message="文化氛围", department=department, period=period
    )
