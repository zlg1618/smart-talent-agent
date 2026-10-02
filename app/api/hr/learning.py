"""HRIS · 培训与开发域接口：总览、必修合规、课程推荐、效果评估。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.tools import learning_tool

router = APIRouter(prefix="/learning", tags=["HRIS-培训与开发"])


@router.get("/overview")
def overview(department: str | None = Query(None), db: Session = Depends(get_db)):
    return learning_tool.run_training_overview(db, message="", department=department)


@router.get("/compliance")
def compliance(department: str | None = Query(None), db: Session = Depends(get_db)):
    """必修培训合规检查。"""
    return learning_tool.run_mandatory_compliance(db, message="", department=department)


@router.get("/recommend")
def recommend(
    name: str = Query(..., description="员工姓名"),
    top: int = Query(5),
    db: Session = Depends(get_db),
):
    """按能力差距推荐课程。"""
    return learning_tool.run_recommend_courses(db, message=name, top=top)


@router.get("/effectiveness")
def effectiveness(department: str | None = Query(None), db: Session = Depends(get_db)):
    return learning_tool.run_learning_effectiveness(db, message="", department=department)
