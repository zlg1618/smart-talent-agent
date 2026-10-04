"""核心域 · 组织发展（Organization Development）确定性计算。

组织发展（OD）的对象是组织、团队、架构、机制与文化，覆盖六类工作：

    组织诊断        健康度调研 + 组织扫描（7S / 6-BOX / 五维框架），定位痛点瓶颈
    架构与管控设计  组织模式、权责划分、分权集权、层级优化、定岗定编
    战略解码        公司战略 → 组织目标 → 部门目标的拆解与追踪
    组织变革管理    扩张 / 并购 / 转型的推进节奏、阻力与影响测算
    文化与氛围      价值观落地、组织氛围、员工敬业度
    组织效能        人效与人力成本分析，输出组织层面改进方案

所有分档、比率与结论均由 Python 计算，大模型只负责把结论讲清楚；
每个结果都带 basis 字段，说明分数是怎么算出来的。
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    CultureSurvey,
    Employee,
    JobArchitecture,
    OrgChange,
    OrgEffectiveness,
    OrgHealthSurvey,
    OrgScan,
    OrgUnit,
    StrategicGoal,
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
                "org_model": u.org_model,
                "control_mode": u.control_mode,
                "authority": u.authority,
                "decision_rights": u.decision_rights,
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
        "org_model_distribution": _distribution(rows, "org_model"),
        "control_mode_distribution": _distribution(rows, "control_mode"),
        "authority_distribution": _distribution(rows, "authority"),
        "units": rows,
        "basis": (
            "编制达成率 = 在编 / 编制；平均管理幅度 = 一线单元在编人数均值；"
            "层级深度 = max(level)"
        ),
        "conclusion": (
            f"共 {len(rows)} 个组织单元，最深 {depth} 层，整体编制达成率 "
            f"{round(overall * 100, 1)}%（在编 {total_actual} / 编制 {total_planned}）。"
            f"{span_comment}{depth_comment}"
        ),
    }


def _distribution(rows: list[dict], key: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for r in rows:
        value = r.get(key) or "-"
        result[value] = result.get(value, 0) + 1
    return dict(sorted(result.items(), key=lambda kv: -kv[1]))


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


# ---------------------------- 五、组织诊断 ----------------------------

# 三种诊断框架的维度定义
SCAN_FRAMEWORKS: dict[str, list[str]] = {
    "seven_s": ["战略", "结构", "制度", "共同价值观", "风格", "人员", "技能"],
    "six_box": ["使命目标", "组织", "关系", "激励", "领导", "支持"],
    "five_dim": ["战略", "组织", "人才", "机制", "文化"],
}

FRAMEWORK_LABELS = {
    "seven_s": "麦肯锡 7S",
    "six_box": "Weisbord 6-BOX",
    "five_dim": "五维诊断框架",
}

# 组织健康度调研维度
HEALTH_DIMENSIONS = [
    "战略清晰",
    "组织架构",
    "流程效率",
    "人才供给",
    "文化氛围",
    "激励机制",
    "协同效率",
]


def org_diagnosis(
    db: Session,
    department: str | None = None,
    period: str | None = None,
    framework: str | None = None,
) -> dict:
    """组织诊断：健康度调研 + 组织扫描（7S / 6-BOX / 五维框架）。

    输出组织健康分、分维度差距、已识别痛点与瓶颈排序。
    """
    # ---------- 1. 组织健康度调研 ----------
    stmt = select(OrgHealthSurvey)
    if department:
        stmt = stmt.where(OrgHealthSurvey.department == department)
    if period:
        stmt = stmt.where(OrgHealthSurvey.period == period)
    surveys = list(db.execute(stmt).scalars().all())

    health_rows = []
    if surveys:
        by_dim: dict[str, list[OrgHealthSurvey]] = {}
        for s in surveys:
            by_dim.setdefault(s.dimension, []).append(s)
        for dim, items in sorted(by_dim.items()):
            score = round(sum(i.score for i in items) / len(items), 2)
            benchmark = round(sum(i.benchmark for i in items) / len(items), 2)
            gap = round(score - benchmark, 2)
            if gap <= -0.5:
                level = "明显短板"
            elif gap < 0:
                level = "低于基准"
            elif gap < 0.3:
                level = "基本达标"
            else:
                level = "优于基准"
            health_rows.append(
                {
                    "dimension": dim,
                    "score": score,
                    "benchmark": benchmark,
                    "gap": gap,
                    "level": level,
                    "sample": sum(i.sample for i in items),
                    "advice": _health_advice(dim, level),
                }
            )
        health_rows.sort(key=lambda x: x["gap"])
        health_score = round(sum(r["score"] for r in health_rows) / len(health_rows), 2)
    else:
        health_score = 0.0

    # ---------- 2. 组织扫描 ----------
    scan_stmt = select(OrgScan)
    if department:
        scan_stmt = scan_stmt.where(OrgScan.department == department)
    if period:
        scan_stmt = scan_stmt.where(OrgScan.period == period)
    if framework:
        scan_stmt = scan_stmt.where(OrgScan.framework == framework)
    scans = list(db.execute(scan_stmt).scalars().all())

    scan_rows = []
    for s in scans:
        gap = round(s.current_score - s.target_score, 2)
        scan_rows.append(
            {
                "framework": s.framework,
                "framework_label": FRAMEWORK_LABELS.get(s.framework, s.framework),
                "department": s.department,
                "dimension": s.dimension,
                "current_score": s.current_score,
                "target_score": s.target_score,
                "gap": gap,
                "issue": s.issue,
                "owner": s.owner or "-",
                "severity": _severity(gap),
            }
        )
    scan_rows.sort(key=lambda x: x["gap"])

    bottlenecks = [r for r in scan_rows if r["gap"] <= -1.0]
    pain_points = [r for r in health_rows if r["level"] == "明显短板"]

    if not health_rows and not scan_rows:
        return {"error": "当前条件下没有组织诊断数据。", "total": 0}

    if health_score >= 4.2:
        health_level = "健康"
    elif health_score >= 3.6:
        health_level = "基本健康"
    elif health_score >= 3.0:
        health_level = "亚健康"
    else:
        health_level = "预警"

    return {
        "department": department or "全部部门",
        "period": period or (surveys[0].period if surveys else "-"),
        "framework": framework or "全部框架",
        "org_health_score": health_score,
        "org_health_level": health_level,
        "health_dimensions": health_rows,
        "pain_points": pain_points,
        "scan_total": len(scan_rows),
        "scan_results": scan_rows,
        "bottlenecks": bottlenecks,
        "basis": (
            "健康分 = 各维度调研均分的平均值；维度差距 = 实际分 − 行业基准；"
            "扫描差距 = 现状分 − 目标分，≤ −1.0 判定为瓶颈"
        ),
        "conclusion": (
            f"组织健康分 {health_score}（{health_level}）。"
            + (
                f"明显短板维度 {len(pain_points)} 项："
                f"{'、'.join(p['dimension'] for p in pain_points)}。"
                if pain_points
                else "各维度均不低于行业基准。"
            )
            + (
                f"组织扫描 {len(scan_rows)} 项，其中 {len(bottlenecks)} 项为瓶颈，"
                f"最需优先解决“{bottlenecks[0]['dimension']}”（{bottlenecks[0]['issue']}）。"
                if bottlenecks
                else "组织扫描未发现显著瓶颈。"
            )
        ),
    }


def _severity(gap: float) -> str:
    if gap <= -1.5:
        return "严重瓶颈"
    if gap <= -1.0:
        return "瓶颈"
    if gap < 0:
        return "有差距"
    return "达标"


def _health_advice(dimension: str, level: str) -> str:
    if level in ("优于基准", "基本达标"):
        return f"{dimension}表现良好，可沉淀做法横向复制"
    base = {
        "战略清晰": "战略未有效传递到一线，建议做一次战略解码与目标对齐",
        "组织架构": "架构与业务不匹配，建议复盘部门设置与汇报线",
        "流程效率": "流程节点冗余，建议梳理核心流程并压缩审批层级",
        "人才供给": "关键岗位供给不足，建议启动继任与梯队建设",
        "文化氛围": "组织氛围偏弱，建议加强管理者的团队建设动作",
        "激励机制": "激励与贡献不匹配，建议复盘绩效与薪酬联动机制",
        "协同效率": "跨部门协同成本高，建议明确接口职责与协同机制",
    }.get(dimension, "该维度低于基准，建议专项复盘")
    return f"{'明显短板：' if level == '明显短板' else ''}{base}"


# ---------------------------- 六、战略解码 ----------------------------


def strategy_decode(
    db: Session, department: str | None = None, period: str | None = None
) -> dict:
    """战略解码：公司战略 → 组织目标 → 部门目标的拆解与达成追踪。"""
    stmt = select(StrategicGoal)
    if period:
        stmt = stmt.where(StrategicGoal.period == period)
    if department:
        stmt = stmt.where(StrategicGoal.owner_department == department)
    goals = list(db.execute(stmt).scalars().all())

    if not goals:
        return {"error": "当前条件下没有战略解码数据。", "total": 0}

    by_level: dict[str, list[dict]] = {"公司": [], "组织": [], "部门": []}
    for g in goals:
        achievement = round(g.current_value / g.target_value, 3) if g.target_value else 0.0
        if achievement >= 1.0:
            status_flag = "已达成"
        elif achievement >= 0.8:
            status_flag = "进展良好"
        elif achievement >= 0.6:
            status_flag = "有风险"
        else:
            status_flag = "严重滞后"
        row = {
            "id": g.id,
            "level": g.level,
            "name": g.name,
            "owner_department": g.owner_department or "-",
            "metric": g.metric,
            "target_value": g.target_value,
            "current_value": g.current_value,
            "achievement": achievement,
            "weight": g.weight,
            "status": g.status,
            "flag": status_flag,
        }
        by_level.setdefault(g.level, []).append(row)

    for rows in by_level.values():
        rows.sort(key=lambda x: x["achievement"])

    all_rows = [r for rows in by_level.values() for r in rows]
    # 加权达成率：权重归一化后按达成率加权
    total_weight = sum(r["weight"] for r in all_rows) or 1.0
    weighted = round(
        sum(r["achievement"] * r["weight"] for r in all_rows) / total_weight, 3
    )

    # 承接检查：部门目标是否都有上级目标
    parent_ids = {g.id for g in goals}
    orphan = [
        r
        for r in all_rows
        if r["level"] == "部门"
        and not any(
            g.id == r["id"] and g.parent_id in parent_ids
            for g in goals
            if g.id == r["id"]
        )
    ]

    lagging = [r for r in all_rows if r["flag"] in ("有风险", "严重滞后")]

    return {
        "department": department or "全部部门",
        "period": period or (goals[0].period if goals else "-"),
        "total": len(all_rows),
        "company_goals": by_level.get("公司", []),
        "org_goals": by_level.get("组织", []),
        "department_goals": by_level.get("部门", []),
        "weighted_achievement": weighted,
        "lagging_goals": lagging,
        "unaligned_goals": orphan,
        "basis": (
            "目标达成率 = 当前值 / 目标值；加权达成率 = Σ(达成率 × 权重) / Σ权重；"
            "≥1.0 已达成，≥0.8 进展良好，≥0.6 有风险，否则严重滞后"
        ),
        "conclusion": (
            f"共 {len(all_rows)} 个目标（公司 {len(by_level.get('公司', []))} / "
            f"组织 {len(by_level.get('组织', []))} / 部门 {len(by_level.get('部门', []))}），"
            f"加权达成率 {round(weighted * 100, 1)}%。"
            + (
                f"其中 {len(lagging)} 个目标进展落后，最需关注的是"
                f"“{lagging[0]['name']}”（达成 {round(lagging[0]['achievement'] * 100, 1)}%）。"
                if lagging
                else "各层级目标进展正常。"
            )
        ),
    }


# ---------------------------- 七、文化与组织氛围 ----------------------------


def org_culture(
    db: Session, department: str | None = None, period: str | None = None
) -> dict:
    """企业文化与组织氛围：价值观落地、氛围感知与敬业度。"""
    stmt = select(CultureSurvey)
    if department:
        stmt = stmt.where(CultureSurvey.department == department)
    if period:
        stmt = stmt.where(CultureSurvey.period == period)
    records = list(db.execute(stmt).scalars().all())

    if not records:
        return {"error": "当前条件下没有文化与氛围调研数据。", "total": 0}

    by_dim: dict[str, list[CultureSurvey]] = {}
    for r in records:
        by_dim.setdefault(r.dimension, []).append(r)

    rows = []
    for dim, items in sorted(by_dim.items()):
        score = round(sum(i.score for i in items) / len(items), 2)
        if score >= 4.2:
            level = "氛围优良"
        elif score >= 3.6:
            level = "健康"
        elif score >= 3.0:
            level = "需关注"
        else:
            level = "预警"
        initiative = next((i.initiative for i in items if i.initiative), "")
        rows.append(
            {
                "dimension": dim,
                "score": score,
                "sample": sum(i.sample for i in items),
                "level": level,
                "initiative": initiative,
                "advice": _culture_advice(dim, level, initiative),
            }
        )
    rows.sort(key=lambda x: x["score"])

    overall = round(sum(r["score"] for r in rows) / len(rows), 2)
    weak = [r for r in rows if r["level"] in ("需关注", "预警")]

    return {
        "department": department or "全部部门",
        "period": period or (records[0].period if records else "-"),
        "total_dimensions": len(rows),
        "overall_score": overall,
        "engagement_score": next(
            (r["score"] for r in rows if r["dimension"] == "敬业度"), None
        ),
        "dimensions": rows,
        "weak_dimensions": weak,
        "basis": (
            "维度分 = 该维度调研均分（1-5）；≥4.2 优良，≥3.6 健康，"
            "≥3.0 需关注，否则预警"
        ),
        "conclusion": (
            f"文化与氛围整体得分 {overall}，"
            + (
                f"其中 {len(weak)} 个维度需关注："
                f"{'、'.join(r['dimension'] for r in weak)}，"
                f"建议优先推进对应文化举措。"
                if weak
                else "各维度均处于健康及以上水平。"
            )
        ),
    }


def _culture_advice(dimension: str, level: str, initiative: str) -> str:
    base = {
        "价值观认同": "价值观停留在口号，建议纳入管理者考核与晋升标准",
        "协作氛围": "部门墙较厚，建议设置跨部门共同目标与联合激励",
        "心理安全": "员工不敢表达异议，建议建立匿名反馈与无责复盘机制",
        "管理风格": "管理风格偏命令式，建议开展管理者辅导式领导力训练",
        "成长空间": "员工看不到成长路径，建议打通任职资格与发展通道",
        "敬业度": "敬业度偏低，建议先解决直接主管与激励认可问题",
    }.get(dimension, "该维度偏低，建议专项调研定位成因")
    if initiative:
        return f"{base}；已配举措：{initiative}"
    return base


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
                "stage": p.stage,
                "stage_index": STAGE_ORDER.get(p.stage, 0),
                "resistance": p.resistance,
                "resistance_source": p.resistance_source or "",
                "risk": risk,
                "target_date": str(p.target_date) if p.target_date else "-",
                "note": p.note or "",
                "advice": _change_advice(p.change_type, risk, affected),
                "resistance_advice": _resistance_advice(p.resistance, p.stage),
            }
        )

    rows.sort(key=lambda x: -x["affected_headcount"])

    total_affected = sum(r["affected_headcount"] for r in rows)
    total_cost = round(sum(r["cost_impact"] for r in rows), 2)
    pending = [r for r in rows if r["status"] != "已完成"]
    high = [r for r in rows if r["risk"] == "高影响"]
    blocked = [r for r in rows if r["resistance"] == "高" and r["status"] != "已完成"]

    return {
        "department": department or "全部部门",
        "total": len(rows),
        "total_affected": total_affected,
        "total_cost_impact": total_cost,
        "pending_count": len(pending),
        "high_impact_plans": high,
        "high_resistance_plans": blocked,
        "stage_distribution": _distribution(rows, "stage"),
        "plans": rows,
        "basis": (
            "影响分级：≥30 人高影响，≥10 人中影响；"
            "变革阶段：宣贯 → 试点 → 推广 → 固化；阻力等级高/中/低"
        ),
        "conclusion": (
            f"共 {len(rows)} 个组织变革方案，累计影响 {total_affected} 人，"
            f"成本影响 {total_cost} 万元。"
            + (
                f"其中 {len(high)} 个为高影响方案（影响 30 人及以上），"
                f"建议提前做沟通方案与人员安置预案。"
                if high
                else "暂无高影响方案，可按计划推进。"
            )
            + (
                f"另有 {len(blocked)} 个方案变革阻力为高，"
                f"需优先处理阻力来源再推进。"
                if blocked
                else ""
            )
        ),
    }


STAGE_ORDER = {"宣贯": 1, "试点": 2, "推广": 3, "固化": 4}


def _resistance_advice(resistance: str, stage: str) -> str:
    if resistance == "高":
        return f"阻力高且当前处于{stage}阶段，建议高管站台宣贯 + 关键人群一对一沟通"
    if resistance == "中":
        return "存在一定阻力，建议在试点阶段收集反馈并快速调整方案"
    return "阻力较低，按既定节奏推进即可"


def _change_advice(change_type: str, risk: str, affected: int) -> str:
    base = {
        "合并": "合并后需重新明确汇报线与岗位职责，避免职责重叠",
        "拆分": "拆分后需补齐管理岗位，防止管理幅度失衡",
        "扩编": "扩编需同步核对预算与办公资源，分批到位更稳妥",
        "缩编": "缩编需配套安置方案与合规流程，优先内部转岗",
        "新设": "新设单元需先明确定位与编制，再启动招聘",
        "调整": "调整方案需明确新旧职责切换时点与过渡安排",
        "并购": "并购需先完成组织架构映射与关键人才保留方案",
        "转型": "转型需配套能力重塑计划，避免只改架构不改能力",
    }.get(change_type, "变更前完成影响评估与沟通计划")
    if risk == "高影响":
        return f"{base}；影响 {affected} 人，建议高管牵头并设专项沟通窗口"
    return base


__all__ = [
    "job_architecture",
    "org_change_simulation",
    "org_culture",
    "org_diagnosis",
    "org_effectiveness",
    "org_structure",
    "strategy_decode",
]
