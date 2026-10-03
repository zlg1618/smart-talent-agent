"""Agent 状态设计。

通过 LangGraph Checkpointer 按 thread_id 持久化，
实现"多轮对话中持续维护查询条件"的效果。
"""

from typing import Any, Optional, TypedDict


class AgentState(TypedDict, total=False):
    # 输入
    user_message: str

    # 意图
    request_type: str  # ORG_DEV / TALENT_DEV / HRIS / UPDATE / CHAT
    active_topic: str  # 最近一次业务意图，用于修改条件后重新执行
    core_module: Optional[str]
    # 核心双域：organization_development / talent_development
    hris_module: Optional[str]
    # HRIS 子模块：recruitment / compensation / performance /
    # employee_relations / learning / workforce

    # 查询条件（跨轮次记忆）
    department: Optional[str]
    period: Optional[str]
    job_level: Optional[str]
    employee_name: Optional[str]

    # 工具结果
    result: Optional[dict]
    result_topic: Optional[str]  # 结果对应的格式化模板

    # 输出
    answer: str
    llm_used: bool  # 本轮回答是否真正由大模型生成
