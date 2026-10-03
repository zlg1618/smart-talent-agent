"""核心域 · 人才发展（Talent Development）确定性计算。

人才发展关注"人如何长起来"，回答四个问题：
    能力差多少      能力现状与目标等级之间的差距
    够不够格        员工与任职资格标准的加权匹配度
    池子活不活      人才池的分层、规模与流动
    项目有没有用    发展项目的覆盖率、完成率、满意度与人均投入
    带教落没落地    导师制的配对率、带教频次与导师负荷

注意：本域不包含人才盘点九宫格、继任地图、人才梯队与个人发展计划（IDP），
这些能力已从系统中移除。

所有匹配度、达成率与结论均由 Python 计算，大模型只负责把结论讲清楚。
"""

from datetime import date

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import (
    Competency,
    DevelopmentProgram,
    Employee,
    EmployeeCompetency,
    Mentorship,
    PerformanceRecord,
    PotentialAssessment,
    TalentPool,
    TalentStandard,
)

# 任职资格维度与员工数据的对应关系
DIMENSION_FIELDS = ["专业能力", "业务贡献", "领导力", "学习敏锐"]

# 匹配度分档
MATCH_RULE = [(0.90, "完全胜任"), (0.75, "基本胜任"), (0.60, "尚有差距"), (0.0, "差距明显")]

# 下一职级映射，用于"够不够格升到下一级"的判断
NEXT_LEVEL = {"P4": "P5", "P5": "P6", "P6": "P7", "P7": "P8", "P8": "M1",
              "M1": "M2", "M2": "M3", "M3": "M3"}


def _match_label(ratio: float) -> str:
    for threshold, label in MATCH_RULE:
        if ratio >= threshold:
            return label
    return "差距明显"


def _find_employee(db: Session, name: str) -> Employee | None:
    return db.execute(select(Employee).where(Employee.name == name)).scalars().first()


def _employee_scores(db: Session, emp: Employee) -> dict[str, float]:
    """把员工的真实数据映射成任职资格四个维度的得分（1-5 分制）。"""
    # 专业能力：现有能力等级的平均值
    levels = list(
        db.execute(
            select(EmployeeCompetency.current_level).where(
                EmployeeCompetency.employee_id == emp.id
            )
        ).scalars().all()
    )
    professional = round(sum(levels) / len(levels), 2) if levels else 3.0

    # 业务贡献：最近一次绩效分
    perf = db.execute(
        select(PerformanceRecord.score)
        .where(PerformanceRecord.employee_id == emp.id)
        .order_by(desc(PerformanceRecord.period))
    ).scalars().first()

    # 领导力与学习敏锐：最近一次潜力评估
    pot = db.execute(
        select(PotentialAssessment)
        .where(PotentialAssessment.employee_id == emp.id)
        .order_by(desc(PotentialAssessment.period))
    ).scalars().first()

    return {
        "专业能力": professional,
        "业务贡献": round(float(perf), 2) if perf else 3.0,
        "领导力": round(float(pot.leadership), 2) if pot and pot.leadership else 3.0,
        "学习敏锐": round(float(pot.learning_agility), 2) if pot and pot.learning_agility else 3.0,
    }


# ---------------------------- 一、能力画像与差距 ----------------------------


def competency_profile(
    db: Session, employee_name: str | None = None, department: str | None = None
) -> dict:
    """能力画像：个人逐项差距，或部门维度的最大短板。"""
    if employee_name:
        emp = _find_employee(db, employee_name)
        if not emp:
            return {"error": f"没有找到员工“{employee_name}”，请确认姓名。", "total": 0}

        rows = db.execute(
            select(EmployeeCompetency, Competency)
            .join(Competency, Competency.id == EmployeeCompetency.competency_id)
            .where(EmployeeCompetency.employee_id == emp.id)
        ).all()

        items = []
        for ec, comp in rows:
            gap = max(0, ec.required_level - ec.current_level)
            items.append(
                {
                    "competency": comp.name,
                    "category": comp.category,
                    "current": ec.current_level,
                    "required": ec.required_level,
                    "gap": gap,
                }
            )
        items.sort(key=lambda x: (-x["gap"], x["competency"]))

        gained = sum(min(i["current"], i["required"]) for i in items)
        needed = sum(i["required"] for i in items)
        achieve = round(gained / needed, 3) if needed else 0.0
        gaps = [i for i in items if i["gap"] > 0]

        return {
            "scope": "个人",
            "employee": emp.name,
            "department": emp.department,
            "job_level": emp.job_level,
            "total": len(items),
            "achieve_rate": achieve,
            "gap_count": len(gaps),
            "top_gaps": gaps[:5],
            "items": items,
            "conclusion": (
                f"{emp.name}（{emp.department}·{emp.job_level}）能力达成率 "
                f"{round(achieve * 100, 1)}%，"
                + (
                    f"共 {len(gaps)} 项未达标，最需补齐的是"
                    f"“{gaps[0]['competency']}”（现 {gaps[0]['current']} 级 / "
                    f"需 {gaps[0]['required']} 级）。"
                    if gaps
                    else "各项能力均已达到目标等级。"
                )
            ),
        }

    # 部门维度
    stmt = (
        select(
            Competency.name,
            func.avg(EmployeeCompetency.current_level),
            func.avg(EmployeeCompetency.required_level),
            func.count(EmployeeCompetency.id),
        )
        .join(Competency, Competency.id == EmployeeCompetency.competency_id)
        .join(Employee, Employee.id == EmployeeCompetency.employee_id)
    )
    if department:
        stmt = stmt.where(Employee.department == department)
    stmt = stmt.group_by(Competency.name)

    rows = []
    for name, cur, req, cnt in db.execute(stmt).all():
        cur = round(float(cur), 2)
        req = round(float(req), 2)
        rows.append(
            {
                "competency": name,
                "avg_current": cur,
                "avg_required": req,
                "gap": round(max(0.0, req - cur), 2),
                "sample": cnt,
            }
        )
    rows.sort(key=lambda x: -x["gap"])

    if not rows:
        return {"error": "当前条件下没有能力评估数据。", "total": 0}

    return {
        "scope": "部门",
        "department": department or "全部部门",
        "total": len(rows),
        "top_gaps": [r for r in rows if r["gap"] >= 0.5][:5],
        "items": rows,
        "conclusion": (
            f"共评估 {len(rows)} 项能力，整体差距最大的三项为"
            f"{'、'.join(r['competency'] for r in rows[:3])}，"
            f"建议围绕这些能力集中配置发展资源。"
        ),
    }


# ---------------------------- 二、任职资格匹配度 ----------------------------


def talent_standard_match(
    db: Session,
    employee_name: str | None = None,
    department: str | None = None,
    job_level: str | None = None,
) -> dict:
    """任职资格匹配度：员工与职级标准的加权比对。"""
    standards = list(db.execute(select(TalentStandard)).scalars().all())
    if not standards:
        return {"error": "尚未配置任职资格标准，无法计算匹配度。", "total": 0}

    # 按 (职族, 职级) 归并标准
    grouped: dict[tuple[str, str], list[TalentStandard]] = {}
    for s in standards:
        grouped.setdefault((s.job_family, s.job_level), []).append(s)

    if employee_name:
        emp = _find_employee(db, employee_name)
        if not emp:
            return {"error": f"没有找到员工“{employee_name}”。", "total": 0}

        target = job_level or NEXT_LEVEL.get(emp.job_level, emp.job_level)
        key = (emp.job_family, target)
        items = grouped.get(key) or grouped.get((emp.job_family, emp.job_level))
        if not items:
            return {
                "error": f"未找到 {emp.job_family} 职族 {target} 职级的任职资格标准。",
                "total": 0,
            }

        scores = _employee_scores(db, emp)
        total_weight = sum(i.weight for i in items) or 1.0
        earned = 0.0
        detail = []
        for i in items:
            actual = scores.get(i.dimension, 3.0)
            reach = min(actual / i.pass_score, 1.0) if i.pass_score else 1.0
            earned += reach * i.weight
            detail.append(
                {
                    "dimension": i.dimension,
                    "weight": i.weight,
                    "pass_score": i.pass_score,
                    "actual": actual,
                    "reach": round(reach, 3),
                    "passed": actual >= i.pass_score,
                    "requirement": i.requirement,
                }
            )
        ratio = round(earned / total_weight, 3)
        failed = [d for d in detail if not d["passed"]]

        return {
            "scope": "个人",
            "employee": emp.name,
            "department": emp.department,
            "job_family": emp.job_family,
            "current_level": emp.job_level,
            "target_level": items[0].job_level,
            "match_rate": ratio,
            "match_label": _match_label(ratio),
            "failed_dimensions": failed,
            "detail": detail,
            "conclusion": (
                f"{emp.name} 对照 {items[0].job_level} 任职资格的匹配度为 "
                f"{round(ratio * 100, 1)}%（{_match_label(ratio)}）。"
                + (
                    f"未达标维度：{'、'.join(d['dimension'] for d in failed)}，"
                    f"建议优先补齐后再次评估。"
                    if failed
                    else "各维度均已达标，可纳入晋升评审。"
                )
            ),
        }

    # 部门维度：统计在职人员对照下一职级的整体匹配情况
    stmt = select(Employee).where(Employee.status == "在职")
    if department:
        stmt = stmt.where(Employee.department == department)
    employees = list(db.execute(stmt).scalars().all())
    if not employees:
        return {"error": "当前条件下没有在职员工。", "total": 0}

    rows = []
    for emp in employees:
        target = job_level or NEXT_LEVEL.get(emp.job_level, emp.job_level)
        items = grouped.get((emp.job_family, target)) or grouped.get(
            (emp.job_family, emp.job_level)
        )
        if not items:
            continue
        scores = _employee_scores(db, emp)
        total_weight = sum(i.weight for i in items) or 1.0
        earned = sum(
            (min(scores.get(i.dimension, 3.0) / i.pass_score, 1.0) if i.pass_score else 1.0)
            * i.weight
            for i in items
        )
        ratio = round(earned / total_weight, 3)
        rows.append(
            {
                "name": emp.name,
                "department": emp.department,
                "job_family": emp.job_family,
                "current_level": emp.job_level,
                "target_level": items[0].job_level,
                "match_rate": ratio,
                "match_label": _match_label(ratio),
            }
        )

    rows.sort(key=lambda x: -x["match_rate"])
    ready = [r for r in rows if r["match_rate"] >= 0.75]
    avg = round(sum(r["match_rate"] for r in rows) / len(rows), 3) if rows else 0.0

    return {
        "scope": "部门",
        "department": department or "全部部门",
        "total": len(rows),
        "avg_match_rate": avg,
        "ready_count": len(ready),
        "ready_rate": round(len(ready) / len(rows), 3) if rows else 0.0,
        "ready_people": ready[:10],
        "people": rows[:20],
        "conclusion": (
            f"共比对 {len(rows)} 人，平均匹配度 {round(avg * 100, 1)}%，"
            f"其中 {len(ready)} 人达到基本胜任及以上（≥75%），"
            f"可作为晋升评审与发展资源投放的优先对象。"
        ),
    }


# ---------------------------- 三、人才池视图 ----------------------------


def talent_pool_view(
    db: Session, department: str | None = None, pool_type: str | None = None
) -> dict:
    """人才池：分层规模、在池流动与活跃度。"""
    stmt = select(TalentPool, Employee).join(Employee, Employee.id == TalentPool.employee_id)
    if department:
        stmt = stmt.where(Employee.department == department)
    if pool_type:
        stmt = stmt.where(TalentPool.pool_type == pool_type)
    records = list(db.execute(stmt).all())

    if not records:
        return {"error": "当前条件下没有人才池数据。", "total": 0}

    pools: dict[str, dict] = {}
    for pool, emp in records:
        item = pools.setdefault(
            pool.pool_name,
            {
                "pool_name": pool.pool_name,
                "pool_type": pool.pool_type,
                "in_pool": 0,
                "observing": 0,
                "exited": 0,
                "scores": [],
                "departments": set(),
                "tags": set(),
                "members": [],
            },
        )
        if pool.stage == "在池":
            item["in_pool"] += 1
        elif pool.stage == "观察":
            item["observing"] += 1
        else:
            item["exited"] += 1
        item["scores"].append(pool.score)
        item["departments"].add(emp.department)
        if pool.tag:
            item["tags"].add(pool.tag)
        item["members"].append(
            {
                "name": emp.name,
                "department": emp.department,
                "job_level": emp.job_level,
                "stage": pool.stage,
                "tag": pool.tag,
                "score": pool.score,
            }
        )

    rows = []
    for name, item in pools.items():
        total = item["in_pool"] + item["observing"] + item["exited"]
        avg_score = round(sum(item["scores"]) / len(item["scores"]), 1)
        active_rate = round(item["in_pool"] / total, 3) if total else 0.0
        if active_rate >= 0.8:
            health = "活跃"
        elif active_rate >= 0.6:
            health = "正常"
        else:
            health = "流失偏高"
        rows.append(
            {
                "pool_name": name,
                "pool_type": item["pool_type"],
                "in_pool": item["in_pool"],
                "observing": item["observing"],
                "exited": item["exited"],
                "total": total,
                "avg_score": avg_score,
                "active_rate": active_rate,
                "health": health,
                "departments": sorted(item["departments"]),
                "tags": sorted(item["tags"]),
                "top_members": sorted(
                    item["members"], key=lambda x: -x["score"]
                )[:5],
                "advice": _pool_advice(health, item["in_pool"], item["observing"]),
            }
        )

    rows.sort(key=lambda x: -x["in_pool"])
    total_in = sum(r["in_pool"] for r in rows)
    weak = [r for r in rows if r["health"] == "流失偏高"]

    return {
        "department": department or "全部部门",
        "total_pools": len(rows),
        "total_in_pool": total_in,
        "average_score": round(
            sum(r["avg_score"] for r in rows) / len(rows), 1
        )
        if rows
        else 0.0,
        "weak_pools": weak,
        "pools": rows,
        "conclusion": (
            f"共 {len(rows)} 个人才池，在池 {total_in} 人。"
            + (
                f"其中 {len(weak)} 个池子出池比例偏高，"
                f"建议复盘入池标准与池内培养投入。"
                if weak
                else "各人才池活跃度正常，可持续运行。"
            )
        ),
    }


def _pool_advice(health: str, in_pool: int, observing: int) -> str:
    if health == "流失偏高":
        return "出池比例过高，建议复核入池标准并增加池内发展机会"
    if observing > in_pool:
        return "观察期成员偏多，建议明确转正或出池的判定节奏"
    return "人才池运行正常，按季度复盘进出池情况"


# ---------------------------- 四、发展项目跟踪 ----------------------------


def development_program_tracking(
    db: Session, program_type: str | None = None
) -> dict:
    """发展项目：覆盖率、完成率、满意度与人均投入。"""
    stmt = select(DevelopmentProgram)
    if program_type:
        stmt = stmt.where(DevelopmentProgram.program_type == program_type)
    programs = list(db.execute(stmt).scalars().all())

    if not programs:
        return {"error": "当前条件下没有发展项目数据。", "total": 0}

    rows = []
    for p in programs:
        capacity = p.capacity or 0
        enrolled = p.enrolled or 0
        completed = p.completed or 0
        fill_rate = round(enrolled / capacity, 3) if capacity else 0.0
        completion_rate = round(completed / enrolled, 3) if enrolled else 0.0
        per_head = round(p.budget * 10000 / enrolled, 0) if enrolled else 0.0
        if completion_rate >= 0.85 and p.satisfaction >= 4.0:
            grade = "效果良好"
        elif completion_rate >= 0.7:
            grade = "基本达标"
        else:
            grade = "需改进"
        rows.append(
            {
                "name": p.name,
                "program_type": p.program_type,
                "audience": p.audience,
                "capacity": capacity,
                "enrolled": enrolled,
                "completed": completed,
                "fill_rate": fill_rate,
                "completion_rate": completion_rate,
                "satisfaction": p.satisfaction,
                "budget": p.budget,
                "cost_per_head": per_head,
                "grade": grade,
                "start_date": str(p.start_date) if p.start_date else "-",
                "end_date": str(p.end_date) if p.end_date else "-",
                "advice": _program_advice(grade, fill_rate, completion_rate),
            }
        )

    rows.sort(key=lambda x: (x["grade"] != "需改进", -x["completion_rate"]))

    total_enrolled = sum(r["enrolled"] for r in rows)
    total_budget = round(sum(r["budget"] for r in rows), 1)
    avg_completion = round(
        sum(r["completion_rate"] for r in rows) / len(rows), 3
    )
    avg_satisfaction = round(
        sum(r["satisfaction"] for r in rows) / len(rows), 2
    )
    poor = [r for r in rows if r["grade"] == "需改进"]

    return {
        "total": len(rows),
        "total_enrolled": total_enrolled,
        "total_budget": total_budget,
        "avg_completion_rate": avg_completion,
        "avg_satisfaction": avg_satisfaction,
        "poor_programs": poor,
        "programs": rows,
        "conclusion": (
            f"共 {len(rows)} 个发展项目，累计入学 {total_enrolled} 人，"
            f"预算 {total_budget} 万元，平均完成率 {round(avg_completion * 100, 1)}%，"
            f"平均满意度 {avg_satisfaction}。"
            + (
                f"其中 {len(poor)} 个项目完成率低于 70%，"
                f"建议复盘选题与学员投入度。"
                if poor
                else "各项目完成情况良好。"
            )
        ),
    }


def _program_advice(grade: str, fill_rate: float, completion_rate: float) -> str:
    if fill_rate < 0.7:
        return "招生未满，建议扩大宣传或调整目标人群"
    if grade == "需改进":
        return f"完成率仅 {round(completion_rate * 100, 1)}%，建议缩短周期并强化过程督促"
    if grade == "效果良好":
        return "效果良好，可沉淀为标准项目并扩大覆盖"
    return "基本达标，建议关注结业后的行为改变与业务应用"


# ---------------------------- 五、导师制运行 ----------------------------


def mentorship_view(db: Session, department: str | None = None) -> dict:
    """导师制：配对规模、带教频次、完成进度与导师负荷。"""
    stmt = (
        select(Mentorship, Employee)
        .join(Employee, Employee.id == Mentorship.mentee_id)
    )
    if department:
        stmt = stmt.where(Employee.department == department)
    records = list(db.execute(stmt).all())

    if not records:
        return {"error": "当前条件下没有导师带教数据。", "total": 0}

    mentors = db.execute(select(Employee)).scalars().all()
    mentor_map = {m.id: m for m in mentors}

    rows = []
    load: dict[int, int] = {}
    for m, mentee in records:
        mentor = mentor_map.get(m.mentor_id)
        progress = round(m.session_count / m.planned_sessions, 3) if m.planned_sessions else 0.0
        if progress >= 1.0:
            stage = "已完成"
        elif progress >= 0.5:
            stage = "推进中"
        else:
            stage = "刚起步"
        load[m.mentor_id] = load.get(m.mentor_id, 0) + 1
        rows.append(
            {
                "mentor": mentor.name if mentor else "-",
                "mentor_level": mentor.job_level if mentor else "-",
                "mentee": mentee.name,
                "mentee_department": mentee.department,
                "mentee_level": mentee.job_level,
                "topic": m.topic,
                "session_count": m.session_count,
                "planned_sessions": m.planned_sessions,
                "progress": progress,
                "stage": stage,
                "status": m.status,
                "start_date": str(m.start_date) if m.start_date else "-",
            }
        )

    rows.sort(key=lambda x: -x["progress"])

    total = len(rows)
    avg_sessions = round(sum(r["session_count"] for r in rows) / total, 1)
    avg_progress = round(sum(r["progress"] for r in rows) / total, 3)
    finished = [r for r in rows if r["stage"] == "已完成"]
    stalled = [r for r in rows if r["stage"] == "刚起步"]
    overloaded = sorted(
        (
            {
                "mentor": mentor_map[mid].name,
                "mentee_count": cnt,
            }
            for mid, cnt in load.items()
            if cnt >= 3 and mid in mentor_map
        ),
        key=lambda x: -x["mentee_count"],
    )

    return {
        "department": department or "全部部门",
        "total_pairs": total,
        "mentor_count": len(load),
        "avg_sessions": avg_sessions,
        "avg_progress": avg_progress,
        "finished_count": len(finished),
        "stalled_count": len(stalled),
        "stalled_pairs": stalled[:5],
        "overloaded_mentors": overloaded,
        "pairs": rows[:20],
        "conclusion": (
            f"共 {total} 组带教关系，涉及 {len(load)} 位导师，"
            f"平均已完成 {avg_sessions} 次带教，整体进度 "
            f"{round(avg_progress * 100, 1)}%。"
            + (
                f"其中 {len(stalled)} 组进度不足 50%，需要督促启动；"
                if stalled
                else ""
            )
            + (
                f"{len(overloaded)} 位导师同时带 3 人以上，负荷偏高。"
                if overloaded
                else "导师负荷分布均衡。"
            )
        ),
    }


__all__ = [
    "competency_profile",
    "development_program_tracking",
    "mentorship_view",
    "talent_pool_view",
    "talent_standard_match",
]
