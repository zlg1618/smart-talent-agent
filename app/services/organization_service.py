"""核心域 · 组织发展（Organization Development）确定性计算。

组织发展关注"组织如何长得好"，回答四个问题：
    架构是否合理    组织单元的层级深度、管理幅度与编制达成
    效能是否健康    人均产出、人工成本率与部门人效排名
    职级是否畅通    职族职级的金字塔分布、晋升率与拥堵情况
    变革是否可控    组织调整方案的影响人数与成本测算

所有分档、比率与结论均由 Python 计算，大模型只负责把结论讲清楚。
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Employee,
    JobArchitecture,
    OrgChange,
    OrgEffectiveness,
    OrgUnit,
)

# 编制达成率分档（下限，由高到低匹配）
FILL_RULE = [(0.95, "已满编"), (0.85, "接近满编"), (0.70, "缺口较大"), (0.0, "严重缺编")]

# 管理幅度健康区间
SPAN_HEALTHY = (4.0, 12.0)

# 组织层级深度参考值
DEPTH_HEALTHY = (3, 5)


def _fill_status(fill_rate: float) -> str:
    for threshold, label in FILL_RULE:
        if fill_rate >= threshold:
            return label
    return "严重缺编"


def _fill_advice(status: str, gap: int, span: float | None) -> str:
    if status == "严重缺编":
        return f"缺口 {gap} 人且达成率过低，优先拆分招聘批次或调整编制计划"
    if status == "缺口较大":
        return f"缺口 {gap} 人，建议加快招聘节奏并评估内部转岗补充"
    if status == "接近满编":
        return "接近满编，按业务节奏补足剩余岗位即可"
    if span is not None and span > SPAN_HEALTHY[1]:
        return "编制已满但管理幅度过宽，建议拆分团队或补充一线管理者"
    return "编制达成良好，维持现有节奏"


# ---------------------------- 一、组织架构与编制 ----------------------------


def org_structure(
    db: Session, department: str | None = None, period: str | None = None
) -> dict:
    """组织架构总览：层级深度、管理幅度、编制达成。"""
    stmt = select(OrgUnit)
    if department:
        stmt = stmt.where(OrgUnit.department == department)
    if period:
        stmt = stmt.where(OrgUnit.period == period)
    units = list(db.execute(stmt).scalars().all())

    if not units:
        return {
            "error": "当前条件下没有组织单元数据，请调整部门或周期后重试。",
            "total": 0,
        }

    # 实际在编以员工主数据为准，避免组织单元表与主数据不一致
    actual_map = dict(
        db.execute(
            select(Employee.department, func.count(Employee.id))
            .where(Employee.status == "在职")
            .group_by(Employee.department)
        ).all()
    )

    child_count: dict[str, int] = {}
    for u in units:
        if u.parent_name:
            child_count[u.parent_name] = child_count.get(u.parent_name, 0) + 1

    rows = []
    for u in units:
        actual = u.actual_headcount or actual_map.get(u.department, 0)
        planned = u.planned_headcount
        fill_rate = round(actual / planned, 3) if planned else 0.0
        gap = max(0, planned - actual)
        status = _fill_status(fill_rate)
        rows.append(
            {
                "name": u.name,
                "department": u.department,
                "parent": u.parent_name or "-",
                "level": u.level,
                "unit_type": u.unit_type,
                "manager": u.manager_name or "-",
                "planned": planned,
                "actual": actual,
                "gap": gap,
                "fill_rate": fill_rate,
                "status": status,
                "advice": _fill_advice(status, gap, None),
            }
        )

    rows.sort(key=lambda x: (x["level"], x["fill_rate"]))

    total_planned = sum(r["planned"] for r in rows)
    total_actual = sum(r["actual"] for r in rows)
    overall = round(total_actual / total_planned, 3) if total_planned else 0.0
    depth = max((r["level"] for r in rows), default=0)

    # 平均管理幅度 = 一线单元（无下级的团队）在编人数的平均值
    leaves = [r for r in rows if not child_count.get(r["name"])]
    avg_span = round(sum(r["actual"] for r in leaves) / len(leaves), 1) if leaves else 0.0

    if not leaves:
        span_comment = "当前组织单元层级扁平，无一线单元可用于计算管理幅度。"
    elif avg_span < SPAN_HEALTHY[0]:
        span_comment = f"平均管理幅度 {avg_span} 人偏窄，管理层冗余，建议合并团队。"
    elif avg_span > SPAN_HEALTHY[1]:
        span_comment = f"平均管理幅度 {avg_span} 人过宽，管理者负荷偏高，建议拆分或补配副手。"
    else:
        span_comment = f"平均管理幅度 {avg_span} 人处于健康区间。"

    if depth < DEPTH_HEALTHY[0]:
        depth_comment = f"组织层级 {depth} 层偏扁平，晋升通道可能不足。"
    elif depth > DEPTH_HEALTHY[1]:
        depth_comment = f"组织层级 {depth} 层偏深，决策链条偏长，建议压缩中间层。"
    else:
        depth_comment = f"组织层级 {depth} 层处于合理区间。"

    return {
        "period": period or (units[0].period if units else "-"),
        "department": department or "全部部门",
        "total_units": len(rows),
        "max_depth": depth,
        "avg_span_of_control": avg_span,
        "total_planned": total_planned,
        "total_actual": total_actual,
        "total_gap": max(0, total_planned - total_actual),
        "overall_fill_rate": overall,
        "shortage_units": [r for r in rows if r["status"] in ("缺口较大", "严重缺编")],
        "units": rows,
        "conclusion": (
            f"共 {len(rows)} 个组织单元，最深 {depth} 层，整体编制达成率 "
            f"{round(overall * 100, 1)}%（在编 {total_actual} / 编制 {total_planned}）。"
            f"{span_comment}{depth_comment}"
        ),
    }


# ---------------------------- 二、组织效能与人效 ----------------------------


def org_effectiveness(
    db: Session, department: str | None = None, period: str | None = None
) -> dict:
    """组织效能分析：人均产出、人工成本率与部门人效排名。"""
    stmt = select(OrgEffectiveness)
    if department:
        stmt = stmt.where(OrgEffectiveness.department == department)
    if period:
        stmt = stmt.where(OrgEffectiveness.period == period)
    records = list(db.execute(stmt).scalars().all())

    if not records:
        return {"error": "当前条件下没有组织效能数据。", "total": 0}

    rows = []
    for r in records:
        headcount = r.headcount or 0
        output_per_head = round(r.revenue / headcount, 1) if headcount else 0.0
        cost_rate = round(r.labor_cost / r.revenue, 3) if r.revenue else 0.0
        rows.append(
            {
                "department": r.department,
                "period": r.period,
                "headcount": headcount,
                "revenue": r.revenue,
                "labor_cost": r.labor_cost,
                "output_per_head": output_per_head,
                "cost_rate": cost_rate,
                "attrition_rate": r.attrition_rate,
                "span_of_control": r.span_of_control,
            }
        )

    avg_output = sum(r["output_per_head"] for r in rows) / len(rows)
    for r in rows:
        r["output_index"] = round(r["output_per_head"] / avg_output, 2) if avg_output else 0.0
        if r["output_index"] >= 1.15:
            r["tier"] = "人效领先"
        elif r["output_index"] >= 0.85:
            r["tier"] = "人效正常"
        else:
            r["tier"] = "人效偏低"
        r["advice"] = _effectiveness_advice(r)

    rows.sort(key=lambda x: -x["output_per_head"])

    total_headcount = sum(r["headcount"] for r in rows)
    total_revenue = sum(r["revenue"] for r in rows)
    total_cost = sum(r["labor_cost"] for r in rows)
    overall_output = round(total_revenue / total_headcount, 1) if total_headcount else 0.0
    overall_cost_rate = round(total_cost / total_revenue, 3) if total_revenue else 0.0
    low = [r for r in rows if r["tier"] == "人效偏低"]

    return {
        "period": period or (rows[0]["period"] if rows else "-"),
        "department": department or "全部部门",
        "total": len(rows),
        "total_headcount": total_headcount,
        "total_revenue": total_revenue,
        "total_labor_cost": total_cost,
        "overall_output_per_head": overall_output,
        "overall_cost_rate": overall_cost_rate,
        "avg_output_per_head": round(avg_output, 1),
        "low_efficiency_departments": low,
        "ranking": rows,
        "conclusion": (
            f"整体人均产出 {overall_output} 万元，人工成本率 "
            f"{round(overall_cost_rate * 100, 1)}%。"
            + (
                f"其中 {len(low)} 个部门人效低于均值 85%，"
                f"建议优先审查编制配置与流程瓶颈。"
                if low
                else "各部门人效分布均衡，无显著低效单元。"
            )
        ),
    }


def _effectiveness_advice(row: dict) -> str:
    if row["tier"] == "人效领先":
        return "人效领先，可作为标杆沉淀方法论并向其他部门复制"
    if row["tier"] == "人效偏低":
        if row["cost_rate"] and row["cost_rate"] > 0.6:
            return "人工成本率偏高，建议冻结扩编并优化人员结构"
        if row["attrition_rate"] and row["attrition_rate"] > 0.15:
            return "离职率偏高拖累人效，建议先解决保留问题再谈扩编"
        return "人效偏低，建议复盘岗位设置与产出口径"
    return "人效处于正常区间，保持现有配置"


# ---------------------------- 三、岗位职级体系 ----------------------------


def job_architecture(db: Session, department: str | None = None) -> dict:
    """岗位职级体系健康度：金字塔分布、晋升率与职级拥堵。"""
    stmt = select(JobArchitecture)
    if department:
        stmt = stmt.where(JobArchitecture.department == department)
    records = list(db.execute(stmt).scalars().all())

    if not records:
        return {"error": "当前条件下没有岗位职级体系数据。", "total": 0}

    # 实际在编按部门+职级统计，优先使用主数据
    actual_map = {
        (row[0], row[1]): row[2]
        for row in db.execute(
            select(Employee.department, Employee.job_level, func.count(Employee.id))
            .where(Employee.status == "在职")
            .group_by(Employee.department, Employee.job_level)
        ).all()
    }

    rows = []
    for r in records:
        actual = actual_map.get((r.department, r.job_level), r.headcount)
        band_width = (
            round((r.salary_max - r.salary_min) / r.salary_mid, 2) if r.salary_mid else 0.0
        )
        rows.append(
            {
                "department": r.department,
                "job_family": r.job_family,
                "job_level": r.job_level,
                "headcount": actual,
                "target_ratio": r.target_ratio,
                "avg_tenure": r.avg_tenure,
                "promotion_rate": r.promotion_rate,
                "salary_min": r.salary_min,
                "salary_mid": r.salary_mid,
                "salary_max": r.salary_max,
                "band_width": band_width,
            }
        )

    rows.sort(key=lambda x: (x["department"], x["job_level"]))

    # 按部门看职级分布形态
    by_dept: dict[str, list[dict]] = {}
    for r in rows:
        by_dept.setdefault(r["department"], []).append(r)

    families = []
    for dept, items in sorted(by_dept.items()):
        total = sum(i["headcount"] for i in items)
        if not total:
            continue
        base = sum(i["headcount"] for i in items if _is_junior(i["job_level"]))
        mid = sum(i["headcount"] for i in items if _is_middle(i["job_level"]))
        senior = sum(i["headcount"] for i in items if _is_senior(i["job_level"]))
        mid_ratio = round(mid / total, 3)
        if mid_ratio >= 0.6:
            shape = "腰部拥堵"
        elif base >= total * 0.6:
            shape = "基层偏重"
        elif senior >= total * 0.45:
            shape = "倒金字塔"
        else:
            shape = "结构均衡"
        avg_promo = round(
            sum(i["promotion_rate"] for i in items) / len(items), 3
        )
        families.append(
            {
                "department": dept,
                "total": total,
                "base": base,
                "mid": mid,
                "senior": senior,
                "mid_ratio": mid_ratio,
                "shape": shape,
                "avg_promotion_rate": avg_promo,
                "advice": _architecture_advice(shape, avg_promo),
            }
        )

    congested = [f for f in families if f["shape"] == "腰部拥堵"]
    low_promo = [f for f in families if f["avg_promotion_rate"] < 0.08]

    return {
        "department": department or "全部部门",
        "total_levels": len(rows),
        "total_headcount": sum(r["headcount"] for r in rows),
        "by_department": families,
        "levels": rows,
        "congested_departments": congested,
        "low_promotion_departments": low_promo,
        "conclusion": (
            f"共 {len(rows)} 个职级配置，覆盖 {sum(r['headcount'] for r in rows)} 人。"
            + (
                f"其中 {len(congested)} 个部门出现腰部拥堵（中级占比过高），"
                f"晋升通道需要扩容。"
                if congested
                else "职级分布整体健康。"
            )
            + (
                f"另有 {len(low_promo)} 个部门年均晋升率低于 8%，"
                f"存在晋升停滞风险。"
                if low_promo
                else ""
            )
        ),
    }


def _is_junior(level: str) -> bool:
    return bool(level) and level.upper().startswith("P") and _num(level) <= 5


def _is_middle(level: str) -> bool:
    return bool(level) and level.upper().startswith("P") and _num(level) in (6, 7)


def _is_senior(level: str) -> bool:
    if not level:
        return False
    return level.upper().startswith("M") or (level.upper().startswith("P") and _num(level) >= 8)


def _num(level: str) -> int:
    digits = "".join(ch for ch in level if ch.isdigit())
    return int(digits) if digits else 0


def _architecture_advice(shape: str, avg_promo: float) -> str:
    if shape == "腰部拥堵":
        return "中级职级堆积，建议开放高级职级名额或拆分职族并行通道"
    if shape == "基层偏重":
        return "基层占比偏高，需加强带教与晋升通道建设"
    if shape == "倒金字塔":
        return "高职级占比偏高，管理成本压力大，建议控制高职级增量"
    if avg_promo < 0.08:
        return "结构均衡但晋升率偏低，建议明确晋升节奏"
    return "职级结构健康，维持现有晋升节奏"


# ---------------------------- 四、组织变革模拟 ----------------------------


def org_change_simulation(
    db: Session, department: str | None = None, change_type: str | None = None
) -> dict:
    """组织变革模拟：调整方案的影响人数与成本测算。"""
    stmt = select(OrgChange)
    if department:
        stmt = stmt.where(OrgChange.department == department)
    if change_type:
        stmt = stmt.where(OrgChange.change_type == change_type)
    plans = list(db.execute(stmt).scalars().all())

    if not plans:
        return {"error": "当前条件下没有组织变革方案数据。", "total": 0}

    rows = []
    for p in plans:
        affected = p.affected_headcount or 0
        cost = p.cost_impact or 0.0
        per_head = round(cost / affected, 2) if affected else 0.0
        if p.status == "已完成":
            risk = "已落地"
        elif affected >= 30:
            risk = "高影响"
        elif affected >= 10:
            risk = "中影响"
        else:
            risk = "低影响"
        rows.append(
            {
                "name": p.name,
                "department": p.department,
                "change_type": p.change_type,
                "source_unit": p.source_unit or "-",
                "target_unit": p.target_unit or "-",
                "affected_headcount": affected,
                "cost_impact": cost,
                "cost_per_head": per_head,
                "status": p.status,
                "risk": risk,
                "target_date": str(p.target_date) if p.target_date else "-",
                "note": p.note or "",
                "advice": _change_advice(p.change_type, risk, affected),
            }
        )

    rows.sort(key=lambda x: -x["affected_headcount"])

    total_affected = sum(r["affected_headcount"] for r in rows)
    total_cost = round(sum(r["cost_impact"] for r in rows), 2)
    pending = [r for r in rows if r["status"] != "已完成"]
    high = [r for r in rows if r["risk"] == "高影响"]

    return {
        "department": department or "全部部门",
        "total": len(rows),
        "total_affected": total_affected,
        "total_cost_impact": total_cost,
        "pending_count": len(pending),
        "high_impact_plans": high,
        "plans": rows,
        "conclusion": (
            f"共 {len(rows)} 个组织变革方案，累计影响 {total_affected} 人，"
            f"成本影响 {total_cost} 万元。"
            + (
                f"其中 {len(high)} 个为高影响方案（影响 30 人及以上），"
                f"建议提前做沟通方案与人员安置预案。"
                if high
                else "暂无高影响方案，可按计划推进。"
            )
        ),
    }


def _change_advice(change_type: str, risk: str, affected: int) -> str:
    base = {
        "合并": "合并后需重新明确汇报线与岗位职责，避免职责重叠",
        "拆分": "拆分后需补齐管理岗位，防止管理幅度失衡",
        "扩编": "扩编需同步核对预算与办公资源，分批到位更稳妥",
        "缩编": "缩编需配套安置方案与合规流程，优先内部转岗",
        "新设": "新设单元需先明确定位与编制，再启动招聘",
        "调整": "调整方案需明确新旧职责切换时点与过渡安排",
    }.get(change_type, "变更前完成影响评估与沟通计划")
    if risk == "高影响":
        return f"{base}；影响 {affected} 人，建议高管牵头并设专项沟通窗口"
    return base


__all__ = [
    "job_architecture",
    "org_change_simulation",
    "org_effectiveness",
    "org_structure",
]
