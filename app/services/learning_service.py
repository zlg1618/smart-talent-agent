"""HRIS · 培训与开发域（Learning & Development）确定性计算。

覆盖四块：
    培训运营      报名率、完成率、学时、人均成本
    必修合规      必修未完成清单与逾期预警
    能力驱动推荐  按员工能力差距（目标等级 - 现状等级）匹配课程
    投入产出      培训满意度、学时产出、预算执行率

课程与能力的匹配由确定性规则完成，模型只做结论解释。
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Competency,
    Employee,
    EmployeeCompetency,
    TrainingCourse,
    TrainingEnrollment,
)

MANDATORY_STATUS_OK = "completed"


def training_overview(db: Session, department: str | None = None) -> dict:
    """培训运营总览：覆盖率、完成率、学时与预算执行。"""
    emp_stmt = select(Employee).where(Employee.status == "在职")
    if department:
        emp_stmt = emp_stmt.where(Employee.department == department)
    employees = list(db.execute(emp_stmt).scalars().all())
    emp_ids = {e.id for e in employees}

    enrolls = list(db.execute(select(TrainingEnrollment)).scalars().all())
    rows = [x for x in enrolls if x.employee_id in emp_ids]

    courses = {c.id: c for c in db.execute(select(TrainingCourse)).scalars().all()}

    completed = [x for x in rows if x.status == MANDATORY_STATUS_OK]
    dropped = [x for x in rows if x.status in ("dropped", "failed")]
    total_hours = sum(x.hours_spent for x in completed)
    total_cost = sum(courses.get(x.course_id).cost_per_head if courses.get(x.course_id) else 0 for x in rows)

    trained_ids = {x.employee_id for x in rows}
    coverage = round(len(trained_ids) / len(employees), 3) if employees else 0.0
    completion = round(len(completed) / len(rows), 3) if rows else 0.0

    feedbacks = [x.feedback_score for x in completed if x.feedback_score > 0]
    avg_feedback = round(sum(feedbacks) / len(feedbacks), 2) if feedbacks else 0.0

    return {
        "department": department or "全部部门",
        "employee_count": len(employees),
        "enrollment_count": len(rows),
        "completed_count": len(completed),
        "dropped_count": len(dropped),
        "training_coverage": coverage,
        "completion_rate": completion,
        "total_hours": round(total_hours, 1),
        "avg_hours_per_employee": round(total_hours / len(employees), 1) if employees else 0.0,
        "total_cost": total_cost,
        "avg_cost_per_employee": round(total_cost / len(employees), 0) if employees else 0,
        "avg_feedback": avg_feedback,
        "conclusion": (
            f"在职 {len(employees)} 人中 {len(trained_ids)} 人有培训记录，覆盖率 "
            f"{round(coverage * 100, 1)}%；完课率 {round(completion * 100, 1)}%，"
            f"累计学时 {round(total_hours, 1)} 小时，人均培训成本 ¥"
            f"{round(total_cost / len(employees), 0) if employees else 0}。"
            + (
                f"有 {len(dropped)} 条记录未通过或中途退出，建议回访原因。"
                if dropped
                else ""
            )
        ),
    }


def mandatory_compliance(db: Session, department: str | None = None) -> dict:
    """必修课程合规检查：谁还没完成必修培训。"""
    emp_stmt = select(Employee).where(Employee.status == "在职")
    if department:
        emp_stmt = emp_stmt.where(Employee.department == department)
    employees = list(db.execute(emp_stmt).scalars().all())

    mandatory = list(
        db.execute(
            select(TrainingCourse).where(TrainingCourse.is_mandatory.is_(True))
        ).scalars().all()
    )
    if not mandatory:
        return {"error": "当前没有配置必修课程"}

    enrolls = list(db.execute(select(TrainingEnrollment)).scalars().all())
    done_map = {
        (x.employee_id, x.course_id)
        for x in enrolls
        if x.status == MANDATORY_STATUS_OK
    }

    gaps = []
    for e in employees:
        missing = [c for c in mandatory if (e.id, c.id) not in done_map]
        if missing:
            gaps.append(
                {
                    "id": e.id,
                    "name": e.name,
                    "department": e.department,
                    "missing_count": len(missing),
                    "missing_courses": [c.name for c in missing],
                    "missing_hours": round(sum(c.duration_hours for c in missing), 1),
                }
            )

    gaps.sort(key=lambda x: -x["missing_count"])
    total_required = len(employees) * len(mandatory)
    done_count = sum(
        1 for e in employees for c in mandatory if (e.id, c.id) in done_map
    )

    return {
        "department": department or "全部部门",
        "employee_count": len(employees),
        "mandatory_course_count": len(mandatory),
        "required_completions": total_required,
        "actual_completions": done_count,
        "compliance_rate": round(done_count / total_required, 3) if total_required else 0.0,
        "non_compliant_count": len(gaps),
        "gaps": gaps[:20],
        "mandatory_courses": [
            {"id": c.id, "name": c.name, "hours": c.duration_hours} for c in mandatory
        ],
        "conclusion": (
            f"必修课程 {len(mandatory)} 门，应完成 {total_required} 人次，"
            f"实际完成 {done_count} 人次，合规率 "
            f"{round(done_count / total_required * 100, 1) if total_required else 0}%。"
            + (
                f"有 {len(gaps)} 人存在必修缺口，最多者缺 "
                f"{gaps[0]['missing_count']} 门，需限期补训。"
                if gaps
                else "必修培训全部完成。"
            )
        ),
    }


def recommend_courses(db: Session, employee_name: str, top: int = 5) -> dict:
    """按员工能力差距推荐课程：gap 越大越优先，同类课程取结业等级最高的。"""
    emp = db.execute(
        select(Employee).where(Employee.name == employee_name)
    ).scalars().first()
    if not emp:
        return {"error": f"未找到员工：{employee_name}"}

    comps = list(
        db.execute(
            select(EmployeeCompetency).where(
                EmployeeCompetency.employee_id == emp.id
            )
        ).scalars().all()
    )
    if not comps:
        return {"error": f"员工 {employee_name} 暂无能力评估数据"}

    comp_map = {c.id: c for c in db.execute(select(Competency)).scalars().all()}
    courses = list(db.execute(select(TrainingCourse)).scalars().all())

    # 能力差距 = 岗位要求等级 - 当前等级（模型字段为 required_level）
    gaps, recommendations = [], []
    for ec in comps:
        required = ec.required_level or 0
        current = ec.current_level or 0
        gap = required - current
        if gap <= 0:
            continue
        comp = comp_map.get(ec.competency_id)
        gaps.append(
            {
                "competency": comp.name if comp else f"#{ec.competency_id}",
                "current_level": current,
                "required_level": required,
                "gap": gap,
            }
        )
        matched = [c for c in courses if c.target_competency_id == ec.competency_id]
        if not matched:
            continue
        matched.sort(key=lambda c: (-c.target_level, c.duration_hours))
        best = matched[0]
        recommendations.append(
            {
                "competency": comp.name if comp else f"#{ec.competency_id}",
                "gap": gap,
                "course": best.name,
                "course_id": best.id,
                "delivery_mode": best.delivery_mode,
                "duration_hours": best.duration_hours,
                "cost_per_head": best.cost_per_head,
                "target_level": best.target_level,
                "already_enough": best.target_level >= required,
                "priority": "高" if gap >= 2 else "中",
            }
        )

    gaps.sort(key=lambda x: -x["gap"])
    recommendations.sort(key=lambda x: (-x["gap"], x["duration_hours"]))
    total_hours = sum(r["duration_hours"] for r in recommendations[:top])
    total_cost = sum(r["cost_per_head"] for r in recommendations[:top])

    return {
        "employee": {
            "id": emp.id,
            "name": emp.name,
            "department": emp.department,
            "position_title": emp.position_title,
            "job_level": emp.job_level,
        },
        "gap_count": len(gaps),
        "gaps": gaps,
        "recommendations": recommendations[:top],
        "total_hours": round(total_hours, 1),
        "total_cost": total_cost,
        "conclusion": (
            f"{emp.name} 有 {len(gaps)} 项能力存在差距，"
            + (
                f"最大差距为「{gaps[0]['competency']}」（现 "
                f"{gaps[0]['current_level']} 级 / 要求 {gaps[0]['required_level']} 级）。"
                if gaps
                else "各项能力均已达标。"
            )
            + (
                f"推荐前 {min(top, len(recommendations))} 门课程，合计 "
                f"{round(total_hours, 1)} 学时、¥{total_cost}。"
                if recommendations
                else "暂无匹配的课程资源。"
            )
        ),
    }


def learning_effectiveness(db: Session, department: str | None = None) -> dict:
    """培训效果分析：按课程统计通过率、满意度与投入产出。"""
    emp_stmt = select(Employee).where(Employee.status == "在职")
    if department:
        emp_stmt = emp_stmt.where(Employee.department == department)
    emp_ids = {e.id for e in db.execute(emp_stmt).scalars().all()}

    courses = {c.id: c for c in db.execute(select(TrainingCourse)).scalars().all()}
    enrolls = [x for x in db.execute(select(TrainingEnrollment)).scalars().all()
               if x.employee_id in emp_ids]

    agg: dict[int, dict] = {}
    for x in enrolls:
        row = agg.setdefault(
            x.course_id,
            {"enrolled": 0, "completed": 0, "failed": 0, "scores": [], "feedbacks": [], "hours": 0.0},
        )
        row["enrolled"] += 1
        if x.status == MANDATORY_STATUS_OK:
            row["completed"] += 1
        elif x.status == "failed":
            row["failed"] += 1
        if x.score > 0:
            row["scores"].append(x.score)
        if x.feedback_score > 0:
            row["feedbacks"].append(x.feedback_score)
        row["hours"] += x.hours_spent

    rows = []
    for cid, row in agg.items():
        course = courses.get(cid)
        if not course:
            continue
        rows.append(
            {
                "course_id": cid,
                "course_name": course.name,
                "category": course.category,
                "enrolled": row["enrolled"],
                "completed": row["completed"],
                "pass_rate": round(row["completed"] / row["enrolled"], 3) if row["enrolled"] else 0.0,
                "avg_score": round(sum(row["scores"]) / len(row["scores"]), 1) if row["scores"] else 0.0,
                "avg_feedback": round(sum(row["feedbacks"]) / len(row["feedbacks"]), 2) if row["feedbacks"] else 0.0,
                "total_hours": round(row["hours"], 1),
                "total_cost": course.cost_per_head * row["enrolled"],
            }
        )

    rows.sort(key=lambda x: (x["avg_feedback"], x["pass_rate"]))
    low_rated = [r for r in rows if r["avg_feedback"] and r["avg_feedback"] < 3.5]

    return {
        "department": department or "全部部门",
        "course_count": len(rows),
        "total_enrollments": len(enrolls),
        "total_cost": sum(r["total_cost"] for r in rows),
        "courses": rows,
        "low_rated_courses": low_rated[:10],
        "conclusion": (
            f"共 {len(rows)} 门课程、{len(enrolls)} 人次报名。"
            + (
                f"其中 {len(low_rated)} 门课程满意度低于 3.5 分，"
                f"建议复盘内容设计或更换讲师。"
                if low_rated
                else "各课程满意度均在 3.5 分以上。"
            )
        ),
    }


__all__ = [
    "learning_effectiveness",
    "mandatory_compliance",
    "recommend_courses",
    "training_overview",
]
