"""个人发展计划（IDP）生成。

基于员工能力差距（required_level - current_level）匹配学习资源，
遵循 70-20-10 发展法则：
    70% 在岗实践与项目历练
    20% 导师辅导与反馈
    10% 正式培训
课程全部来自数据库，未匹配到资源时明确标注"暂无匹配资源"。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Competency, Course, Employee, EmployeeCompetency
from app.services import employee_service, talent_review_service

FORM_BUCKET = {
    "项目": "70% 项目历练",
    "导师": "20% 导师辅导",
    "线上": "10% 正式培训",
    "线下": "10% 正式培训",
}

BUCKET_ORDER = ["70% 项目历练", "20% 导师辅导", "10% 正式培训"]


def build_idp(
    db: Session,
    name: str | None = None,
    employee_id: int | None = None,
    period: str | None = None,
    max_gaps: int = 3,
) -> dict:
    """生成某位员工的发展计划建议。"""
    if name:
        emp = employee_service.get_employee_by_name(db, name)
        if not emp:
            return {"error": f"未找到员工：{name}"}
    elif employee_id:
        emp = db.get(Employee, employee_id)
        if not emp:
            return {"error": f"未找到员工 ID：{employee_id}"}
    else:
        return {"error": "缺少员工姓名或 ID"}

    if period is None:
        period = employee_service.get_latest_period(db)

    # 能力差距
    stmt = select(EmployeeCompetency).where(EmployeeCompetency.employee_id == emp.id)
    records = list(db.execute(stmt).scalars().all())

    gaps = []
    for rec in records:
        gap = rec.required_level - rec.current_level
        if gap <= 0:
            continue
        comp = db.get(Competency, rec.competency_id)
        gaps.append(
            {
                "competency": comp.name if comp else f"能力#{rec.competency_id}",
                "category": comp.category if comp else None,
                "current_level": rec.current_level,
                "required_level": rec.required_level,
                "gap": gap,
            }
        )

    gaps.sort(key=lambda x: -x["gap"])

    # 九宫格定位决定发展基调
    grid = talent_review_service.locate_employee(db, emp.name, period)
    talent_type = (grid or {}).get("talent_type")

    plan = []
    for g in gaps[:max_gaps]:
        comp = db.execute(
            select(Competency).where(Competency.name == g["competency"])
        ).scalars().first()
        if not comp:
            continue

        courses = list(
            db.execute(
                select(Course).where(Course.competency_id == comp.id)
            ).scalars().all()
        )
        if not courses:
            plan.append(
                {
                    "competency": g["competency"],
                    "gap": g["gap"],
                    "action_type": "暂无匹配资源",
                    "action_name": "数据库中暂无对应学习资源，需人工补充",
                    "bucket": None,
                    "duration_hours": 0,
                }
            )
            continue

        # 每个能力项按 70-20-10 各取一项最接近目标等级的资源
        for form in ["项目", "导师", "线上", "线下"]:
            pool = [c for c in courses if c.form == form]
            if not pool:
                continue
            picked = min(
                pool, key=lambda c: (abs(c.target_level - g["required_level"]), c.id)
            )
            plan.append(
                {
                    "competency": g["competency"],
                    "gap": g["gap"],
                    "action_type": form,
                    "action_name": picked.name,
                    "bucket": FORM_BUCKET.get(form),
                    "target_level": picked.target_level,
                    "duration_hours": picked.duration_hours,
                }
            )

    plan.sort(key=lambda x: (BUCKET_ORDER.index(x["bucket"]) if x["bucket"] else 99))

    bucket_hours = {b: 0 for b in BUCKET_ORDER}
    for item in plan:
        if item["bucket"]:
            bucket_hours[item["bucket"]] += item["duration_hours"]

    total_hours = sum(bucket_hours.values())

    return {
        "employee": {
            "employee_id": emp.id,
            "name": emp.name,
            "department": emp.department,
            "position_title": emp.position_title,
            "job_level": emp.job_level,
        },
        "period": period,
        "talent_type": talent_type,
        "grid_name": (grid or {}).get("grid_name"),
        "grid_action": (grid or {}).get("action"),
        "gaps": gaps,
        "plan": plan,
        "summary": {
            "gap_count": len(gaps),
            "action_count": len(plan),
            "total_hours": total_hours,
            "by_70_20_10": bucket_hours,
        },
        "principle": "70% 项目历练 + 20% 导师辅导 + 10% 正式培训",
    }
