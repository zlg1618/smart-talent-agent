"""人才盘点：九宫格（绩效 × 潜力）。

这是本项目的核心确定性计算。九宫格定位、人才分类、管理动作建议
全部由 Python 依据数据库中的真实绩效与潜力数据计算得出，
大模型不参与任何打分与分类决策。
"""

from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.models import Employee
from app.services import employee_service

# 九宫格定义：(绩效档, 潜力档) -> 名称、人才类型、管理动作
NINE_BOX = {
    ("高", "高"): {
        "name": "超级明星",
        "talent_type": "明星人才",
        "action": "加速晋升，纳入关键岗位继任池，交付战略性挑战项目",
    },
    ("高", "中"): {
        "name": "中坚力量",
        "talent_type": "绩效之星",
        "action": "扩大职责范围，做专业纵深发展，重点激励与保留",
    },
    ("高", "低"): {
        "name": "业务骨干",
        "talent_type": "专业贡献者",
        "action": "走专家序列晋升，沉淀方法论并承担带教",
    },
    ("中", "高"): {
        "name": "潜力之星",
        "talent_type": "待激活人才",
        "action": "补齐关键经历，横向轮岗历练，指定高管导师",
    },
    ("中", "中"): {
        "name": "核心骨干",
        "talent_type": "稳定贡献者",
        "action": "聚焦一项能力突破，绩效目标适度上浮",
    },
    ("中", "低"): {
        "name": "稳定贡献者",
        "talent_type": "稳定贡献者",
        "action": "维持现状，明确岗位要求，管理晋升预期",
    },
    ("低", "高"): {
        "name": "待激活错配",
        "talent_type": "错配人才",
        "action": "诊断错配原因（岗位 / 主管 / 动机），尝试调岗重新激发",
    },
    ("低", "中"): {
        "name": "待改进",
        "talent_type": "待改进人才",
        "action": "启动绩效改进计划（PIP），明确短板与改进期限",
    },
    ("低", "低"): {
        "name": "待优化",
        "talent_type": "低效人才",
        "action": "转岗或依法依规淘汰，做好合规与人员补充安排",
    },
}

PERF_ORDER = ["低", "中", "高"]
POT_ORDER = ["低", "中", "高"]


def score_band(score: float | None) -> str:
    """把分数换算成低 / 中 / 高三档。"""
    settings = get_settings()
    if score is None:
        return "低"
    if score >= settings.talent_score_high:
        return "高"
    if score >= settings.talent_score_low:
        return "中"
    return "低"


def locate_grid(performance: float | None, potential: float | None) -> dict:
    """根据绩效与潜力定位格子。"""
    perf_band = score_band(performance)
    pot_band = score_band(potential)
    meta = NINE_BOX[(perf_band, pot_band)]
    return {
        "perf_band": perf_band,
        "pot_band": pot_band,
        "grid_key": f"{perf_band}-{pot_band}",
        "grid_name": meta["name"],
        "talent_type": meta["talent_type"],
        "action": meta["action"],
    }


def build_talent_review(
    db: Session,
    department: str | None = None,
    period: str | None = None,
    job_level: str | None = None,
    only_grid: list[str] | None = None,
) -> dict:
    """生成人才盘点九宫格结果。

    Args:
        department: 部门过滤，为空表示全公司
        period: 考核周期，为空取最新周期
        job_level: 职级过滤
        only_grid: 只保留指定格子，如 ["高-高", "中-高"]
    """
    if period is None:
        period = employee_service.get_latest_period(db)

    employees = employee_service.list_employees(
        db, department=department, job_level=job_level
    )

    items = []
    for emp in employees:
        perf = employee_service.get_performance(db, emp.id, period)
        pot = employee_service.get_potential(db, emp.id, period)

        perf_score = perf.score if perf else None
        pot_score = pot.potential_score if pot else None

        # 数据缺失的员工不参与盘点，避免错误归类
        if perf_score is None or pot_score is None:
            continue

        grid = locate_grid(perf_score, pot_score)
        if only_grid and grid["grid_key"] not in only_grid:
            continue

        items.append(
            {
                "employee_id": emp.id,
                "name": emp.name,
                "department": emp.department,
                "position_title": emp.position_title,
                "job_level": emp.job_level,
                "performance": round(perf_score, 2),
                "grade": perf.grade if perf else None,
                "potential": round(pot_score, 2),
                "mobility": bool(pot.mobility) if pot else False,
                **grid,
            }
        )

    items.sort(key=lambda x: (-(x["performance"] + x["potential"]), x["name"]))

    # 按格子汇总
    summary = []
    for pot_band in reversed(POT_ORDER):
        row = []
        for perf_band in PERF_ORDER:
            meta = NINE_BOX[(perf_band, pot_band)]
            matched = [
                i for i in items if i["perf_band"] == perf_band and i["pot_band"] == pot_band
            ]
            row.append(
                {
                    "grid_key": f"{perf_band}-{pot_band}",
                    "grid_name": meta["name"],
                    "talent_type": meta["talent_type"],
                    "action": meta["action"],
                    "count": len(matched),
                    "ratio": round(len(matched) / len(items), 4) if items else 0.0,
                    "members": [m["name"] for m in matched[:10]],
                }
            )
        summary.append(row)

    high_potential = [i for i in items if i["pot_band"] == "高"]
    star = [i for i in items if i["grid_key"] == "高-高"]
    risk = [i for i in items if i["grid_key"] in ("低-低", "低-中")]

    return {
        "period": period,
        "department": department or "全部部门",
        "job_level": job_level or "全部职级",
        "total": len(items),
        "employees": items,
        "grid_matrix": summary,
        "star_talent": [i["name"] for i in star],
        "high_potential": [i["name"] for i in high_potential],
        "risk_talent": [i["name"] for i in risk],
        "high_potential_ratio": round(len(high_potential) / len(items), 4) if items else 0.0,
    }


def locate_employee(db: Session, name: str, period: str | None = None) -> dict | None:
    """定位单个员工的九宫格位置与发展建议。"""
    emp = employee_service.get_employee_by_name(db, name)
    if not emp:
        return None

    if period is None:
        period = employee_service.get_latest_period(db)

    perf = employee_service.get_performance(db, emp.id, period)
    pot = employee_service.get_potential(db, emp.id, period)

    if not perf or not pot:
        return {
            "employee_id": emp.id,
            "name": emp.name,
            "department": emp.department,
            "position_title": emp.position_title,
            "job_level": emp.job_level,
            "period": period,
            "performance": perf.score if perf else None,
            "potential": pot.potential_score if pot else None,
            "error": "该员工缺少完整评价数据，无法定位九宫格",
        }

    grid = locate_grid(perf.score, pot.potential_score)
    return {
        "employee_id": emp.id,
        "name": emp.name,
        "department": emp.department,
        "position_title": emp.position_title,
        "job_level": emp.job_level,
        "period": period,
        "performance": round(perf.score, 2),
        "grade": perf.grade,
        "potential": round(pot.potential_score, 2),
        "mobility": bool(pot.mobility),
        **grid,
    }
