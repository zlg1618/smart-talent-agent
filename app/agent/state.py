"""Agent 状态设计。

通过 LangGraph Checkpointer 按 thread_id 持久化，
实现"多轮对话中持续维护盘点条件"的效果。
"""

from typing import Any, Optional, TypedDict


class AgentState(TypedDict, total=False):
    # 输入
    user_message: str

    # 意图
    request_type: str  # TALENT_REVIEW / SUCCESSION / IDP / DIAGNOSIS / UPDATE / PREFERENCE / CHAT
    active_topic: str  # 最近一次业务意图，用于修改条件后重新执行

    # 盘点条件（跨轮次记忆）
    department: Optional[str]
    period: Optional[str]
    job_level: Optional[str]
    employee_name: Optional[str]

    # 筛选偏好
    preferences: dict

    # 工具结果
    result: Optional[dict]
    result_topic: Optional[str]  # 结果对应的格式化模板

    # 输出
    answer: str
    llm_used: bool  # 本轮回答是否真正由大模型生成
