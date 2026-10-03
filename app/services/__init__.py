from app.services import (
    compensation_service,
    employee_relations_service,
    employee_service,
    learning_service,
    organization_service,
    performance_service,
    recruitment_service,
    talent_development_service,
    workforce_service,
)

# 核心双域 → 计算服务映射
CORE_SERVICE_MAP: dict[str, object] = {
    "organization_development": organization_service,
    "talent_development": talent_development_service,
}

# HRIS 六大模块 → 计算服务映射
HRIS_SERVICE_MAP: dict[str, object] = {
    "recruitment": recruitment_service,
    "compensation": compensation_service,
    "performance": performance_service,
    "employee_relations": employee_relations_service,
    "learning": learning_service,
    "workforce": workforce_service,
}

# 核心双域展示名
CORE_MODULE_LABELS: dict[str, str] = {
    "organization_development": "组织发展",
    "talent_development": "人才发展",
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
    "CORE_MODULE_LABELS",
    "CORE_SERVICE_MAP",
    "HRIS_MODULE_LABELS",
    "HRIS_SERVICE_MAP",
    "compensation_service",
    "employee_relations_service",
    "employee_service",
    "learning_service",
    "organization_service",
    "performance_service",
    "recruitment_service",
    "talent_development_service",
    "workforce_service",
]
