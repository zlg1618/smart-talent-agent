"""HRIS 事务服务：请假、考勤、剩余额度计算。"""

from datetime import date, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import AttendanceRecord, Employee, LeaveRequest


# ------------------ 请假规则（中国劳动法）------------------


def statutory_leave(years_of_service: float) -> int:
    """根据工龄返回法定年假天数。"""
    if years_of_service < 1:
        return 0
    if years_of_service < 10:
        return 5
    if years_of_service < 20:
        return 10
    return 15


def _years_of_service(emp: Employee, today: date | None = None) -> float:
    today = today or date.today()
    delta = today - emp.hire_date
    return round(delta.days / 365.25, 2)


# ------------------ 请假 ------------------


def get_leave_balance(db: Session, employee_name: str) -> dict:
    emp = db.execute(
        select(Employee).where(Employee.name == employee_name)
    ).scalars().first()
    if not emp:
        return {"error": f"未找到员工：{employee_name}"}

    years = _years_of_service(emp)
    entitlement = statutory_leave(years)

    # 已使用：approved + pending 都计入占额
    used_rows = db.execute(
        select(func.coalesce(func.sum(LeaveRequest.days), 0)).where(
            LeaveRequest.employee_id == emp.id,
            LeaveRequest.leave_type == "annual",
            LeaveRequest.status.in_(["approved", "pending"]),
        )
    ).scalar()
    used = float(used_rows or 0)
    remaining = max(0.0, round(entitlement - used, 1))

    pending = list(
        db.execute(
            select(LeaveRequest).where(
                LeaveRequest.employee_id == emp.id,
                LeaveRequest.status == "pending",
            ).order_by(desc(LeaveRequest.start_date))
        ).scalars().all()
    )

    return {
        "employee": {
            "id": emp.id,
            "name": emp.name,
            "department": emp.department,
            "hire_date": emp.hire_date.isoformat(),
            "years_of_service": years,
        },
        "annual_entitlement": entitlement,
        "annual_used": used,
        "annual_remaining": remaining,
        "pending_requests": [
            {
                "id": p.id,
                "leave_type": p.leave_type,
                "start_date": p.start_date.isoformat(),
                "end_date": p.end_date.isoformat(),
                "days": p.days,
                "reason": p.reason,
            }
            for p in pending
        ],
    }


def submit_leave_request(
    db: Session,
    employee_name: str,
    leave_type: str,
    start_date: date,
    end_date: date,
    reason: str = "",
) -> dict:
    emp = db.execute(
        select(Employee).where(Employee.name == employee_name)
    ).scalars().first()
    if not emp:
        return {"error": f"未找到员工：{employee_name}"}

    if end_date < start_date:
        return {"error": "结束日期早于开始日期"}

    days = (end_date - start_date).days + 1

    # 年假类型：检查余额
    warning = None
    if leave_type == "annual":
        bal = get_leave_balance(db, employee_name)
        if bal.get("annual_remaining", 0) < days:
            warning = (
                f"申请 {days} 天超过年假剩余 {bal['annual_remaining']} 天，"
                "建议主管沟通或拆分申请"
            )

    req = LeaveRequest(
        employee_id=emp.id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        days=float(days),
        reason=reason,
        status="pending",
    )
    db.add(req)
    db.commit()

    return {
        "request_id": req.id,
        "employee_name": emp.name,
        "leave_type": leave_type,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "days": days,
        "status": req.status,
        "warning": warning,
    }


def approve_leave(
    db: Session, leave_id: int, approver_name: str, approve: bool = True
) -> dict:
    req = db.get(LeaveRequest, leave_id)
    if not req:
        return {"error": f"未找到请假申请：{leave_id}"}
    approver = db.execute(
        select(Employee).where(Employee.name == approver_name)
    ).scalars().first()
    if not approver:
        return {"error": f"未找到审批人：{approver_name}"}
    req.status = "approved" if approve else "rejected"
    req.approver_id = approver.id
    db.commit()
    return {
        "request_id": req.id,
        "status": req.status,
        "approver": approver.name,
    }


def list_pending_leaves(db: Session, manager_name: str | None = None) -> list[dict]:
    stmt = select(LeaveRequest).where(LeaveRequest.status == "pending")
    rows = list(db.execute(stmt.order_by(desc(LeaveRequest.start_date))).scalars().all())
    result = []
    for r in rows:
        emp = db.get(Employee, r.employee_id)
        result.append(
            {
                "request_id": r.id,
                "employee_name": emp.name if emp else "?",
                "department": emp.department if emp else "?",
                "leave_type": r.leave_type,
                "start_date": r.start_date.isoformat(),
                "end_date": r.end_date.isoformat(),
                "days": r.days,
                "reason": r.reason,
            }
        )
    return result


# ------------------ 考勤 ------------------


def get_attendance_summary(
    db: Session,
    employee_name: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    emp = db.execute(
        select(Employee).where(Employee.name == employee_name)
    ).scalars().first()
    if not emp:
        return {"error": f"未找到员工：{employee_name}"}

    end_date = end_date or date.today()
    start_date = start_date or (end_date - timedelta(days=30))

    rows = list(
        db.execute(
            select(AttendanceRecord)
            .where(
                AttendanceRecord.employee_id == emp.id,
                AttendanceRecord.date >= start_date,
                AttendanceRecord.date <= end_date,
            )
            .order_by(AttendanceRecord.date)
        ).scalars().all()
    )

    days_total = 0
    workdays = 0
    absent = 0
    late = 0
    total_hours = 0.0
    for r in rows:
        days_total += 1
        if not r.is_absent:
            workdays += 1
            total_hours += r.hours
            if r.is_late:
                late += 1
        else:
            absent += 1

    return {
        "employee": {"id": emp.id, "name": emp.name, "department": emp.department},
        "range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        "days_total": days_total,
        "workdays": workdays,
        "absent_days": absent,
        "late_count": late,
        "total_hours": round(total_hours, 1),
        "avg_hours": round(total_hours / workdays, 2) if workdays else 0.0,
        "attendance_rate": round(workdays / days_total * 100, 1) if days_total else 0.0,
    }