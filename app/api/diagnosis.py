"""组织诊断接口。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.tools import diagnosis_tool

router = APIRouter(prefix="/api/diagnosis", tags=["组织诊断"])


@router.get("")
def diagnosis(
    department: str | None = Query(None, description="部门，为空表示全公司"),
    period: str | None = Query(None, description="考核周期"),
    db: Session = Depends(get_db),
):
    return diagnosis_tool.run_org_diagnosis(db, department=department, period=period)
