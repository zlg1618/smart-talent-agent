from app.tools import (
    compensation_tool,
    employee_relations_tool,
    learning_tool,
    organization_tool,
    performance_tool,
    recruitment_tool,
    talent_development_tool,
    workforce_tool,
)

# 核心双域 → Tool 映射
CORE_TOOL_MAP: dict[str, object] = {
    "organization_development": organization_tool,
    "talent_development": talent_development_tool,
}

# HRIS 六大模块 → Tool 映射
HRIS_TOOL_MAP: dict[str, object] = {
    "recruitment": recruitment_tool,
    "compensation": compensation_tool,
    "performance": performance_tool,
    "employee_relations": employee_relations_tool,
    "learning": learning_tool,
    "workforce": workforce_tool,
}

__all__ = [
    "CORE_TOOL_MAP",
    "HRIS_TOOL_MAP",
    "compensation_tool",
    "employee_relations_tool",
    "learning_tool",
    "organization_tool",
    "performance_tool",
    "recruitment_tool",
    "talent_development_tool",
    "workforce_tool",
]
