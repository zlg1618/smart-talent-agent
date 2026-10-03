"""接口请求与响应模型。"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """AI 对话请求。

    同一个 thread_id 下的多轮对话共享一份查询条件状态。
    """

    thread_id: str = Field(default="default", description="会话 ID，用于多轮记忆")
    message: str = Field(..., description="用户消息")


class ChatResponse(BaseModel):
    thread_id: str
    message: str
    request_type: Optional[str] = None
    active_topic: Optional[str] = None
    # 核心双域：organization_development / talent_development
    core_module: Optional[str] = None
    # HRIS 子模块：recruitment / compensation / performance /
    # employee_relations / learning / workforce
    hris_module: Optional[str] = None
    conditions: dict[str, Any] = {}
    result: Optional[dict[str, Any]] = None
    answer: Optional[str] = None
    llm_used: bool = False  # 本轮回答是否由大模型生成（false 表示走规则模板）
