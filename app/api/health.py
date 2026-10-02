"""健康检查。"""

from fastapi import APIRouter

from app.services.ai_service import llm_status

router = APIRouter(prefix="/api/health", tags=["健康检查"])


@router.get("")
def health():
    return {"status": "ok", "service": "smart-talent-agent", "llm": llm_status()}
