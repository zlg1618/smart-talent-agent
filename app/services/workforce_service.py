"""HRIS · 人力资源规划域（Workforce Planning）确定性计算。

覆盖三块：
    编制规划      编制达成率、在招缺口、预算执行率
    供需预测      自然流失、内部供给、外部招聘需求测算
    离职风险      六因子加权风险分、分级与保留建议

风险分与缺口测算全部是确定性公式，模型只解释结论。
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AttritionRisk,
    Employee,
    HeadcountPlan,
    JobPost,
    KeyPosition,
    SuccessionPlan,
    WorkforceForecast,
)

# 离职风险因子权重，合计 1.0
RISK_WEIGHTS = {
    "factor_tenure": 0.15,        # 司龄短更容易走
    "factor_performance": 0.15,   # 高绩效但未获晋升
    "factor_compensation": 0.20,  # 薪酬竞争力不足
    "factor_promotion": 0.20,     # 晋升停滞
    "factor_engagement": 0.15,    # 敬业度低
    "factor_market": 0.15,        # 外部市场热度
}

RISK_LEVEL_RULE = [(70, "high"), (45, "medium"), (0, "low")]

RETENTION_ACTION = {
    "factor_compensation": "参照带宽中位值启动薪酬追平，或给一次性保留奖金",
    "factor_promotion": "明确晋升路径与时间表，或横向轮岗提供新挑战",
    "factor_engagement": "安排一对一深度访谈，识别真实诉求并有针对性干预",
    "factor_performance": "确保贡献被看见，纳入关键项目与继任池",
    "factor_tenure": "强化入职 6 个月内的融入辅导与导师机制",
    "factor_market": "对标外部市场薪酬并评估职衔竞争力",
}


def headcount_review(db: Session, department: str | None = None, period: str | None = None) -> dict:
    """编制达成审查：直接与在编、在招、预算执行对比。"""
    plans = list(db.execute(select(HeadcountPlan)).scalars().all())
    if period:
        plans = [p for p in plans if p.period == period]
    if department:
        plans = [p for p in plans if p.department == department]
    if not plans:
        return {"error": "暂无编制计划数据"}

    # 实际在编按数据库实时统计，覆盖预算值
    actual_map = dict(
        db.execute(
            select(Employee.department, func.count(Employee.id))
            .where(Employee.status == "在职")
            .group_by(Employee.department)
        ).all()
    )
    open_req_map = {}
    for row in db.execute(
        select(JobPost.department, func.count(JobPost.id))
        .where(JobPost.status == "open")
        .group_by(JobPost.department)
    ).all():
        open_req_map[row[0]] = row[1]

    rows = []
    for p in plans:
        actual = actual_map.get(p.department, 0)
        fill_rate = round(actual / p.planned_headcount, 3) if p.planned_headcount else 0.0
        budget_usage = round(p.actual_cost / p.budget_amount, 3) if p.budget_amount else 0.0
        open_req = open_req_map.get(p.department, 0)
        gap = max(0, p.planned_headcount - actual)
        if fill_rate >= 0.95:
            status = "已满编"
        elif fill_rate >= 0.85:
            status = "接近满编"
        elif fill_rate >= 0.7:
            status = "缺口较大"
        else:
            status = "严重缺编"
        rows.append(
            {
                "department": p.department,
                "period": p.period,
                "planned": p.planned_headcount,
                "actual": actual,
                "gap": gap,
                "open_reqs": open_req,
                "fill_rate": fill_rate,
                "budget_amount": p.budget_amount,
                "actual_cost": p.actual_cost,
                "budget_usage": budget_usage,
                "status": status,
                "advice": _headcount_advice(status, gap, open_req, budget_usage),
            }
        )

    rows.sort(key=lambda x: x["fill_rate"])
    total_planned = sum(r["planned"] for r in rows)
    total_actual = sum(r["actual"] for r in rows)
    overall = round(total_actual / total_planned, 3) if total_planned else 0.0

    return {
        "period": period or (rows[0]["period"] if rows else "-"),
        "department": department or "全部部门",
        "total_planned": total_planned,
        "total_actual": total_actual,
        "total_gap": max(0, total_planned - total_actual),
        "overall_fill_rate": overall,
        "shortage_departments": [r for r in rows if r["status"] in ("缺口较大", "严重缺编")],
        "over_budget_departments": [r for r in rows if r["budget_usage"] > 1.05],
        "plans": rows,
        "conclusion": (
            f"整体编制达成率 {round(overall * 100, 1)}%（在编 {total_actual} / 编制 "
            f"{total_planned}），缺口 {max(0, total_planned - total_actual)} 人。"
            + (
                f"其中 {sum(1 for r in rows if r['status'] in ('缺口较大', '严重缺编'))} "
                f"个部门缺口较大，建议优先配置招聘资源。"
                if any(r["status"] in ("缺口较大", "严重缺编") for r in rows)
                else "各部门编制达成良好。"
            )
        ),
    }


def _headcount_advice(status: str, gap: int, open_req: int, usage: float) -> str:
    if status == "严重缺编":
        return (
            f"缺口 {gap} 人，当前在招 {open_req} 个需求，"
            f"{'招聘力度不足，建议增开渠道或放宽筛选标准' if open_req < gap else '招聘已覆盖缺口，需关注进度'}"
        )
    if status == "缺口较大":
        return f"缺口 {gap} 人，建议优先补齐关键岗位"
    if usage > 1.05:
        return f"编制基本达成，但人力成本已超预算 {round((usage - 1) * 100, 1)}%，需控编"
    return "编制与预算均在合理区间"


def supply_demand_forecast(
    db: Session, department: str | None = None, scenario: str = "baseline"
) -> dict:
    """人力供需预测：自然流失 + 业务增量对内外部供给的影响。"""
    forecasts = list(db.execute(select(WorkforceForecast)).scalars().all())
    if department:
        forecasts = [f for f in forecasts if f.department == department]
    forecasts = [f for f in forecasts if f.scenario == scenario]
    if not forecasts:
        return {"error": f"暂无 {scenario} 情景下的人力预测数据"}

    rows = []
    for f in forecasts:
        net_demand = max(0, f.natural_attrition + f.demand_growth)
        supply_gap = max(0, net_demand - f.internal_supply)
        external_need = f.external_hire_need or supply_gap
        coverage = round(f.internal_supply / net_demand, 3) if net_demand else 1.0
        if coverage >= 0.8:
            status = "内部可满足"
        elif coverage >= 0.5:
            status = "部分需外部补充"
        else:
            status = "高度依赖外部招聘"
        rows.append(
            {
                "department": f.department,
                "job_level": f.job_level,
                "scenario": f.scenario,
                "current_supply": f.current_supply,
                "natural_attrition": f.natural_attrition,
                "demand_growth": f.demand_growth,
                "net_demand": round(net_demand, 1),
                "internal_supply": f.internal_supply,
                "external_hire_need": external_need,
                "internal_coverage": coverage,
                "status": status,
            }
        )

    rows.sort(key=lambda x: -x["external_hire_need"])
    total_internal = sum(r["internal_supply"] for r in rows)
    # 招聘需求按人头取整：不能招 0.4 个人
    total_external = round(sum(r["external_hire_need"] for r in rows))
    total_demand = round(sum(r["net_demand"] for r in rows))

    return {
        "department": department or "全部部门",
        "scenario": scenario,
        "forecast_rows": len(rows),
        "total_net_demand": total_demand,
        "total_internal_supply": total_internal,
        "total_external_hire": total_external,
        "internal_coverage": round(total_internal / total_demand, 3) if total_demand else 1.0,
        "rows": rows,
        "hotspots": rows[:8],
        "conclusion": (
            f"{scenario} 情景下净需求 {total_demand} 人，"
            f"内部可供给 {total_internal} 人，仍需外部招聘 {total_external} 人。"
            + (
                f"缺口最大的为「{rows[0]['department']} / {rows[0]['job_level']}」，"
                f"需外部补充 {rows[0]['external_hire_need']} 人。"
                if rows
                else ""
            )
        ),
    }


def attrition_risk_scan(
    db: Session, department: str | None = None, only_high: bool = False
) -> dict:
    """离职风险扫描：识别高风险人群与首要风险因子。"""
    risks = list(db.execute(select(AttritionRisk)).scalars().all())
    emps = {e.id: e for e in db.execute(select(Employee)).scalars().all()}

    rows = []
    for r in risks:
        emp = emps.get(r.employee_id)
        if not emp or emp.status != "在职":
            continue
        if department and emp.department != department:
            continue
        # 六因子加权，缺失记录时按库内评分兜底
        computed = sum(
            getattr(r, field, 0.0) or 0.0 for field in RISK_WEIGHTS
        )
        score = r.risk_score or round(sum(
            (getattr(r, field, 0.0) or 0.0) * weight * 100
            for field, weight in RISK_WEIGHTS.items()
        ), 1)
        top_factor = max(RISK_WEIGHTS, key=lambda f: getattr(r, f, 0.0) or 0.0)
        level = "low"
        for threshold, label in RISK_LEVEL_RULE:
            if score >= threshold:
                level = label
                break
        rows.append(
            {
                "id": emp.id,
                "name": emp.name,
                "department": emp.department,
                "position_title": emp.position_title,
                "job_level": emp.job_level,
                "risk_score": score,
                "risk_level": level,
                "top_factor": top_factor,
                "top_factor_label": _factor_label(top_factor),
                "key_reason": r.key_reason,
                "retention_action": r.retention_action or RETENTION_ACTION[top_factor],
            }
        )

    if only_high:
        rows = [r for r in rows if r["risk_level"] == "high"]
    rows.sort(key=lambda x: -x["risk_score"])

    high = [r for r in rows if r["risk_level"] == "high"]
    medium = [r for r in rows if r["risk_level"] == "medium"]

    # 关键岗位交叉风险：既是关键岗又是高风险
    key_emp_ids = {p.incumbent_id for p in db.execute(select(KeyPosition)).scalars().all()}
    critical = [r for r in high if r["id"] in key_emp_ids]

    return {
        "department": department or "全部部门",
        "scanned_count": len(rows),
        "high_risk_count": len(high),
        "medium_risk_count": len(medium),
        "critical_position_risk": len(critical),
        "people": rows[:20],
        "critical_position_people": critical[:10],
        "conclusion": (
            f"扫描 {len(rows)} 人，高风险 {len(high)} 人（占 "
            f"{round(len(high) / len(rows) * 100, 1) if rows else 0}%）。"
            + (
                f"其中 {len(critical)} 人身处关键岗位，一旦流失将直接影响业务连续性，"
                f"建议立即启动保留方案并确认继任人选。"
                if critical
                else ""
            )
        ),
    }


def _factor_label(field: str) -> str:
    return {
        "factor_tenure": "司龄过短",
        "factor_performance": "绩效未被认可",
        "factor_compensation": "薪酬缺乏竞争力",
        "factor_promotion": "晋升停滞",
        "factor_engagement": "敬业度偏低",
        "factor_market": "外部机会吸引",
    }.get(field, field)


def succession_coverage_link(db: Session, period: str | None = None) -> dict:
    """把规划域与继任域连起来：高风险在岗 + 无继任覆盖 = 最高优先级。"""
    from app.services import succession_service

    succession = succession_service.build_succession_map(db)
    covered_ids = set()
    for pos in succession.get("positions", []):
        if pos.get("candidates"):
            covered_ids.add(pos.get("incumbent_id"))

    scan = attrition_risk_scan(db, only_high=True)
    uncovered = [p for p in scan["people"] if p["id"] not in covered_ids]

    return {
        "period": period or "-",
        "high_risk_total": scan["high_risk_count"],
        "uncovered_high_risk": len(uncovered),
        "uncovered_people": uncovered[:10],
        "conclusion": (
            f"高风险人员 {scan['high_risk_count']} 人中，"
            f"{len(uncovered)} 人所在岗位没有继任候选人。"
            + (
                "这类组合一旦发生离职将出现真空，需立即指定接班人或启动外部储备。"
                if uncovered
                else "高风险岗位均已配置继任人选。"
            )
        ),
    }


__all__ = [
    "attrition_risk_scan",
    "headcount_review",
    "succession_coverage_link",
    "supply_demand_forecast",
]
