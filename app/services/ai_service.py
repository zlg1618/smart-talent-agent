"""AI 对话服务：对外封装 LangGraph Agent。"""

from typing import Any

from app.agent.graph import build_graph
from app.config.database import SessionLocal
from app.llm import get_llm_client
from app.services import employee_service


class AIService:
    def __init__(self):
        self.graph = build_graph()

    def chat(self, thread_id: str, message: str) -> dict[str, Any]:
        """执行一轮对话，返回意图、条件、工具结果与回答。"""
        config = {"configurable": {"thread_id": thread_id}}
        state = self.graph.invoke({"user_message": message}, config=config)

        return {
            "thread_id": thread_id,
            "message": message,
            "request_type": state.get("request_type"),
            "active_topic": state.get("active_topic"),
            "hris_module": state.get("hris_module"),
            "conditions": {
                "department": state.get("department"),
                "period": state.get("period"),
                "job_level": state.get("job_level"),
                "employee_name": state.get("employee_name"),
            },
            "preferences": state.get("preferences") or {},
            "result": state.get("result"),
            "answer": state.get("answer"),
            "llm_used": bool(state.get("llm_used")),
        }

    def get_state(self, thread_id: str) -> dict[str, Any]:
        """查看某个会话当前记忆的盘点条件。"""
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = self.graph.get_state(config)
        values = snapshot.values if snapshot else {}
        return {
            "thread_id": thread_id,
            "conditions": {
                "department": values.get("department"),
                "period": values.get("period"),
                "job_level": values.get("job_level"),
                "employee_name": values.get("employee_name"),
            },
            "preferences": values.get("preferences") or {},
            "active_topic": values.get("active_topic"),
            "hris_module": values.get("hris_module"),
        }

    def reset(self, thread_id: str) -> dict[str, Any]:
        """清空某个会话的记忆。"""
        config = {"configurable": {"thread_id": thread_id}}
        self.graph.update_state(
            config,
            {
                "department": None,
                "period": None,
                "job_level": None,
                "employee_name": None,
                "preferences": {},
                "active_topic": None,
                "result": None,
                "answer": None,
            },
        )
        return {"thread_id": thread_id, "reset": True}


def build_ai_service() -> AIService:
    return AIService()


def default_period() -> str | None:
    db = SessionLocal()
    try:
        return employee_service.get_latest_period(db)
    finally:
        db.close()


def llm_status() -> dict[str, Any]:
    client = get_llm_client()
    return {
        "provider": client.settings.llm_provider,
        "client_ready": client.available(),
        "reachable": client.probe(),
        "error": client.error,
        "fallback_to_rule": client.settings.llm_fallback_to_rule,
        "note": "client_ready 仅表示客户端已构建；reachable 表示服务真实可达。"
        "两者为 false 时 Agent 自动回退到规则引擎。",
    }
