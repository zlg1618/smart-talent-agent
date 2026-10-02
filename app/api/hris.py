"""统一 HRIS 路由入口：聚合六大模块子路由并提供模块清单。"""

from fastapi import APIRouter

from app.api.hr import (
    compensation,
    employee_relations,
    learning,
    performance,
    recruitment,
    workforce,
)

router = APIRouter(prefix="/api/hris", tags=["HRIS"])

MODULE_LABELS = {
    "recruitment": "招聘管理",
    "compensation": "薪酬与福利",
    "performance": "绩效管理",
    "employee_relations": "员工关系管理",
    "learning": "培训与开发",
    "workforce": "人力资源规划",
}

router.include_router(recruitment.router)
router.include_router(compensation.router)
router.include_router(performance.router)
router.include_router(employee_relations.router)
router.include_router(learning.router)
router.include_router(workforce.router)


@router.get("/modules")
def list_modules():
    """列出 HRIS 六大模块及其路由前缀。"""
    return {
        "total": len(MODULE_LABELS),
        "modules": [
            {"key": key, "name": label, "prefix": f"/api/hris/{key}"}
            for key, label in MODULE_LABELS.items()
        ],
    }
