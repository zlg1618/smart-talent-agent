"""继任地图与人才梯队建设。

继任覆盖率、继任深度、梯队厚度比等指标全部由 Python 计算，
数据库中有多少继任关系就返回多少，不为凑数虚构候选人。
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Employee, KeyPosition, SuccessionPlan
from app.services import employee_service

READINESS_LABEL = {
    "ready_now": "立即就绪",
    "ready_1y": "1 年内就绪",
    "ready_2y": "2 年内就绪",
    "not_ready": "尚未就绪",
}

READINESS_RANK = {"ready_now": 0, "ready_1y": 1, "ready_2y": 2, "not_ready": 3}

LEVEL_RANK = {
    "P4": 1,
    "P5": 2,
    "P6": 3,
    "P7": 4,
    "P8": 5,
    "M1": 3,
    "M2": 4,
    "M3": 5,
}


def level_rank(level: str) -> int:
    return LEVEL_RANK.get(level, 0)


def track_of(level: str) -> str:
    """职级所属发展通道：专业通道（P）或管理通道（M）。"""
    return "管理通道" if str(level).upper().startswith("M") else "专业通道"


def _calc_pipeline(distribution: list[dict]) -> list[dict]:
    """计算同一通道内相邻职级的梯队供给比。"""
    pipeline = []
    for i in range(len(distribution) - 1):
        lower = distribution[i]
        upper = distribution[i + 1]
        demand = upper["count"]
        supply = lower["count"]
        ratio = round(supply / demand, 2) if demand else 0.0

        if ratio >= 1.5:
            health = "储备充足"
        elif ratio >= 1.0:
            health = "储备偏薄"
        else:
            health = "梯队断层"

        pipeline.append(
            {
                "from_level": lower["job_level"],
                "to_level": upper["job_level"],
                "supply": supply,
                "demand": demand,
                "supply_ratio": ratio,
                "health": health,
            }
        )
    return pipeline


def build_succession_map(
    db: Session,
    department: str | None = None,
    criticality: str | None = None,
    exclude_readiness: list[str] | None = None,
) -> dict:
    """生成关键岗位继任地图。"""
    stmt = select(KeyPosition)
    if department:
        stmt = stmt.where(KeyPosition.department == department)
    if criticality:
        stmt = stmt.where(KeyPosition.criticality == criticality)
    positions = list(db.execute(stmt.order_by(KeyPosition.id)).scalars().all())

    positions_out = []
    with_successor = 0
    ready_now_count = 0
    total_successors = 0
    risk_positions = []

    for pos in positions:
        plans = sorted(
            pos.successors, key=lambda p: READINESS_RANK.get(p.readiness, 9)
        )
        successors = []
        for plan in plans:
            if exclude_readiness and plan.readiness in exclude_readiness:
                continue
            emp = db.get(Employee, plan.successor_id)
            if not emp:
                continue
            successors.append(
                {
                    "successor_id": emp.id,
                    "name": emp.name,
                    "department": emp.department,
                    "job_level": emp.job_level,
                    "readiness": plan.readiness,
                    "readiness_label": READINESS_LABEL.get(plan.readiness, plan.readiness),
                    "note": plan.note,
                }
            )

        incumbent = db.get(Employee, pos.incumbent_id) if pos.incumbent_id else None

        has_ready_now = any(s["readiness"] == "ready_now" for s in successors)
        if successors:
            with_successor += 1
        if has_ready_now:
            ready_now_count += 1
        total_successors += len(successors)

        if not successors:
            risk_level = "高风险"
            risk_reason = "无任何继任候选人"
        elif not has_ready_now:
            risk_level = "中风险"
            risk_reason = "无立即就绪候选人，最短准备周期偏长"
        elif len(successors) == 1:
            risk_level = "中风险"
            risk_reason = "仅单一候选人，缺乏备份"
        else:
            risk_level = "低风险"
            risk_reason = "继任梯队完整"

        item = {
            "key_position_id": pos.id,
            "title": pos.title,
            "department": pos.department,
            "job_level": pos.job_level,
            "criticality": pos.criticality,
            "incumbent": incumbent.name if incumbent else None,
            "successors": successors,
            "successor_count": len(successors),
            "has_ready_now": has_ready_now,
            "risk_level": risk_level,
            "risk_reason": risk_reason,
        }
        positions_out.append(item)
        if risk_level == "高风险" or (
            risk_level == "中风险" and pos.criticality == "高"
        ):
            risk_positions.append(item)

    total = len(positions_out)
    return {
        "department": department or "全部部门",
        "total_key_positions": total,
        "positions": positions_out,
        "coverage": {
            "total": total,
            "with_successor": with_successor,
            "ready_now": ready_now_count,
            "coverage_rate": round(with_successor / total, 4) if total else 0.0,
            "ready_now_rate": round(ready_now_count / total, 4) if total else 0.0,
            "avg_depth": round(total_successors / total, 2) if total else 0.0,
        },
        "risk_positions": risk_positions,
    }


def build_talent_pipeline(db: Session, department: str | None = None) -> dict:
    """人才梯队分析：职级分布与梯队厚度比。

    供给比 = 下一层级人数 / 上一层级人数。
    供给比越高，说明晋升储备越充足。
    """
    stmt = select(Employee.job_level, func.count(Employee.id)).where(
        Employee.status == "在职"
    )
    if department:
        stmt = stmt.where(Employee.department == department)
    stmt = stmt.group_by(Employee.job_level)

    rows = db.execute(stmt).all()
    all_levels = [{"job_level": lv, "count": cnt} for lv, cnt in rows]
    distribution = sorted(all_levels, key=lambda x: (track_of(x["job_level"]), level_rank(x["job_level"])))

    # 专业通道与管理通道分别计算，避免跨通道比较
    tracks = []
    pipeline = []
    for track_name in ("专业通道", "管理通道"):
        track_levels = sorted(
            [d for d in all_levels if track_of(d["job_level"]) == track_name],
            key=lambda x: level_rank(x["job_level"]),
        )
        if len(track_levels) < 2:
            continue
        track_pipeline = _calc_pipeline(track_levels)
        for item in track_pipeline:
            item["track"] = track_name
        tracks.append(
            {
                "track": track_name,
                "level_distribution": track_levels,
                "pipeline": track_pipeline,
            }
        )
        pipeline.extend(track_pipeline)

    succession = build_succession_map(db, department=department)
    broken = [p for p in pipeline if p["health"] == "梯队断层"]

    return {
        "department": department or "全部部门",
        "level_distribution": distribution,
        "tracks": tracks,
        "pipeline": pipeline,
        "key_position_coverage": succession["coverage"],
        "broken_levels": [f"{p['to_level']}({p['track']})" for p in broken],
        "risk_positions": succession["risk_positions"],
        "conclusion": _pipeline_conclusion(pipeline, succession["coverage"]),
    }


def _pipeline_conclusion(pipeline: list[dict], coverage: dict) -> list[str]:
    conclusions = []
    for p in pipeline:
        track = p.get("track", "")
        if p["health"] == "梯队断层":
            conclusions.append(
                f"{track} {p['from_level']} 到 {p['to_level']} 存在梯队断层，"
                f"储备 {p['supply']} 人对应 {p['demand']} 个上级岗位，需外部引进或加速培养"
            )
        elif p["health"] == "储备偏薄":
            conclusions.append(
                f"{track} {p['from_level']} 到 {p['to_level']} 储备偏薄，建议提前启动继任培养"
            )

    rate = coverage.get("ready_now_rate", 0)
    if rate < 0.5:
        conclusions.append(
            f"关键岗位立即就绪覆盖率仅 {round(rate * 100, 1)}%，低于 50%，继任风险偏高"
        )
    if not conclusions:
        conclusions.append("梯队结构与继任覆盖整体健康，保持现有盘点节奏即可")
    return conclusions
