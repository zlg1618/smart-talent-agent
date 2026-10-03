"""核心域 · 人才发展接口：能力差距、任职资格、人才池、发展项目、导师制。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.tools import talent_development_tool

router = APIRouter(prefix="/talent-development", tags=["核心-人才发展"])


@router.get("/competency")
def competency(
    employee_name: str | None = Query(None),
    department: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """能力画像与差距。指定员工看个人，否则看部门短板。"""
    return talent_development_tool.run_competency_profile(
        db, message=employee_name or "能力差距",
        employee_name=employee_name, department=department,
    )


@router.get("/standard-match")
def standard_match(
    employee_name: str | None = Query(None),
    department: str | None = Query(None),
    job_level: str | None = Query(None, description="目标职级，如 P7"),
    db: Session = Depends(get_db),
):
    """任职资格匹配度：员工与职级标准的加权比对。"""
    return talent_development_tool.run_talent_standard_match(
        db, message=employee_name or "任职资格",
        employee_name=employee_name, department=department, job_level=job_level,
    )


@router.get("/pool")
def pool(
    department: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """人才池视图：分层规模、在池流动与活跃度。"""
    return talent_development_tool.run_talent_pool(
        db, message="人才池", department=department
    )


@router.get("/program")
def program(db: Session = Depends(get_db)):
    """发展项目跟踪：覆盖率、完成率、满意度与人均投入。"""
    return talent_development_tool.run_development_program(db, message="发展项目")


@router.get("/mentorship")
def mentorship(
    department: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """导师制运行：配对规模、带教频次、进度与导师负荷。"""
    return talent_development_tool.run_mentorship(
        db, message="导师制", department=department
    )
