"""个人发展计划接口。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.tools import idp_tool

router = APIRouter(prefix="/api/idp", tags=["个人发展计划"])


@router.get("")
def idp(
    name: str | None = Query(None, description="员工姓名"),
    employee_id: int | None = Query(None, description="员工 ID"),
    period: str | None = Query(None, description="考核周期"),
    max_gaps: int = Query(3, description="最多处理几个能力差距"),
    db: Session = Depends(get_db),
):
    return idp_tool.run_idp(
        db, name=name, employee_id=employee_id, period=period, max_gaps=max_gaps
    )
