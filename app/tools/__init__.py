from app.tools import (
    compensation_tool,
    diagnosis_tool,
    employee_relations_tool,
    idp_tool,
    learning_tool,
    performance_tool,
    recruitment_tool,
    succession_tool,
    talent_review_tool,
    workforce_tool,
)

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
    "HRIS_TOOL_MAP",
    "compensation_tool",
    "diagnosis_tool",
    "employee_relations_tool",
    "idp_tool",
    "learning_tool",
    "performance_tool",
    "recruitment_tool",
    "succession_tool",
    "talent_review_tool",
    "workforce_tool",
]
