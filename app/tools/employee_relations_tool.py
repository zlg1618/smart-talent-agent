"""HRIS · 员工关系管理域 Tool：假期、考勤、关系事件、敬业度。"""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Employee
from app.services import employee_relations_service
from app.tools.recruitment_tool import _DAYS_RE


TYPE_KEYWORDS = {
    "annual": ["年假"],
    "sick": ["病假"],
    "personal": ["事假"],
    "compensatory": ["调休"],
    "maternity": ["产假", "陪产假"],
}


def _find_employee(db: Session, message: str) -> Employee | None:
    rows = db.execute(select(Employee).distinct()).scalars().all()
    for emp in rows:
        if emp.name and emp.name in message:
            return emp
    return None


def _resolve_leave_type(message: str) -> str:
    for key, words in TYPE_KEYWORDS.items():
        for w in words:
            if w in message:
                return key
    return "annual"


def _extract_date_range(message: str) -> tuple[date, date] | None:
    """粗略从消息中抽取起止日期。"""
    import re

    pattern = re.compile(r"(20\d{2})[-/年](\d{1,2})[-/月](\d{1,2})")
    matches = list(pattern.finditer(message))
    if not matches:
        return None
    first = matches[0]
    last = matches[-1]
    start = date(int(first.group(1)), int(first.group(2)), int(first.group(3)))
    end = (
        date(int(last.group(1)), int(last.group(2)), int(last.group(3)))
        if last is not first
        else start
    )
    return start, end


def run_leave_balance(db: Session, message: str, employee_name: str | None = None) -> dict:
    if not employee_name:
        employee_name = (
            _find_employee(db, message).name if _find_employee(db, message) else None
        )
    if not employee_name:
        return {"error": "请告诉我要查询哪位员工的年假，例如：张伟的年假余额"}
    return employee_relations_service.get_leave_balance(db, employee_name)


def run_submit_leave(
    db: Session, message: str, employee_name: str | None = None
) -> dict:
    if not employee_name:
        emp = _find_employee(db, message)
        if not emp:
            return {"error": "请告诉我要为哪位员工请假"}
        employee_name = emp.name

    leave_type = _resolve_leave_type(message)
    range_ = _extract_date_range(message)
    days_match = _DAYS_RE.search(message)

    if range_:
        start, end = range_
        days = (end - start).days + 1
    elif days_match:
        days = float(days_match.group(1))
        start = date.today() + timedelta(days=1)
        end = start + timedelta(days=int(days) - 1)
    else:
        return {
            "error": "请提供请假日期或天数，例如："
            "「张伟 请 3 天年假」或「张伟 请 2025-10-10 到 2025-10-12 的年假」"
        }

    reason = message
    return employee_relations_service.submit_leave_request(
        db, employee_name, leave_type, start, end, reason
    )


def run_approve_leave(
    db: Session, message: str, approver_name: str | None = None
) -> dict:
    import re

    m = re.search(r"请假\s*(?:申请\s*)?(?:id\s*[:：#]?\s*|号\s*[:：]?\s*)?(\d+)", message)
    if not m:
        return {"error": "请提供请假申请 ID，例如：批准请假申请 3"}

    leave_id = int(m.group(1))
    approve = "批准" in message or "通过" in message
    reject = "拒绝" in message or "驳回" in message

    if not approver_name:
        approver = _find_employee(db, message)
        approver_name = approver.name if approver else "admin"

    if reject:
        return employee_relations_service.approve_leave(db, leave_id, approver_name, approve=False)
    if approve:
        return employee_relations_service.approve_leave(db, leave_id, approver_name, approve=True)
    return {"error": "请说「批准请假申请 N」或「拒绝请假申请 N」"}


def run_attendance(
    db: Session, message: str, employee_name: str | None = None
) -> dict:
    if not employee_name:
        emp = _find_employee(db, message)
        if emp:
            employee_name = emp.name
    if not employee_name:
        return {"error": "请告诉我要查询哪位员工的考勤，例如：李伟的查询能力"}
    return employee_relations_service.get_attendance_summary(db, employee_name)


def run_pending_leaves(db: Session, message: str) -> dict:
    return {"pending": employee_relations_service.list_pending_leaves(db)}


def run_relation_cases(db: Session, message: str, department: str | None = None) -> dict:
    if not department:
        department = _find_department(db, message)
    return employee_relations_service.relation_case_analysis(db, department=department)


def run_engagement(db: Session, message: str, department: str | None = None) -> dict:
    if not department:
        department = _find_department(db, message)
    return employee_relations_service.engagement_analysis(db, department=department)


def _find_department(db: Session, message: str) -> str | None:
    """从消息里猜部门：优先全名匹配。"""
    departments = [
        d[0]
        for d in db.execute(select(Employee.department).distinct()).all()
        if d[0]
    ]
    departments.sort(key=len, reverse=True)
    for dep in departments:
        if dep in message:
            return dep
    return None