"""核心域 · 人才发展（Talent Development）确定性计算。

人才发展（TD）的对象是人、个体与人才梯队，覆盖七类工作：

    人才盘点        九宫格（绩效 × 潜力）+ 360 度评估，识别高潜与短板
    胜任力模型      能力项、等级行为描述与岗位能力要求
    任职资格        职族职级的四维达标线加权匹配
    继任与梯队      关键岗位继任者计划与梯队供给比
    高潜培养        高潜人才项目、管理者训练营、行动学习
    学习发展体系    内训、轮岗、导师制、个人发展计划 IDP
    人才任用        结合盘点结果输出晋升、保留、调整建议

所有匹配度、达成率与结论均由 Python 计算，大模型只负责把结论讲清楚；
每个结果都带 basis 字段，说明分数是怎么算出来的。
"""

from datetime import date

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import (
    Competency,
    CompetencyLevel,
    DevelopmentPlan,
    DevelopmentProgram,
    Employee,
    EmployeeCompetency,
    KeyPosition,
    Mentorship,
    PerformanceRecord,
    PositionCompetency,
    PotentialAssessment,
    Review360,
    SuccessionCandidate,
    TalentPool,
    TalentStandard,
)

# 九宫格：绩效与潜力各自的低/中/高分档阈值（1-5 分制）
REVIEW_SCORE_LOW = 3.0
REVIEW_SCORE_HIGH = 3.8

# 九宫格格子命名（绩效档, 潜力档）
GRID_NAMES = {
    ("高", "高"): "超级明星",
    ("高", "中"): "中坚骨干",
    ("高", "低"): "业务专家",
    ("中", "高"): "潜力之星",
    ("中", "中"): "稳定贡献者",
    ("中", "低"): "踏实执行者",
    ("低", "高"): "待激活者",
    ("低", "中"): "待提升者",
    ("低", "低"): "待优化者",
}

# 高潜定义所在格子
HIGH_POTENTIAL_GRIDS = {("高", "高"), ("中", "高")}

# 360 评估维度
REVIEW_DIMENSIONS = ["专业能力", "协作沟通", "领导力", "执行力"]

# 继任准备度排序与中文标签
READINESS_ORDER = {"ready_now": 1, "ready_1y": 2, "ready_2y": 3, "not_ready": 4}
READINESS_LABEL = {
    "ready_now": "立即就绪",
    "ready_1y": "1 年内就绪",
    "ready_2y": "2 年内就绪",
    "not_ready": "尚未就绪",
}

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


# ---------------------------- 六、人才盘点（九宫格 + 360） ----------------------------


def _grade_band(score: float) -> str:
    if score >= REVIEW_SCORE_HIGH:
        return "高"
    if score >= REVIEW_SCORE_LOW:
        return "中"
    return "低"


def talent_review(
    db: Session,
    department: str | None = None,
    period: str | None = None,
    job_level: str | None = None,
) -> dict:
    """人才盘点：绩效 × 潜力九宫格 + 360 度评估，识别高潜与短板人员。"""
    stmt = select(Employee).where(Employee.status == "在职")
    if department:
        stmt = stmt.where(Employee.department == department)
    if job_level:
        stmt = stmt.where(Employee.job_level == job_level)
    employees = list(db.execute(stmt).scalars().all())

    if not employees:
        return {"error": "当前条件下没有参与盘点的在职员工。", "total": 0}

    # 最近一次的绩效与潜力分
    people = []
    for emp in employees:
        perf_stmt = (
            select(PerformanceRecord.score)
            .where(PerformanceRecord.employee_id == emp.id)
        )
        pot_stmt = select(PotentialAssessment).where(
            PotentialAssessment.employee_id == emp.id
        )
        if period:
            perf_stmt = perf_stmt.where(PerformanceRecord.period == period)
            pot_stmt = pot_stmt.where(PotentialAssessment.period == period)
        perf = db.execute(
            perf_stmt.order_by(desc(PerformanceRecord.period))
        ).scalars().first()
        pot = db.execute(
            pot_stmt.order_by(desc(PotentialAssessment.period))
        ).scalars().first()

        perf_score = round(float(perf), 2) if perf else 3.0
        pot_score = round(float(pot.potential_score), 2) if pot else 3.0
        perf_band = _grade_band(perf_score)
        pot_band = _grade_band(pot_score)
        grid = (perf_band, pot_band)
        people.append(
            {
                "id": emp.id,
                "name": emp.name,
                "department": emp.department,
                "job_level": emp.job_level,
                "performance": perf_score,
                "potential": pot_score,
                "performance_band": perf_band,
                "potential_band": pot_band,
                "grid": f"{perf_band}-{pot_band}",
                "grid_name": GRID_NAMES.get(grid, "待评估"),
                "is_high_potential": grid in HIGH_POTENTIAL_GRIDS,
            }
        )

    # 九宫格矩阵：行=绩效（高→低），列=潜力（低→高）
    perf_bands = ["高", "中", "低"]
    pot_bands = ["低", "中", "高"]
    matrix = []
    for pb in perf_bands:
        row = []
        for tb in pot_bands:
            members = [
                p for p in people if p["performance_band"] == pb and p["potential_band"] == tb
            ]
            row.append(
                {
                    "performance_band": pb,
                    "potential_band": tb,
                    "grid": f"{pb}-{tb}",
                    "grid_name": GRID_NAMES.get((pb, tb), "待评估"),
                    "count": len(members),
                    "people": [
                        {"name": m["name"], "department": m["department"],
                         "job_level": m["job_level"]}
                        for m in members[:8]
                    ],
                }
            )
        matrix.append(row)

    high_potential = sorted(
        [p for p in people if p["is_high_potential"]],
        key=lambda x: (-x["potential"], -x["performance"]),
    )
    low_performers = sorted(
        [p for p in people if p["performance_band"] == "低"],
        key=lambda x: (x["potential"], x["performance"]),
    )

    # ---------- 360 度评估 ----------
    r360_stmt = select(Review360)
    if period:
        r360_stmt = r360_stmt.where(Review360.period == period)
    reviews = list(db.execute(r360_stmt).scalars().all())

    review_rows = []
    if reviews:
        emp_ids = {p["id"] for p in people}
        by_emp: dict[int, list[Review360]] = {}
        for r in reviews:
            if r.employee_id in emp_ids:
                by_emp.setdefault(r.employee_id, []).append(r)

        for emp_id, items in by_emp.items():
            person = next(p for p in people if p["id"] == emp_id)
            by_role: dict[str, float] = {}
            for role in ("自评", "上级", "同级", "下级"):
                scores = [i.score for i in items if i.rater_role == role]
                if scores:
                    by_role[role] = round(sum(scores) / len(scores), 2)
            self_score = by_role.get("自评")
            others = [v for k, v in by_role.items() if k != "自评"]
            others_avg = round(sum(others) / len(others), 2) if others else None
            gap = round(self_score - others_avg, 2) if (self_score and others_avg) else None
            if gap is None:
                cognition = "数据不足"
            elif gap >= 0.5:
                cognition = "自评偏高"
            elif gap <= -0.5:
                cognition = "自评偏低"
            else:
                cognition = "认知一致"
            review_rows.append(
                {
                    "name": person["name"],
                    "department": person["department"],
                    "job_level": person["job_level"],
                    "by_role": by_role,
                    "self_score": self_score,
                    "others_avg": others_avg,
                    "cognition_gap": gap,
                    "cognition": cognition,
                }
            )
        review_rows.sort(key=lambda x: abs(x["cognition_gap"] or 0), reverse=True)

    cognition_issues = [r for r in review_rows if r["cognition"] in ("自评偏高", "自评偏低")]

    return {
        "department": department or "全部部门",
        "period": period or "最近一次",
        "job_level": job_level or "全部职级",
        "total": len(people),
        "grid_matrix": matrix,
        "grid_summary": [
            {"grid": c["grid"], "grid_name": c["grid_name"], "count": c["count"]}
            for row in matrix
            for c in row
            if c["count"]
        ],
        "high_potential_count": len(high_potential),
        "high_potential": [
            {"name": p["name"], "department": p["department"], "job_level": p["job_level"],
             "performance": p["performance"], "potential": p["potential"],
             "grid_name": p["grid_name"]}
            for p in high_potential[:10]
        ],
        "low_performer_count": len(low_performers),
        "low_performers": [
            {"name": p["name"], "department": p["department"], "job_level": p["job_level"],
             "performance": p["performance"], "potential": p["potential"],
             "grid_name": p["grid_name"]}
            for p in low_performers[:10]
        ],
        "review_360_total": len(review_rows),
        "review_360": review_rows[:10],
        "cognition_issues": cognition_issues[:5],
        "people": people,
        "basis": (
            f"绩效档：≥{REVIEW_SCORE_HIGH} 高、≥{REVIEW_SCORE_LOW} 中、其余低；"
            "潜力档同阈值。九宫格 = 绩效档 × 潜力档；"
            "高潜 = （高-高）与（中-高）；"
            "360 认知偏差 = 自评分 − 他人均分，|差值| ≥ 0.5 判定为认知不一致"
        ),
        "conclusion": (
            f"参与盘点 {len(people)} 人，高潜 {len(high_potential)} 人"
            f"（占 {round(len(high_potential) / len(people) * 100, 1)}%），"
            f"待优化 {len(low_performers)} 人。"
            + (
                f"360 评估覆盖 {len(review_rows)} 人，其中 {len(cognition_issues)} 人"
                f"存在自我认知偏差，面谈时需要重点对齐。"
                if review_rows
                else ""
            )
        ),
    }


# ---------------------------- 七、胜任力模型 ----------------------------


def competency_model(
    db: Session,
    job_family: str | None = None,
    job_level: str | None = None,
    employee_name: str | None = None,
) -> dict:
    """胜任力模型：能力项、等级行为描述与岗位能力要求。"""
    competencies = list(db.execute(select(Competency)).scalars().all())
    if not competencies:
        return {"error": "尚未搭建能力模型。", "total": 0}

    levels = list(db.execute(select(CompetencyLevel)).scalars().all())
    level_map: dict[int, list[dict]] = {}
    for lv in sorted(levels, key=lambda x: x.level):
        level_map.setdefault(lv.competency_id, []).append(
            {"level": lv.level, "behavior": lv.behavior, "evidence": lv.evidence}
        )

    req_stmt = select(PositionCompetency)
    if job_family:
        req_stmt = req_stmt.where(PositionCompetency.job_family == job_family)
    if job_level:
        req_stmt = req_stmt.where(PositionCompetency.job_level == job_level)
    requirements = list(db.execute(req_stmt).scalars().all())
    comp_names = {c.id: c.name for c in competencies}

    req_rows = []
    covered_ids = set()
    for r in requirements:
        req_rows.append(
            {
                "job_family": r.job_family,
                "job_level": r.job_level,
                "competency": comp_names.get(r.competency_id, "-"),
                "required_level": r.required_level,
                "weight": r.weight,
                "behavior": next(
                    (
                        lv["behavior"]
                        for lv in level_map.get(r.competency_id, [])
                        if lv["level"] == r.required_level
                    ),
                    "",
                ),
            }
        )
        covered_ids.add(r.competency_id)
    req_rows.sort(key=lambda x: (-x["weight"], x["competency"]))

    model_rows = [
        {
            "competency": c.name,
            "category": c.category,
            "levels": level_map.get(c.id, []),
            "has_position_requirement": c.id in covered_ids,
        }
        for c in competencies
    ]

    # 员工对照：现状等级 vs 岗位要求等级
    employee_gap = None
    if employee_name:
        emp = _find_employee(db, employee_name)
        if emp:
            current = {
                ec.competency_id: ec.current_level
                for ec in db.execute(
                    select(EmployeeCompetency).where(
                        EmployeeCompetency.employee_id == emp.id
                    )
                ).scalars().all()
            }
            family = job_family or emp.job_family
            level = job_level or emp.job_level
            matched = [
                r
                for r in req_rows
                if r["job_family"] == family and r["job_level"] == level
            ]
            if matched:
                total_weight = sum(r["weight"] for r in matched) or 1.0
                earned = sum(
                    min(current.get(_cid(r["competency"], comp_names), 0) / r["required_level"], 1.0)
                    * r["weight"]
                    for r in matched
                )
                fit = round(earned / total_weight, 3)
                employee_gap = {
                    "employee": emp.name,
                    "job_family": family,
                    "job_level": level,
                    "fit_rate": fit,
                    "fit_label": "达标" if fit >= 0.9 else ("接近达标" if fit >= 0.75 else "差距较大"),
                    "items": [
                        {
                            "competency": r["competency"],
                            "current": current.get(_cid(r["competency"], comp_names), 0),
                            "required": r["required_level"],
                            "weight": r["weight"],
                        }
                        for r in matched
                    ],
                }

    coverage = round(len(covered_ids) / len(competencies), 3) if competencies else 0.0

    return {
        "job_family": job_family or "全部职族",
        "job_level": job_level or "全部职级",
        "total_competencies": len(competencies),
        "total_level_definitions": len(levels),
        "requirement_coverage": coverage,
        "model": model_rows,
        "position_requirements": req_rows,
        "employee_gap": employee_gap,
        "basis": (
            "模型覆盖度 = 已被岗位要求引用的能力项 / 能力项总数；"
            "员工符合度 = Σ(权重 × min(现状等级 / 要求等级, 1)) / Σ权重"
        ),
        "conclusion": (
            f"能力模型共 {len(competencies)} 项能力、{len(levels)} 条等级行为描述，"
            f"岗位要求覆盖 {round(coverage * 100, 1)}%。"
            + (
                f"{employee_gap['employee']} 对照 {employee_gap['job_level']} 的符合度为 "
                f"{round(employee_gap['fit_rate'] * 100, 1)}%（{employee_gap['fit_label']}）。"
                if employee_gap
                else ""
            )
        ),
    }


def _cid(name: str, comp_names: dict[int, str]) -> int | None:
    for k, v in comp_names.items():
        if v == name:
            return k
    return None


# ---------------------------- 八、继任者计划与梯队建设 ----------------------------


def succession_plan(
    db: Session, department: str | None = None, criticality: str | None = None
) -> dict:
    """继任者计划与关键岗位人才梯队建设。"""
    stmt = select(KeyPosition)
    if department:
        stmt = stmt.where(KeyPosition.department == department)
    if criticality:
        stmt = stmt.where(KeyPosition.criticality == criticality)
    positions = list(db.execute(stmt).scalars().all())

    if not positions:
        return {"error": "当前条件下没有关键岗位数据。", "total": 0}

    emp_names = {e.id: e for e in db.execute(select(Employee)).scalars().all()}

    rows = []
    for pos in positions:
        candidates = list(
            db.execute(
                select(SuccessionCandidate).where(
                    SuccessionCandidate.key_position_id == pos.id
                )
            ).scalars().all()
        )
        cand_rows = []
        for c in candidates:
            emp = emp_names.get(c.candidate_id)
            cand_rows.append(
                {
                    "name": emp.name if emp else "-",
                    "department": emp.department if emp else "-",
                    "job_level": emp.job_level if emp else "-",
                    "readiness": c.readiness,
                    "readiness_label": READINESS_LABEL.get(c.readiness, c.readiness),
                    "source": c.source,
                    "note": c.note or "",
                }
            )
        cand_rows.sort(key=lambda x: READINESS_ORDER.get(x["readiness"], 9))

        incumbent = emp_names.get(pos.incumbent_id)
        ready_now = [c for c in cand_rows if c["readiness"] == "ready_now"]
        if not cand_rows:
            risk = "无继任人选"
        elif ready_now:
            risk = "有立即就绪人选"
        elif any(c["readiness"] in ("ready_1y", "ready_2y") for c in cand_rows):
            risk = "仅有一年内就绪人选"
        else:
            risk = "人选均未就绪"

        rows.append(
            {
                "title": pos.title,
                "department": pos.department,
                "job_level": pos.job_level,
                "criticality": pos.criticality,
                "vacancy_risk": pos.vacancy_risk,
                "incumbent": incumbent.name if incumbent else "-",
                "candidate_count": len(cand_rows),
                "ready_now_count": len(ready_now),
                "coverage_depth": len(cand_rows),
                "risk": risk,
                "candidates": cand_rows,
                "advice": _succession_advice(pos.criticality, risk, len(cand_rows)),
            }
        )

    rows.sort(
        key=lambda x: (
            {"高": 0, "中": 1, "低": 2}.get(x["criticality"], 3),
            x["candidate_count"],
        )
    )

    total = len(rows)
    covered = [r for r in rows if r["candidate_count"] > 0]
    ready_now_positions = [r for r in rows if r["ready_now_count"] > 0]
    no_candidate = [r for r in rows if r["candidate_count"] == 0]
    risk_positions = [
        r for r in rows if r["candidate_count"] == 0 or r["ready_now_count"] == 0
    ]
    avg_depth = round(
        sum(r["candidate_count"] for r in rows) / total, 2
    ) if total else 0.0

    return {
        "department": department or "全部部门",
        "total": total,
        "coverage_rate": round(len(covered) / total, 3) if total else 0.0,
        "ready_now_rate": round(len(ready_now_positions) / total, 3) if total else 0.0,
        "avg_depth": avg_depth,
        "risk_position_count": len(risk_positions),
        "risk_positions": [
            {"title": r["title"], "department": r["department"],
             "criticality": r["criticality"], "risk": r["risk"]}
            for r in risk_positions[:8]
        ],
        "positions": rows,
        "basis": (
            "覆盖率 = 有候选人的关键岗位 / 关键岗位总数；"
            "立即就绪率 = 有 ready_now 人选的岗位 / 总数；"
            "梯队深度 = 岗位候选人数"
        ),
        "conclusion": (
            f"关键岗位 {total} 个，继任覆盖率 {round(len(covered) / total * 100, 1)}%，"
            f"立即就绪率 {round(len(ready_now_positions) / total * 100, 1)}%，"
            f"平均梯队深度 {avg_depth} 人。"
            + (
                f"其中 {len(no_candidate)} 个岗位完全没有继任人选，"
                f"{len(risk_positions) - len(no_candidate)} 个岗位缺少立即就绪人选，"
                f"需分别启动外部储备与内部加速培养。"
                if risk_positions
                else "各关键岗位均已配置立即就绪人选。"
            )
        ),
    }


def _succession_advice(criticality: str, risk: str, depth: int) -> str:
    if risk == "无继任人选":
        return "无任何继任人选，建议立即启动外部储备并指定临时负责人"
    if risk == "人选均未就绪":
        return "候选人准备度不足，建议搭配导师制与轮岗加速培养"
    if risk == "仅有一年内就绪人选":
        return "缺少立即就绪人选，建议为最接近者安排代理锻炼"
    if criticality == "高" and depth < 2:
        return "关键岗位仅 1 名继任者，单点风险高，建议补充第二梯队"
    return "继任梯队健康，按年度复盘更新人选"


# ---------------------------- 九、个人发展计划 IDP ----------------------------


def idp_view(
    db: Session,
    employee_name: str | None = None,
    department: str | None = None,
    period: str | None = None,
) -> dict:
    """学习发展体系中的个人发展计划 IDP：70-20-10 分布与执行进度。"""
    stmt = select(DevelopmentPlan, Employee).join(
        Employee, Employee.id == DevelopmentPlan.employee_id
    )
    if department:
        stmt = stmt.where(Employee.department == department)
    if period:
        stmt = stmt.where(DevelopmentPlan.period == period)
    if employee_name:
        stmt = stmt.where(Employee.name == employee_name)
    records = list(db.execute(stmt).all())

    if not records:
        return {
            "error": "当前条件下没有个人发展计划数据。",
            "total": 0,
        }

    by_emp: dict[str, list[dict]] = {}
    for plan, emp in records:
        by_emp.setdefault(emp.name, []).append(
            {
                "employee": emp.name,
                "department": emp.department,
                "job_level": emp.job_level,
                "period": plan.period,
                "goal": plan.goal,
                "bucket": plan.bucket,
                "action_type": plan.action_type,
                "action_name": plan.action_name,
                "due_date": str(plan.due_date) if plan.due_date else "-",
                "status": plan.status,
                "progress": plan.progress,
            }
        )

    people = []
    for name, items in sorted(by_emp.items()):
        done = [i for i in items if i["status"] == "已完成"]
        avg_progress = round(sum(i["progress"] for i in items) / len(items), 1)
        bucket_dist = {"70": 0, "20": 0, "10": 0}
        for i in items:
            bucket_dist[i["bucket"]] = bucket_dist.get(i["bucket"], 0) + 1
        people.append(
            {
                "employee": name,
                "department": items[0]["department"],
                "job_level": items[0]["job_level"],
                "period": items[0]["period"],
                "goal": items[0]["goal"],
                "action_count": len(items),
                "completed_count": len(done),
                "completion_rate": round(len(done) / len(items), 3),
                "avg_progress": avg_progress,
                "by_70_20_10": bucket_dist,
                "actions": items,
            }
        )

    people.sort(key=lambda x: -x["avg_progress"])
    total_actions = sum(p["action_count"] for p in people)
    total_done = sum(p["completed_count"] for p in people)
    overall_bucket = {"70": 0, "20": 0, "10": 0}
    for p in people:
        for k, v in p["by_70_20_10"].items():
            overall_bucket[k] = overall_bucket.get(k, 0) + v
    stalled = [p for p in people if p["avg_progress"] < 50]

    return {
        "department": department or "全部部门",
        "period": period or (records[0][0].period if records else "-"),
        "total_people": len(people),
        "total_actions": total_actions,
        "completed_actions": total_done,
        "overall_completion_rate": round(total_done / total_actions, 3) if total_actions else 0.0,
        "by_70_20_10": overall_bucket,
        "stalled_count": len(stalled),
        "stalled_people": [
            {"employee": p["employee"], "avg_progress": p["avg_progress"]}
            for p in stalled[:5]
        ],
        "people": people[:20],
        "basis": (
            "完成率 = 已完成行动项 / 行动项总数；"
            "70-20-10 = 在职历练 / 他人辅导 / 正式培训 的行动项分布"
        ),
        "conclusion": (
            f"共 {len(people)} 人制定了个人发展计划，合计 {total_actions} 个行动项，"
            f"完成率 {round(total_done / total_actions * 100, 1) if total_actions else 0}%。"
            + (
                f"其中 {len(stalled)} 人平均进度不足 50%，需要主管介入复盘。"
                if stalled
                else "整体推进正常。"
            )
        ),
    }


# ---------------------------- 十、人才任用建议 ----------------------------


def talent_placement(
    db: Session, department: str | None = None, period: str | None = None
) -> dict:
    """人才任用建议：结合盘点、任职资格与离职风险输出人员调整建议。"""
    review = talent_review(db, department=department, period=period)
    if review.get("error"):
        return review

    people = review["people"]
    if not people:
        return {"error": "当前条件下没有可评估人员。", "total": 0}

    # 任职资格匹配度（对照下一职级）
    standards = list(db.execute(select(TalentStandard)).scalars().all())
    grouped: dict[tuple[str, str], list[TalentStandard]] = {}
    for s in standards:
        grouped.setdefault((s.job_family, s.job_level), []).append(s)

    # 离职风险
    risk_map = {}
    try:
        from app.models import AttritionRisk

        risks = db.execute(select(AttritionRisk)).scalars().all()
        latest: dict[int, AttritionRisk] = {}
        for r in risks:
            prev = latest.get(r.employee_id)
            if prev is None or (r.period or "") >= (prev.period or ""):
                latest[r.employee_id] = r
        risk_map = {k: (v.risk_score, v.risk_level) for k, v in latest.items()}
    except Exception:  # 无风险数据时降级为不参与判断
        risk_map = {}

    promote, retain, activate, adjust, watch = [], [], [], [], []
    for p in people:
        emp = db.execute(
            select(Employee).where(Employee.id == p["id"])
        ).scalars().first()
        if not emp:
            continue

        target = NEXT_LEVEL.get(emp.job_level, emp.job_level)
        items = grouped.get((emp.job_family, target)) or grouped.get(
            (emp.job_family, emp.job_level)
        )
        match_rate = None
        if items:
            scores = _employee_scores(db, emp)
            total_weight = sum(i.weight for i in items) or 1.0
            earned = sum(
                (min(scores.get(i.dimension, 3.0) / i.pass_score, 1.0) if i.pass_score else 1.0)
                * i.weight
                for i in items
            )
            match_rate = round(earned / total_weight, 3)

        risk_score, risk_level = risk_map.get(emp.id, (0.0, "low"))
        base = {
            "name": emp.name,
            "department": emp.department,
            "job_level": emp.job_level,
            "performance": p["performance"],
            "potential": p["potential"],
            "grid_name": p["grid_name"],
            "match_rate": match_rate,
            "risk_score": risk_score,
            "risk_level": risk_level,
        }

        if (
            p["performance_band"] == "高"
            and p["potential_band"] == "高"
            and (match_rate or 0) >= 0.75
        ):
            base["suggestion"] = "晋升提拔"
            base["reason"] = "高绩效高潜且任职资格达标"
            base["action"] = f"纳入 {target} 晋升评审，同步明确新的挑战性任务"
            promote.append(base)
        elif p["performance_band"] == "高" and risk_level == "high":
            base["suggestion"] = "重点保留"
            base["reason"] = "高绩效但离职风险高"
            base["action"] = "启动保留面谈，优先给薪酬追平或晋升承诺"
            retain.append(base)
        elif p["potential_band"] == "高" and p["performance_band"] == "低":
            base["suggestion"] = "激活换岗"
            base["reason"] = "高潜低绩，可能是岗位匹配问题"
            base["action"] = "安排轮岗或换项目，配导师后再观察一个周期"
            activate.append(base)
        elif p["performance_band"] == "低" and p["potential_band"] == "低":
            base["suggestion"] = "调整或淘汰"
            base["reason"] = "低绩效低潜"
            base["action"] = "先走绩效改进计划（PIP），未改善则启动岗位调整"
            adjust.append(base)
        else:
            base["suggestion"] = "持续观察"
            base["reason"] = "绩效与潜力均处于中间档"
            base["action"] = "维持现有岗位，明确下一周期的提升目标"
            watch.append(base)

    groups = [
        ("晋升提拔", promote),
        ("重点保留", retain),
        ("激活换岗", activate),
        ("调整或淘汰", adjust),
        ("持续观察", watch),
    ]

    return {
        "department": department or "全部部门",
        "period": period or "最近一次",
        "total": len(people),
        "groups": [
            {
                "suggestion": label,
                "count": len(items),
                "people": sorted(
                    items,
                    key=lambda x: (-(x["match_rate"] or 0), -x["performance"]),
                )[:8],
            }
            for label, items in groups
        ],
        "basis": (
            "晋升：绩效高 且 潜力高 且 下一职级匹配度 ≥75%；"
            "保留：绩效高 且 离职风险为高；"
            "激活：潜力高 但 绩效低；"
            "调整：绩效低 且 潜力低"
        ),
        "conclusion": (
            f"共评估 {len(people)} 人：建议晋升 {len(promote)} 人、"
            f"重点保留 {len(retain)} 人、激活换岗 {len(activate)} 人、"
            f"调整或淘汰 {len(adjust)} 人、持续观察 {len(watch)} 人。"
            + (
                f"最优先动作是保留 {retain[0]['name']}"
                f"（离职风险 {retain[0]['risk_score']}）。"
                if retain
                else ""
            )
        ),
    }


__all__ = [
    "competency_model",
    "competency_profile",
    "development_program_tracking",
    "idp_view",
    "mentorship_view",
    "succession_plan",
    "talent_placement",
    "talent_pool_view",
    "talent_review",
    "talent_standard_match",
]
