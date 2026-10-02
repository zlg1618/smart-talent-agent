"""组织诊断。

基于数据库中的部门级指标，按固定规则计算健康分并输出问题清单。
健康分与问题判定完全由 Python 完成，属于可审计的确定性逻辑。
"""

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.models import DepartmentMetric
from app.services import employee_service, succession_service

LEVEL_HEALTHY = "健康"
LEVEL_WATCH = "关注"
LEVEL_ALERT = "预警"


def _health_level(score: float) -> str:
    if score >= 85:
        return LEVEL_HEALTHY
    if score >= 70:
        return LEVEL_WATCH
    return LEVEL_ALERT


def diagnose_department(metric: DepartmentMetric, ready_now_rate: float | None) -> dict:
    """单个部门的诊断：扣分制，满分 100。"""
    settings = get_settings()
    issues = []
    score = 100.0

    if metric.turnover_rate >= settings.diagnosis_turnover_danger:
        score -= 25
        issues.append(
            {
                "name": "离职率过高",
                "level": LEVEL_ALERT,
                "detail": f"离职率 {round(metric.turnover_rate * 100, 1)}%，"
                f"超过 {round(settings.diagnosis_turnover_danger * 100)}% 警戒线",
                "suggestion": "开展离职访谈，定位管理、薪酬或发展通道问题",
            }
        )
    elif metric.turnover_rate >= settings.diagnosis_turnover_warning:
        score -= 12
        issues.append(
            {
                "name": "离职率偏高",
                "level": LEVEL_WATCH,
                "detail": f"离职率 {round(metric.turnover_rate * 100, 1)}%，"
                f"超过 {round(settings.diagnosis_turnover_warning * 100)}% 预警线",
                "suggestion": "关注核心人群流失，排查高绩效员工稳定性",
            }
        )

    if metric.avg_performance < 3.0:
        score -= 15
        issues.append(
            {
                "name": "整体绩效偏低",
                "level": LEVEL_ALERT,
                "detail": f"平均绩效 {round(metric.avg_performance, 2)}，低于 3.0",
                "suggestion": "复盘目标设定合理性与人员能力匹配度",
            }
        )
    elif metric.avg_performance < 3.3:
        score -= 8
        issues.append(
            {
                "name": "绩效表现偏弱",
                "level": LEVEL_WATCH,
                "detail": f"平均绩效 {round(metric.avg_performance, 2)}，低于 3.3",
                "suggestion": "加强过程辅导与绩效反馈频率",
            }
        )

    if metric.high_potential_ratio < settings.diagnosis_hp_ratio_warning:
        score -= 15
        issues.append(
            {
                "name": "高潜人才断层",
                "level": LEVEL_ALERT,
                "detail": f"高潜占比 {round(metric.high_potential_ratio * 100, 1)}%，"
                f"低于 {round(settings.diagnosis_hp_ratio_warning * 100)}%",
                "suggestion": "启动高潜识别与外部引进，重建人才蓄水池",
            }
        )
    elif metric.high_potential_ratio < 0.15:
        score -= 8
        issues.append(
            {
                "name": "高潜储备不足",
                "level": LEVEL_WATCH,
                "detail": f"高潜占比 {round(metric.high_potential_ratio * 100, 1)}%，低于 15%",
                "suggestion": "扩大盘点范围，增加潜力评估维度",
            }
        )

    if metric.span_of_control > settings.diagnosis_span_wide:
        score -= 10
        issues.append(
            {
                "name": "管理幅度过宽",
                "level": LEVEL_WATCH,
                "detail": f"平均管理幅度 {round(metric.span_of_control, 1)} 人，超过 "
                f"{round(settings.diagnosis_span_wide)} 人",
                "suggestion": "增设基层管理者或拆分团队",
            }
        )
    elif metric.span_of_control < settings.diagnosis_span_narrow:
        score -= 8
        issues.append(
            {
                "name": "管理幅度过窄",
                "level": LEVEL_WATCH,
                "detail": f"平均管理幅度 {round(metric.span_of_control, 1)} 人，低于 "
                f"{round(settings.diagnosis_span_narrow)} 人",
                "suggestion": "合并小团队，减少管理层级",
            }
        )

    if metric.avg_tenure < settings.diagnosis_tenure_short:
        score -= 10
        issues.append(
            {
                "name": "团队稳定性弱",
                "level": LEVEL_WATCH,
                "detail": f"平均司龄 {round(metric.avg_tenure, 1)} 年，低于 "
                f"{settings.diagnosis_tenure_short} 年",
                "suggestion": "加强新人融入与导师机制",
            }
        )

    if metric.headcount_change <= -5:
        score -= 5
        issues.append(
            {
                "name": "人员净流出",
                "level": LEVEL_WATCH,
                "detail": f"本期人数净变化 {metric.headcount_change} 人",
                "suggestion": "复核编制与招聘补齐节奏",
            }
        )

    if ready_now_rate is not None and ready_now_rate < 0.5:
        score -= 10
        issues.append(
            {
                "name": "继任准备不足",
                "level": LEVEL_ALERT,
                "detail": f"关键岗位立即就绪覆盖率 {round(ready_now_rate * 100, 1)}%，低于 50%",
                "suggestion": "为关键岗位指定接班人并设定培养里程碑",
            }
        )

    score = max(0.0, round(score, 1))
    return {
        "department": metric.department,
        "headcount": metric.headcount,
        "metrics": {
            "avg_tenure": round(metric.avg_tenure, 2),
            "turnover_rate": round(metric.turnover_rate, 4),
            "avg_performance": round(metric.avg_performance, 2),
            "high_potential_ratio": round(metric.high_potential_ratio, 4),
            "span_of_control": round(metric.span_of_control, 2),
            "headcount_change": metric.headcount_change,
        },
        "health_score": score,
        "health_level": _health_level(score),
        "issues": issues,
    }


def build_org_diagnosis(
    db: Session, department: str | None = None, period: str | None = None
) -> dict:
    """组织诊断，可指定部门或全公司。"""
    if period is None:
        period = employee_service.get_latest_period(db)

    stmt = select(DepartmentMetric)
    if department:
        stmt = stmt.where(DepartmentMetric.department == department)
    if period:
        stmt = stmt.where(DepartmentMetric.period == period)
    stmt = stmt.order_by(desc(DepartmentMetric.id))
    metrics = list(db.execute(stmt).scalars().all())

    if not metrics:
        return {
            "period": period,
            "department": department or "全部部门",
            "departments": [],
            "error": "该周期暂无组织诊断数据",
        }

    # 各部门关键岗位继任就绪率
    succession_all = succession_service.build_succession_map(db)
    ready_now_by_dept: dict[str, float] = {}
    for pos in succession_all["positions"]:
        dept = pos["department"]
        if dept not in ready_now_by_dept:
            ready_now_by_dept[dept] = []
        ready_now_by_dept[dept].append(1 if pos["has_ready_now"] else 0)
    ready_now_rate = {
        d: sum(v) / len(v) for d, v in ready_now_by_dept.items() if v
    }

    departments = [
        diagnose_department(m, ready_now_rate.get(m.department)) for m in metrics
    ]
    departments.sort(key=lambda x: x["health_score"])

    scores = [d["health_score"] for d in departments]
    org_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    all_issues = [i for d in departments for i in d["issues"]]
    alert_issues = [i for i in all_issues if i["level"] == LEVEL_ALERT]

    return {
        "period": period,
        "department": department or "全部部门",
        "department_count": len(departments),
        "org_health_score": org_score,
        "org_health_level": _health_level(org_score),
        "departments": departments,
        "alert_issue_count": len(alert_issues),
        "top_issues": alert_issues[:5],
        "worst_department": departments[0]["department"] if departments else None,
    }
