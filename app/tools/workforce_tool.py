"""HRIS · 人力资源规划域 Tool：编制审查、供需预测、离职风险、继任联动。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Employee
from app.services import workforce_service

SCENARIO_KEYWORDS = {
    "conservative": ["保守"],
    "aggressive": ["激进", "乐观"],
    "baseline": ["基准", "中性"],
}


def _find_department(db: Session, message: str) -> str | None:
    departments = [
        d[0] for d in db.execute(select(Employee.department).distinct()).all() if d[0]
    ]
    departments.sort(key=len, reverse=True)
    for dep in departments:
        if dep in message:
            return dep
    return None


def run_headcount_review(
    db: Session, message: str, department: str | None = None, period: str | None = None
) -> dict:
    return workforce_service.headcount_review(
        db, department=department or _find_department(db, message), period=period
    )


def run_supply_demand_forecast(
    db: Session, message: str, department: str | None = None
) -> dict:
    scenario = "baseline"
    for key, words in SCENARIO_KEYWORDS.items():
        if any(w in message for w in words):
            scenario = key
            break
    return workforce_service.supply_demand_forecast(
        db, department=department or _find_department(db, message), scenario=scenario
    )


def run_attrition_risk(
    db: Session, message: str, department: str | None = None
) -> dict:
    only_high = any(k in message for k in ("高风险", "高危", "重点人"))
    return workforce_service.attrition_risk_scan(
        db,
        department=department or _find_department(db, message),
        only_high=only_high,
    )


__all__ = [
    "run_attrition_risk",
    "run_headcount_review",
    "run_supply_demand_forecast",
]
