"""HRIS · 员工关系管理域接口：假期、考勤、关系事件、敬业度。"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.tools import employee_relations_tool

router = APIRouter(prefix="/employee-relations", tags=["HRIS-员工关系管理"])


@router.get("/leave/balance")
def leave_balance(name: str = Query(..., description="员工姓名"), db: Session = Depends(get_db)):
    return employee_relations_tool.run_leave_balance(db, message=name)


@router.post("/leave/submit")
def submit_leave(
    name: str = Query(..., description="员工姓名"),
    leave_type: str = Query("annual", description="annual/sick/personal/compensatory/maternity"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    days: Optional[float] = Query(None, description="不传起止日期时按天数算"),
    reason: str = Query(""),
    db: Session = Depends(get_db),
):
    if start_date and end_date:
        message = f"{name} 请 {leave_type} 从 {start_date} 到 {end_date}"
    elif days:
        message = f"{name} 请 {days} 天 {leave_type}"
    else:
        return {"error": "请提供起止日期或天数"}
    return employee_relations_tool.run_submit_leave(db, message, employee_name=name)


@router.post("/leave/approve")
def approve_leave(
    leave_id: int = Query(..., description="请假申请 ID"),
    approve: bool = Query(True),
    approver: str = Query("admin"),
    db: Session = Depends(get_db),
):
    from app.services import employee_relations_service

    return employee_relations_service.approve_leave(db, leave_id, approver, approve=approve)


@router.get("/leave/pending")
def pending_leaves(db: Session = Depends(get_db)):
    return employee_relations_tool.run_pending_leaves(db, message="待审批")


@router.get("/attendance")
def attendance(
    name: str = Query(..., description="员工姓名"),
    days: int = Query(30, description="回溯天数"),
    db: Session = Depends(get_db),
):
    from app.services import employee_relations_service

    end = date.today()
    start = end - __import__("datetime").timedelta(days=days)
    return employee_relations_service.get_attendance_summary(db, name, start, end)


@router.get("/cases")
def relation_cases(
    department: str | None = Query(None), db: Session = Depends(get_db)
):
    return employee_relations_tool.run_relation_cases(db, message="", department=department)


@router.get("/engagement")
def engagement(
    department: str | None = Query(None),
    period: str | None = Query(None),
    db: Session = Depends(get_db),
):
    from app.services import employee_relations_service

    return employee_relations_service.engagement_analysis(db, department=department, period=period)
