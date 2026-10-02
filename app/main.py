"""FastAPI 入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import (
    ai,
    diagnosis,
    employee,
    health,
    hris,
    idp,
    integrations,
    succession,
    talent_review,
)
from app.config.database import init_db
from app.config.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时建表，确保接口可用
    init_db()
    yield


app = FastAPI(
    title="Smart Talent Agent",
    description=(
        "智能组织发展与人才盘点 Agent，"
        "并集成 HRIS 六大模块：招聘、薪酬与福利、绩效管理、"
        "员工关系管理、培训与开发、人力资源规划"
    ),
    version="2.0.0",
    lifespan=lifespan,
)


app.include_router(health.router)
app.include_router(ai.router)
app.include_router(employee.router)
# 人才管理与组织发展
app.include_router(talent_review.router)
app.include_router(succession.router)
app.include_router(idp.router)
app.include_router(diagnosis.router)
# HRIS 六大模块 + 外部系统接入
app.include_router(hris.router)
app.include_router(integrations.router)


@app.get("/")
def root():
    settings = get_settings()
    return {
        "service": "smart-talent-agent",
        "docs": "/docs",
        "database": settings.database_url.split("://")[0],
        "llm_provider": settings.llm_provider,
        "modules": {
            "talent": ["/api/talent", "/api/succession", "/api/idp", "/api/diagnosis"],
            "hris": ["/api/hris/recruitment", "/api/hris/compensation",
                     "/api/hris/performance", "/api/hris/employee-relations",
                     "/api/hris/learning", "/api/hris/workforce"],
            "integrations": "/api/integrations",
        },
    }
