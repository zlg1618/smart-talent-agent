"""AI 对话接口。

同一个 thread_id 下多轮对话共享盘点条件，支持随时修改条件并重新盘点。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.schemas import ChatRequest, ChatResponse
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/ai", tags=["AI 对话"])

_ai_service: AIService | None = None


def get_ai_service() -> AIService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, service: AIService = Depends(get_ai_service)):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="message 不能为空")
    return service.chat(request.thread_id, request.message)


@router.get("/state/{thread_id}")
def get_state(thread_id: str, service: AIService = Depends(get_ai_service)):
    """查看会话当前记忆的盘点条件与偏好。"""
    return service.get_state(thread_id)


@router.post("/reset/{thread_id}")
def reset_state(thread_id: str, service: AIService = Depends(get_ai_service)):
    """清空会话记忆。"""
    return service.reset(thread_id)


@router.get("/llm")
def llm_info():
    from app.services.ai_service import llm_status

    return llm_status()


@router.get("/employees/sample")
def sample_employees(db: Session = Depends(get_db), limit: int = 10):
    """返回少量员工姓名，方便构造对话请求。"""
    from app.services import employee_service

    employees = employee_service.list_employees(db)[:limit]
    return [
        {
            "name": e.name,
            "department": e.department,
            "job_level": e.job_level,
            "position_title": e.position_title,
        }
        for e in employees
    ]
