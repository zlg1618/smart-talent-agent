"""核心双域路由包。

    organization_development  组织发展：架构编制 / 组织效能 / 职级体系 / 变革模拟
    talent_development        人才发展：能力差距 / 任职资格 / 人才池 / 项目 / 导师制
"""

from fastapi import APIRouter

from app.api.core import organization, talent

router = APIRouter(prefix="/api/core", tags=["核心域"])

MODULE_LABELS = {
    "organization_development": "组织发展",
    "talent_development": "人才发展",
}

router.include_router(organization.router)
router.include_router(talent.router)


@router.get("/modules")
def list_modules():
    """列出核心双域及其路由前缀。"""
    return {
        "total": len(MODULE_LABELS),
        "modules": [
            {
                "key": "organization_development",
                "name": "组织发展",
                "prefix": "/api/core/organization-development",
            },
            {
                "key": "talent_development",
                "name": "人才发展",
                "prefix": "/api/core/talent-development",
            },
        ],
    }


__all__ = ["organization", "talent"]
