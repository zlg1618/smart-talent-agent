"""HRIS · 员工关系管理域（Employee Relations）确定性计算。

覆盖四块：
    假期管理      法定年假天数、已用额度、剩余额度
    考勤管理      出勤率、迟到、缺勤、累计工时
    关系事件      劳动纠纷、申诉、关怀事件的风险分级与闭环跟踪
    敬业度        五维得分、eNPS 推荐者占比、离职倾向预警

所有业务规则（含法定年假天数）由 Python 计算，模型不参与。
"""

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


# ------------------ 关系事件 ------------------

CASE_SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}

RESOLVE_SLA_DAYS = {"low": 30, "medium": 14, "high": 7}


def relation_case_analysis(db: Session, department: str | None = None) -> dict:
    """员工关系事件台账：未闭环、超期、高风险识别。"""
    from app.models import RelationCase

    stmt = select(RelationCase)
    if department:
        emp_ids = [
            e.id
            for e in db.execute(
                select(Employee.id).where(Employee.department == department)
            ).scalars().all()
        ]
        stmt = stmt.where(RelationCase.employee_id.in_(emp_ids))
    cases = list(db.execute(stmt).scalars().all())

    emps = {e.id: e for e in db.execute(select(Employee)).scalars().all()}
    today = date.today()
    rows = []
    for c in cases:
        emp = emps.get(c.employee_id)
        if not emp:
            continue
        sla = RESOLVE_SLA_DAYS.get(c.severity, 14)
        days_open = (today - c.opened_at).days
        overdue = c.status == "open" and days_open > sla
        rows.append(
            {
                "case_id": c.id,
                "employee": emp.name,
                "department": emp.department,
                "case_type": c.case_type,
                "severity": c.severity,
                "status": c.status,
                "days_open": days_open,
                "sla_days": sla,
                "overdue": overdue,
                "escalation_risk": c.escalation_risk,
            }
        )

    rows.sort(key=lambda x: (-CASE_SEVERITY_RANK.get(x["severity"], 0), -x["days_open"]))
    open_cases = [r for r in rows if r["status"] == "open"]
    overdue_cases = [r for r in rows if r["overdue"]]
    high_risk = [r for r in rows if r["escalation_risk"] >= 0.6]

    return {
        "department": department or "全部部门",
        "total_cases": len(rows),
        "open_cases": len(open_cases),
        "overdue_cases": len(overdue_cases),
        "high_escalation_risk": len(high_risk),
        "by_type": dict(
            sorted(
                {t: sum(1 for r in rows if r["case_type"] == t) for t in set(r["case_type"] for r in rows)}.items(),
                key=lambda x: -x[1],
            )
        ),
        "overdue_list": overdue_cases[:10],
        "high_risk_list": high_risk[:10],
        "conclusion": (
            f"共 {len(rows)} 起关系事件，未闭环 {len(open_cases)} 起。"
            + (
                f"其中 {len(overdue_cases)} 起已超出处理时限，{len(high_risk)} 起升级风险较高，"
                f"建议由 HR 负责人直接介入。"
                if overdue_cases or high_risk
                else "均在时限内推进。"
            )
        ),
    }


# ------------------ 敬业度 ------------------

ENGAGEMENT_DIMENSIONS = [
    ("score_work", "工作本身"),
    ("score_manager", "直属上级"),
    ("score_growth", "成长发展"),
    ("score_reward", "薪酬回报"),
    ("score_balance", "工作生活平衡"),
]


def engagement_analysis(db: Session, department: str | None = None, period: str | None = None) -> dict:
    """敬业度分析：整体得分、五维短板、eNPS 与低分预警人群。"""
    from app.models import EngagementSurvey

    stmt = select(EngagementSurvey)
    if department:
        emp_ids = [
            e.id
            for e in db.execute(
                select(Employee.id).where(
                    Employee.department == department, Employee.status == "在职"
                )
            ).scalars().all()
        ]
        stmt = stmt.where(EngagementSurvey.employee_id.in_(emp_ids))
    surveys = list(db.execute(stmt).scalars().all())

    periods = sorted({s.period for s in surveys}, reverse=True)
    period = period or (periods[0] if periods else None)
    if period:
        surveys = [s for s in surveys if s.period == period]
    if not surveys:
        return {"error": "暂无敬业度调查数据"}

    emps = {e.id: e for e in db.execute(select(Employee)).scalars().all()}
    rows = []
    for s in surveys:
        emp = emps.get(s.employee_id)
        if not emp:
            continue
        lowest_dim = min(
            ENGAGEMENT_DIMENSIONS, key=lambda kv: getattr(s, kv[0])
        )
        rows.append(
            {
                "id": emp.id,
                "name": emp.name,
                "department": emp.department,
                "overall_score": s.overall_score,
                "lowest_dimension": lowest_dim[1],
                "lowest_score": getattr(s, lowest_dim[0]),
                "is_promoter": s.is_promoter,
            }
        )

    n = len(rows)
    avg = round(sum(r["overall_score"] for r in rows) / n, 2) if n else 0.0
    promoters = sum(1 for r in rows if r["is_promoter"])
    enps = round((promoters / n - (n - promoters) / n) * 100, 1) if n else 0.0

    dim_scores = []
    for field, label in ENGAGEMENT_DIMENSIONS:
        vals = [getattr(s, field) for s in surveys]
        dim_scores.append({"dimension": label, "score": round(sum(vals) / len(vals), 2)})
    dim_scores.sort(key=lambda x: x["score"])

    low = [r for r in rows if r["overall_score"] < 3.0]

    return {
        "department": department or "全部部门",
        "period": period,
        "survey_count": n,
        "avg_score": avg,
        "enps": enps,
        "promoter_percent": round(promoters / n * 100, 1) if n else 0.0,
        "dimension_scores": dim_scores,
        "weakest_dimension": dim_scores[0] if dim_scores else None,
        "low_score_count": len(low),
        "low_score_people": sorted(low, key=lambda x: x["overall_score"])[:10],
        "conclusion": (
            f"{period} 敬业度平均 {avg} 分，eNPS {enps}。"
            + (
                f"最弱维度为「{dim_scores[0]['dimension']}」（{dim_scores[0]['score']} 分），"
                f"建议作为下阶段组织改善重点。"
                if dim_scores
                else ""
            )
            + (f"另有 {len(low)} 人得分低于 3 分，建议一对一访谈。" if low else "")
        ),
    }


__all__ = [
    "approve_leave",
    "engagement_analysis",
    "get_attendance_summary",
    "get_leave_balance",
    "list_pending_leaves",
    "relation_case_analysis",
    "statutory_leave",
    "submit_leave_request",
]