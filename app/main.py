"""FastAPI 入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import (
    ai,
    ats,
    diagnosis,
    employee,
    health,
    hr_transaction,
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
    description="基于 LangGraph 与 FastAPI 的智能组织发展与人才盘点 Agent",
    version="1.0.0",
    lifespan=lifespan,
)


app.include_router(health.router)
app.include_router(ai.router)
app.include_router(employee.router)
app.include_router(talent_review.router)
app.include_router(succession.router)
app.include_router(idp.router)
app.include_router(diagnosis.router)
app.include_router(ats.router)
app.include_router(hr_transaction.router)
app.include_router(integrations.router)


@app.get("/")
def root():
    settings = get_settings()
    return {
        "service": "smart-talent-agent",
        "docs": "/docs",
        "database": settings.database_url.split("://")[0],
        "llm_provider": settings.llm_provider,
    }
