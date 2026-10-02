"""HRIS · 绩效管理域（Performance Management）确定性计算。

覆盖四块：
    目标达成      OKR / KPI 加权达成率
    绩效评估      自评 vs 主管评偏差分析
    强制分布      S/A/B/C/D 校准前后分布校验与调整建议
    改进计划      PIP 命中 Mauve infra 人群识别与辅导建议

所有计算由 Python 完成，模型不参与打分。
"""

from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Employee,
    ImprovementPlan,
    PerformanceGoal,
    PerformanceRecord,
    PerformanceReview,
)

# 强制分布标准：{"等级": (下限, 上限)}
FORCED_DISTRIBUTION = {
    "S": (0.00, 0.10),
    "A": (0.00, 0.25),
    "B": (0.40, 0.70),
    "C": (0.05, 0.20),
    "D": (0.00, 0.10),
}

RATING_LABEL = [(4.5, "S"), (4.0, "A"), (3.2, "B"), (2.5, "C"), (0.0, "D")]


def _label_of(score: float) -> str:
    for threshold, label in RATING_LABEL:
        if score >= threshold:
            return label
    return "D"


def goal_achievement(
    db: Session, department: str | None = None, period: str | None = None
) -> dict:
    """目标加权达成率分析。"""
    period = period or _latest_period(db)
    stmt = select(PerformanceGoal).where(PerformanceGoal.period == period)
    if department:
        emp_ids = _active_employee_ids(db, department)
        stmt = stmt.where(PerformanceGoal.employee_id.in_(emp_ids))
    goals = list(db.execute(stmt).scalars().all())
    if not goals:
        return {"error": f"{period} 暂无绩效目标数据"}

    by_emp: dict[int, list[PerformanceGoal]] = {}
    for g in goals:
        by_emp.setdefault(g.employee_id, []).append(g)

    emps = {e.id: e for e in db.execute(select(Employee)).scalars().all()}

    rows = []
    for emp_id, gs in by_emp.items():
        emp = emps.get(emp_id)
        if not emp:
            continue
        total_w = sum(g.weight for g in gs) or 1.0
        achieved = 0.0
        completed_cnt = 0
        for g in gs:
            rate = min(1.0, g.actual_value / g.target_value) if g.target_value else 0.0
            achieved += rate * g.weight
            if g.status == "completed":
                completed_cnt += 1
        rows.append(
            {
                "id": emp.id,
                "name": emp.name,
                "department": emp.department,
                "goal_count": len(gs),
                "completed_count": completed_cnt,
                "at_risk_count": sum(1 for g in gs if g.status in ("at_risk", "missed")),
                "achievement_rate": round(achieved / total_w, 3),
            }
        )

    rows.sort(key=lambda x: -x["achievement_rate"])
    n = len(rows)
    avg = round(sum(r["achievement_rate"] for r in rows) / n, 3) if n else 0.0
    low = [r for r in rows if r["achievement_rate"] < 0.7]
    at_risk = [r for r in rows if r["at_risk_count"] > 0]

    return {
        "department": department or "全部部门",
        "period": period,
        "employee_count": n,
        "goal_count": len(goals),
        "avg_achievement": avg,
        "low_achiever_count": len(low),
        "at_risk_count": len(at_risk),
        "top10": rows[:10],
        "bottom10": rows[-10:],
        "conclusion": (
            f"{period} 共跟踪 {len(goals)} 条目标，覆盖 {n} 人，平均达成率 "
            f"{round(avg * 100, 1)}%。"
            + (
                f"其中 {len(low)} 人达成率低于 70%，{len(at_risk)} 人有目标处于风险状态，"
                f"建议逐一复盘卡点。"
                if low or at_risk
                else "整体达成情况良好。"
            )
        ),
    }


def review_deviation(db: Session, department: str | None = None, period: str | None = None) -> dict:
    """自评与主管评的偏差分析，识别认知落差大的人群。"""
    period = period or _latest_period(db)
    stmt = select(PerformanceReview).where(PerformanceReview.period == period)
    if department:
        emp_ids = _active_employee_ids(db, department)
        stmt = stmt.where(PerformanceReview.employee_id.in_(emp_ids))
    reviews = list(db.execute(stmt).scalars().all())
    if not reviews:
        return {"error": f"{period} 暂无绩效评估数据"}

    emps = {e.id: e for e in db.execute(select(Employee)).scalars().all()}
    rows = []
    for r in reviews:
        emp = emps.get(r.employee_id)
        if not emp:
            continue
        delta = round(r.manager_score - r.self_score, 2)
        if abs(delta) >= 1.0:
            kind = "严重低估" if delta > 0 else "严重高估"
        elif abs(delta) >= 0.5:
            kind = "低估" if delta > 0 else "高估"
        else:
            kind = "一致"
        rows.append(
            {
                "id": emp.id,
                "name": emp.name,
                "department": emp.department,
                "self_score": r.self_score,
                "manager_score": r.manager_score,
                "calibrated_score": r.calibrated_score,
                "delta": delta,
                "kind": kind,
                "rating_label": r.rating_label,
            }
        )

    rows.sort(key=lambda x: -abs(x["delta"]))
    n = len(rows)
    avg_abs_gap = round(sum(abs(x["delta"]) for x in rows) / n, 2) if n else 0.0
    big_gap = [x for x in rows if abs(x["delta"]) >= 1.0]

    return {
        "department": department or "全部部门",
        "period": period,
        "review_count": n,
        "avg_abs_gap": avg_abs_gap,
        "big_gap_count": len(big_gap),
        "big_gap_people": big_gap[:10],
        "conclusion": (
            f"{period} 共 {n} 条评估记录，自评与主管评平均绝对偏差 {avg_abs_gap} 分。"
            + (
                f"其中 {len(big_gap)} 人偏差超过 1 分，需在绩效面谈中对齐评价标准和证据。"
                if big_gap
                else "评价标尺基本一致。"
            )
        ),
    }


def distribution_check(db: Session, department: str | None = None, period: str | None = None) -> dict:
    """强制分布校验：校准后的等级分布是否落在标准区间内。"""
    period = period or _latest_period(db)
    stmt = select(PerformanceReview).where(PerformanceReview.period == period)
    if department:
        emp_ids = _active_employee_ids(db, department)
        stmt = stmt.where(PerformanceReview.employee_id.in_(emp_ids))
    reviews = list(db.execute(stmt).scalars().all())
    if not reviews:
        return {"error": f"{period} 暂无绩效校准数据"}

    final = Counter(
        (r.rating_label or _label_of(r.calibrated_score or r.manager_score)) for r in reviews
    )
    n = len(reviews)

    rows, deviations = [], []
    for label, (low, high) in FORCED_DISTRIBUTION.items():
        cnt = final.get(label, 0)
        share = round(cnt / n, 3) if n else 0.0
        within = low <= share <= high
        rows.append(
            {
                "rating": label,
                "count": cnt,
                "share": share,
                "standard": [low, high],
                "within_standard": within,
            }
        )
        if not within:
            direction = "占比过高" if share > high else "占比过低"
            need = (
                int((share - high) * n) if share > high else int((low - share) * n)
            )
            deviations.append(
                {
                    "rating": label,
                    "direction": direction,
                    "adjust_count": abs(need),
                    "advice": _distribution_advice(label, direction, abs(need)),
                }
            )

    return {
        "department": department or "全部部门",
        "period": period,
        "total_reviewed": n,
        "distribution": rows,
        "deviation_count": len(deviations),
        "deviations": deviations,
        "conclusion": (
            f"{period} 参与校准 {n} 人。"
            + (
                f"有 {len(deviations)} 个等级偏离强制分布标准，建议在校准会上重点讨论。"
                if deviations
                else "各等级分布均符合强制分布标准。"
            )
        ),
    }


def _distribution_advice(rating: str, direction: str, count: int) -> str:
    action = {
        ("S", "占比过高"): "复核 S 标准的执行一致性，非极少数顶尖贡献建议下调至 A",
        ("S", "占比过低"): "核实是否有被漏评的高绩效者，必要时补提",
        ("D", "占比过高"): "区分是能力问题还是管理问题，先做管理者辅导",
        ("D", "占比过低"): "核实是否存在回避给低分的宽松倾向",
        ("C", "占比过高"): "确认绩效标准是否被普遍拔高，检查目标设定合理性",
        ("C", "占比过低"): "核实是否存在集中给 B 的中庸倾向",
    }
    return action.get((rating, direction), f"建议调整约 {count} 人以对齐强制分布")


def improvement_tracking(db: Session, department: str | None = None) -> dict:
    """PIP 改进计划跟进：命中人群与尚未改善的员工。"""
    stmt = select(ImprovementPlan)
    if department:
        emp_ids = _active_employee_ids(db, department)
        stmt = stmt.where(ImprovementPlan.employee_id.in_(emp_ids))
    plans = list(db.execute(stmt).scalars().all())

    emps = {e.id: e for e in db.execute(select(Employee)).scalars().all()}
    rows = []
    for p in plans:
        emp = emps.get(p.employee_id)
        if not emp:
            continue
        latest = db.execute(
            select(PerformanceRecord)
            .where(PerformanceRecord.employee_id == p.employee_id)
            .order_by(PerformanceRecord.period.desc())
        ).scalars().first()
        rows.append(
            {
                "id": emp.id,
                "name": emp.name,
                "department": emp.department,
                "period": p.period,
                "target_score": p.target_score,
                "current_score": latest.score if latest else 0.0,
                "gap": round((p.target_score or 0) - (latest.score if latest else 0), 2),
                "outcome": p.outcome,
                "status": "已达标" if latest and latest.score >= p.target_score else "未达标",
            }
        )

    ongoing = [r for r in rows if r["outcome"] == "ongoing"]
    passed = [r for r in rows if r["outcome"] == "passed"]
    failed = [r for r in rows if r["outcome"] == "failed"]

    return {
        "department": department or "全部部门",
        "total": len(rows),
        "ongoing": len(ongoing),
        "passed": len(passed),
        "failed": len(failed),
        "people": rows,
        "conclusion": (
            f"共 {len(rows)} 份改进计划：进行中 {len(ongoing)}、已通过 {len(passed)}、"
            f"未通过 {len(failed)}。"
            + (
                f"未通过者建议启动岗位调整或协商解除流程。"
                if failed
                else "暂无未通过的改进计划。"
            )
        ),
    }


# ------------------ 辅助 ------------------


def _latest_period(db: Session) -> str:
    p = db.execute(
        select(PerformanceReview.period)
        .group_by(PerformanceReview.period)
        .order_by(PerformanceReview.period.desc())
    ).scalars().first()
    if p:
        return p
    return (
        db.execute(
            select(PerformanceRecord.period)
            .group_by(PerformanceRecord.period)
            .order_by(PerformanceRecord.period.desc())
        ).scalars().first()
        or "2025H1"
    )


def _active_employee_ids(db: Session, department: str) -> list[int]:
    return [
        e.id
        for e in db.execute(
            select(Employee.id).where(
                Employee.department == department, Employee.status == "在职"
            )
        ).scalars().all()
    ]


__all__ = [
    "distribution_check",
    "goal_achievement",
    "improvement_tracking",
    "review_deviation",
]
