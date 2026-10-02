from app.services import (
    compensation_service,
    diagnosis_service,
    employee_relations_service,
    employee_service,
    idp_service,
    learning_service,
    performance_service,
    recruitment_service,
    succession_service,
    talent_review_service,
    workforce_service,
)

# HRIS 六大模块 → 计算服务映射
HRIS_SERVICE_MAP: dict[str, object] = {
    "recruitment": recruitment_service,
    "compensation": compensation_service,
    "performance": performance_service,
    "employee_relations": employee_relations_service,
    "learning": learning_service,
    "workforce": workforce_service,
}

# HRIS 六大模块展示名
HRIS_MODULE_LABELS: dict[str, str] = {
    "recruitment": "招聘管理",
    "compensation": "薪酬与福利",
    "performance": "绩效管理",
    "employee_relations": "员工关系管理",
    "learning": "培训与开发",
    "workforce": "人力资源规划",
}

__all__ = [
    "HRIS_MODULE_LABELS",
    "HRIS_SERVICE_MAP",
    "compensation_service",
    "diagnosis_service",
    "employee_relations_service",
    "employee_service",
    "idp_service",
    "learning_service",
    "performance_service",
    "recruitment_service",
    "succession_service",
    "talent_review_service",
    "workforce_service",
]
