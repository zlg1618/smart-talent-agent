"""HRIS · 薪酬与福利域（Compensation & Benefits）确定性计算。

核心指标：
    compa-ratio        个人固定薪 / 带宽中位值，衡量薪酬内部公平性
    range penetration  带宽渗透率 =（个人薪 - 带宽下限）/（上限 - 下限）
    red / green circle 高于上限为红圈（超薪），低于下限为绿圈（欠薪）
    TCC                总现金薪酬 = 固定薪 + 目标奖金 + 长期激励
    TDC                总直接薪酬 = TCC + 年化福利成本

所有数字由 Python 计算，大模型只负责解释结论。
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    BenefitPlan,
    DepartmentMetric,
    Employee,
    EmployeeBenefit,
    EmployeeCompensation,
    SalaryBand,
)

# compa-ratio 健康区间
COMPA_HEALTHY = (0.90, 1.10)

RISK_RULE = [
    (1.20, "显著超薪", "冻结调薪，改用一次性奖金认可"),
    (1.10, "轻微超薪", "暂缓调薪，优先给浮动激励"),
    (0.90, "低于带宽下限", "优先纳入调薪池，分两次补齐到中位值"),
    (0.00, "严重低于市场对标", "立即启动薪酬追平，否则离职风险高"),
]


def _latest_compensation(db: Session, employee_id: int) -> EmployeeCompensation | None:
    return db.execute(
        select(EmployeeCompensation)
        .where(EmployeeCompensation.employee_id == employee_id)
        .order_by(EmployeeCompensation.effective_date.desc())
    ).scalars().first()


def _default_band(city: str = "-") -> tuple[int, int, int]:
    """兜底带宽，避免数据缺失导致除零。"""
    return (240000, 300000, 400000)


def compa_ratio_analysis(
    db: Session, department: str | None = None, job_level: str | None = None
) -> dict:
    """部门 / 职级维度的 compa-ratio 分布与外部竞争力分析。"""
    stmt = select(Employee).where(Employee.status == "在职")
    if department:
        stmt = stmt.where(Employee.department == department)
    if job_level:
        stmt = stmt.where(Employee.job_level == job_level)
    employees = list(db.execute(stmt).scalars().all())
    if not employees:
        return {"error": "当前条件下没有在职员工"}

    bands = {
        (b.job_level, b.city): (b.minimum, b.median, b.maximum)
        for b in db.execute(select(SalaryBand)).scalars().all()
    }

    details = []
    for emp in employees:
        comp = _latest_compensation(db, emp.id)
        if not comp:
            details.append(
                {
                    "id": emp.id,
                    "name": emp.name,
                    "department": emp.department,
                    "job_level": emp.job_level,
                    "base_salary": 0,
                    "band": None,
                    "compa_ratio": 0.0,
                    "penetration": 0.0,
                    "status": "未定薪",
                    "issue": "缺少薪酬记录",
                    "suggestion": "补录薪酬数据后再参与公平性分析",
                }
            )
            continue

        key = (emp.job_level, emp.city)
        minimum, median, maximum = bands.get(key, _default_band())
        base = comp.base_salary
        ratio = round(base / median, 3) if median else 0.0
        spread = maximum - minimum
        penetration = round((base - minimum) / spread, 3) if spread else 0.0

        if base > maximum:
            status = "红圈（超薪）"
        elif base < minimum:
            status = "绿圈（欠薪）"
        elif COMPA_HEALTHY[0] <= ratio <= COMPA_HEALTHY[1]:
            status = "健康"
        else:
            status = "需关注"

        issue = ""
        suggestion = ""
        if status in ("红圈（超薪）", "绿圈（欠薪）") or status == "需关注":
            for threshold, text, advice in RISK_RULE:
                if ratio >= threshold or (threshold == 0.0 and ratio < 0.90):
                    if ratio >= 1.10 or ratio < 0.90:
                        issue = f"compa-ratio {ratio}，" + text
                        suggestion = advice
                    break

        details.append(
            {
                "id": emp.id,
                "name": emp.name,
                "department": emp.department,
                "job_level": emp.job_level,
                "base_salary": base,
                "band": {"min": minimum, "median": median, "max": maximum},
                "compa_ratio": ratio,
                "penetration": penetration,
                "status": status,
                "issue": issue,
                "suggestion": suggestion,
            }
        )

    scored = [d for d in details if d["compa_ratio"] > 0]
    n = len(scored)
    avg_ratio = round(sum(d["compa_ratio"] for d in scored) / n, 3) if n else 0.0
    below = [d for d in scored if d["compa_ratio"] < COMPA_HEALTHY[0]]
    above = [d for d in scored if d["compa_ratio"] > COMPA_HEALTHY[1]]

    return {
        "department": department or "全部部门",
        "job_level": job_level or "全部职级",
        "employee_count": len(details),
        "avg_compa_ratio": avg_ratio,
        "below_band_count": len(below),
        "above_band_count": len(above),
        "healthy_ratio_label": f"{COMPA_HEALTHY[0]} ~ {COMPA_HEALTHY[1]}",
        "below_band": sorted(below, key=lambda x: x["compa_ratio"])[:10],
        "above_band": sorted(above, key=lambda x: -x["compa_ratio"])[:10],
        "distribution": details,
        "conclusion": _ratio_conclusion(avg_ratio, below, above, n),
    }


def _ratio_conclusion(avg: float, below: list, above: list, n: int) -> str:
    if n == 0:
        return "暂无有效薪酬数据，无法做公平性分析。"
    parts = [f"共 {n} 人参与比对，平均 compa-ratio {avg}。"]
    if below:
        share = round(len(below) / n * 100, 1)
        parts.append(
            f"{len(below)} 人低于健康下限（占 {share}%），"
            f"其中最低为 {below[-1]['compa_ratio']}，建议优先纳入调薪池。"
        )
    if above:
        parts.append(
            f"{len(above)} 人高于健康上限，建议改用浮动激励替代固定调薪。"
        )
    if not below and not above:
        parts.append("全员落在健康区间内，内部公平性良好。")
    return "".join(parts)


def salary_adjustment_simulation(
    db: Session, department: str | None = None, budget_pct: float = 5.0
) -> dict:
    """调薪预算模拟：优先补给低于带宽下限的人，测算预算是否够用。"""
    analysis = compa_ratio_analysis(db, department=department)
    if analysis.get("error"):
        return analysis

    distribution = [d for d in analysis["distribution"] if d["compa_ratio"] > 0]
    total_base = sum(d["base_salary"] for d in distribution)
    budget = int(total_base * budget_pct / 100)

    below = sorted(
        [d for d in distribution if d["compa_ratio"] < COMPA_HEALTHY[0]],
        key=lambda x: x["compa_ratio"],
    )

    plan, used, remain = [], 0, budget
    for d in below:
        target = int(d["band"]["median"] * COMPA_HEALTHY[0])
        need = max(0, target - d["base_salary"])
        if need <= 0:
            continue
        grant = min(need, remain)
        if grant <= 0:
            break
        plan.append(
            {
                "id": d["id"],
                "name": d["name"],
                "department": d["department"],
                "job_level": d["job_level"],
                "current_base": d["base_salary"],
                "grant": grant,
                "raise_pct": round(grant / d["base_salary"] * 100, 1)
                if d["base_salary"]
                else 0.0,
                "new_compa_ratio": round(
                    (d["base_salary"] + grant) / d["band"]["median"], 3
                ),
            }
        )
        used += grant
        remain -= grant

    return {
        "department": department or "全部部门",
        "budget_pct": budget_pct,
        "total_base": total_base,
        "budget_amount": budget,
        "used_amount": used,
        "remain_amount": remain,
        "adjusted_count": len(plan),
        "unaddressed_count": max(0, len(below) - len(plan)),
        "plan": plan,
        "conclusion": (
            f"预算合计 ¥{budget:,}（调薪池 {budget_pct}%），"
            f"可为 {len(plan)} 人补齐至健康下限，支出 ¥{used:,}，剩余 ¥{remain:,}。"
            + (
                f"仍有 {max(0, len(below) - len(plan))} 人未覆盖，建议下一周期继续。"
                if len(below) > len(plan)
                else "低于下限人员已全部覆盖。"
            )
        ),
    }


def benefits_analysis(db: Session, department: str | None = None) -> dict:
    """福利参保覆盖与人均成本分析。"""
    stmt = select(Employee).where(Employee.status == "在职")
    if department:
        stmt = stmt.where(Employee.department == department)
    employees = list(db.execute(stmt).scalars().all())
    plans = list(db.execute(select(BenefitPlan)).scalars().all())
    enrollments = list(db.execute(select(EmployeeBenefit)).scalars().all())

    emp_ids = {e.id for e in employees}
    active_enroll = [
        x for x in enrollments if x.employee_id in emp_ids and x.status == "active"
    ]

    rows = []
    for p in plans:
        enrolled_ids = {x.employee_id for x in active_enroll if x.plan_id == p.id}
        covered = len(enrolled_ids)
        rate = round(covered / len(employees), 3) if employees else 0.0
        rows.append(
            {
                "plan_id": p.id,
                "plan_name": p.name,
                "category": p.category,
                "is_core": p.is_core,
                "annual_cost": p.annual_cost,
                "enrolled": covered,
                "coverage_rate": rate,
                "total_cost": p.annual_cost * covered,
                "gap": "覆盖不足" if p.is_core and rate < 0.95 else ("可选福利" if not p.is_core else "达标"),
            }
        )

    rows.sort(key=lambda x: (-int(x["is_core"]), x["coverage_rate"]))
    core_rows = [r for r in rows if r["is_core"]]
    total_cost = sum(r["total_cost"] for r in rows)
    avg_cost = round(total_cost / len(employees), 0) if employees else 0
    under = [r for r in core_rows if r["coverage_rate"] < 0.95]

    return {
        "department": department or "全部部门",
        "employee_count": len(employees),
        "plan_count": len(plans),
        "total_benefit_cost": total_cost,
        "avg_cost_per_head": int(avg_cost),
        "core_plan_count": len(core_rows),
        "under_covered_count": len(under),
        "plans": rows,
        "conclusion": (
            f"共 {len(plans)} 项福利（其中核心 {len(core_rows)} 项），"
            f"人均年成本约 ¥{int(avg_cost):,}。"
            + (
                f"有 {len(under)} 项核心福利覆盖不足 95%，需排查参保流程。"
                if under
                else "核心福利覆盖均已达标。"
            )
        ),
    }


def compensation_summary(db: Session, employee_name: str) -> dict:
    """单人薪酬总览：TCC / TDC / 带宽位置 / 福利清单。"""
    emp = db.execute(
        select(Employee).where(Employee.name == employee_name)
    ).scalars().first()
    if not emp:
        return {"error": f"未找到员工：{employee_name}"}

    comp = _latest_compensation(db, emp.id)
    if not comp:
        return {"error": f"员工 {employee_name} 暂无薪酬记录"}

    band = db.execute(
        select(SalaryBand).where(SalaryBand.job_level == emp.job_level)
    ).scalars().first()
    minimum, median, maximum = (
        (band.minimum, band.median, band.maximum) if band else _default_band()
    )

    bonus = int(comp.base_salary * comp.target_bonus_pct / 100)
    tcc = comp.base_salary + bonus + comp.equity_value

    benefits_list = list(
        db.execute(
            select(EmployeeBenefit, BenefitPlan)
            .join(BenefitPlan, BenefitPlan.id == EmployeeBenefit.plan_id)
            .where(
                EmployeeBenefit.employee_id == emp.id,
                EmployeeBenefit.status == "active",
            )
        ).all()
    )
    benefit_cost = sum(p.annual_cost for _, p in benefits_list)
    tdc = tcc + benefit_cost

    ratio = round(comp.base_salary / median, 3) if median else 0.0
    spread = maximum - minimum
    penetration = round((comp.base_salary - minimum) / spread, 3) if spread else 0.0

    return {
        "employee": {
            "id": emp.id,
            "name": emp.name,
            "department": emp.department,
            "position_title": emp.position_title,
            "job_level": emp.job_level,
        },
        "effective_date": comp.effective_date.isoformat(),
        "base_salary": comp.base_salary,
        "target_bonus_pct": comp.target_bonus_pct,
        "target_bonus": bonus,
        "equity_value": comp.equity_value,
        "tcc": tcc,
        "benefit_cost": benefit_cost,
        "tdc": tdc,
        "band": {"min": minimum, "median": median, "max": maximum},
        "compa_ratio": ratio,
        "penetration": penetration,
        "last_adjust_pct": comp.last_adjust_pct,
        "last_adjust_date": comp.last_adjust_date.isoformat() if comp.last_adjust_date else None,
        "benefits": [
            {"name": p.name, "category": p.category, "cost": p.annual_cost}
            for _, p in benefits_list
        ],
        "conclusion": (
            f"{emp.name} 总现金薪酬 ¥{tcc:,}（base ¥{comp.base_salary:,} + "
            f"目标奖金 ¥{bonus:,} + 长期激励 ¥{comp.equity_value:,}），"
            f"含福利后总直接薪酬 ¥{tdc:,}；compa-ratio {ratio}，"
            f"在带宽中位于 {round(penetration * 100)}% 位置。"
        ),
    }


__all__ = [
    "benefits_analysis",
    "compa_ratio_analysis",
    "compensation_summary",
    "salary_adjustment_simulation",
]
