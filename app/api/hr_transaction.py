"""HRIS 事务接口：年假、考勤、请假审批。"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.tools import hr_transaction_tool

router = APIRouter(prefix="/api/hr", tags=["HRIS 事务"])


@router.get("/leave/balance")
def leave_balance(
    name: str = Query(..., description="员工姓名"),
    db: Session = Depends(get_db),
):
    return hr_transaction_tool.run_leave_balance(db, "", employee_name=name)


@router.post("/leave/request")
def leave_request(
    name: str = Query(..., description="员工姓名"),
    leave_type: str = Query("annual", description="annual / sick / personal / compensatory"),
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    reason: str = Query("", description="请假原因"),
    db: Session = Depends(get_db),
):
    from app.services import hr_transaction_service

    return hr_transaction_service.submit_leave_request(
        db, name, leave_type, start_date, end_date, reason
    )


@router.post("/leave/approve")
def leave_approve(
    request_id: int = Query(..., description="请假申请 ID"),
    approver: str = Query(..., description="审批人姓名"),
    approve: bool = Query(True, description="True 批准 / False 驳回"),
    db: Session = Depends(get_db),
):
    from app.services import hr_transaction_service

    return hr_transaction_service.approve_leave(db, request_id, approver, approve=approve)


@router.get("/leave/pending")
def pending_leaves(db: Session = Depends(get_db)):
    from app.services import hr_transaction_service

    return {"pending": hr_transaction_service.list_pending_leaves(db)}


@router.get("/attendance")
def attendance(
    name: str = Query(..., description="员工姓名"),
    days: int = Query(30, description="最近天数"),
    db: Session = Depends(get_db),
):
    end = date.today()
    start = date.fromordinal(end.toordinal() - days)
    from app.services import hr_transaction_service

    return hr_transaction_service.get_attendance_summary(db, name, start, end)