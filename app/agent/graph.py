"""LangGraph Agent 工作流。

职责划分：
- 大模型：意图识别、信息抽取、自然语言解释
- Python：九宫格定位、继任覆盖、梯队供给比、能力差距、组织健康分
- 数据库：唯一真实数据来源

工作流：
    analyze_request
        ├─ CHAT        → chat
        ├─ PREFERENCE  → extract_preferences → generate_answer
        └─ 其他         → extract_info
                              ├─ TALENT_REVIEW → talent_review → generate_answer
                              ├─ SUCCESSION    → succession    → generate_answer
                              ├─ IDP           → idp           → generate_answer
                              ├─ DIAGNOSIS     → diagnosis     → generate_answer
                              └─ UPDATE(无主题) → generate_answer
"""

from sqlalchemy import select

from app.agent import prompts, rules
from app.agent.formatters import format_result
from app.agent.memory import get_checkpointer
from app.agent.state import AgentState
from app.config.database import SessionLocal
from app.llm import get_llm_client
from app.models import PerformanceRecord
from app.services import employee_service
from app.tools import diagnosis_tool, idp_tool, succession_tool, talent_review_tool

VALID_INTENTS = {
    "TALENT_REVIEW",
    "SUCCESSION",
    "IDP",
    "DIAGNOSIS",
    "UPDATE",
    "PREFERENCE",
    "CHAT",
}

BUSINESS_INTENTS = {"TALENT_REVIEW", "SUCCESSION", "IDP", "DIAGNOSIS"}

PIPELINE_KEYWORDS = ["梯队", "断层", "职级分布", "储备", "供给"]

CLEAR_KEYWORDS = ["不限", "取消筛选", "清除筛选", "清空筛选", "所有人才", "全部人才", "不要筛选"]


def _all_periods(db) -> list[str]:
    return list(
        db.execute(select(PerformanceRecord.period).distinct()).scalars().all()
    )


# ---------------------------- 节点 ----------------------------


def analyze_request(state: AgentState) -> dict:
    """意图识别。大模型不可用时回退到关键词规则。"""
    message = state.get("user_message", "")
    llm = get_llm_client()

    intent = None
    if llm.available():
        system_prompt, user_prompt = prompts.render_intent_prompt(message)
        data = llm.invoke_json(system_prompt, user_prompt)
        if data and data.get("request_type") in VALID_INTENTS:
            intent = data["request_type"]

    if intent is None:
        intent = rules.rule_intent(message)

    patch: dict = {
        "request_type": intent,
        "result": None,
        "result_topic": None,
        "answer": None,
        "llm_used": False,
    }
    if intent in BUSINESS_INTENTS:
        patch["active_topic"] = intent
    return patch


def extract_info(state: AgentState) -> dict:
    """抽取部门、周期、职级、员工姓名，写入跨轮次状态。"""
    message = state.get("user_message", "")
    db = SessionLocal()
    try:
        extracted = None
        llm = get_llm_client()
        if llm.available():
            departments = employee_service.list_departments(db)
            periods = _all_periods(db)
            system_prompt, user_prompt = prompts.render_extract_prompt(
                message, departments, periods
            )
            data = llm.invoke_json(system_prompt, user_prompt)
            if isinstance(data, dict):
                extracted = data

        if not extracted:
            extracted = rules.rule_extract(db, message)
    finally:
        db.close()

    patch: dict = {}
    for key in ("department", "period", "job_level", "employee_name"):
        value = extracted.get(key)
        if value:
            patch[key] = value
    return patch


def extract_preferences(state: AgentState) -> dict:
    """抽取筛选偏好。"""
    message = state.get("user_message", "")
    llm = get_llm_client()

    # 用户明确要求取消筛选时，清空全部偏好
    if any(k in message for k in CLEAR_KEYWORDS):
        return {"preferences": {}}

    data = None
    if llm.available():
        system_prompt, user_prompt = prompts.render_preference_prompt(message)
        data = llm.invoke_json(system_prompt, user_prompt)

    if not isinstance(data, dict):
        data = rules.rule_preference(message)

    preferences = dict(state.get("preferences") or {})
    for key in ("only_grid", "criticality", "exclude_readiness"):
        value = data.get(key)
        if value:
            preferences[key] = value
    return {"preferences": preferences}


def talent_review_node(state: AgentState) -> dict:
    db = SessionLocal()
    try:
        preferences = state.get("preferences") or {}
        result = talent_review_tool.run_talent_review(
            db,
            department=state.get("department"),
            period=state.get("period"),
            job_level=state.get("job_level"),
            only_grid=preferences.get("only_grid"),
        )
    finally:
        db.close()
    return {"result": result, "result_topic": "TALENT_REVIEW"}


def succession_node(state: AgentState) -> dict:
    db = SessionLocal()
    try:
        preferences = state.get("preferences") or {}
        message = state.get("user_message", "")
        if any(k in message for k in PIPELINE_KEYWORDS):
            result = succession_tool.run_talent_pipeline(
                db, department=state.get("department")
            )
            topic = "PIPELINE"
        else:
            result = succession_tool.run_succession_map(
                db,
                department=state.get("department"),
                criticality=preferences.get("criticality"),
                exclude_readiness=preferences.get("exclude_readiness"),
            )
            topic = "SUCCESSION"
    finally:
        db.close()
    return {"result": result, "result_topic": topic}


def idp_node(state: AgentState) -> dict:
    name = state.get("employee_name")
    if not name:
        return {
            "result": {
                "error": "请告诉我要为哪位员工生成个人发展计划，"
                "例如“给张伟做一份 IDP”或“生成李娜的发展计划”。"
            },
            "result_topic": "IDP",
        }

    db = SessionLocal()
    try:
        result = idp_tool.run_idp(
            db, name=name, period=state.get("period")
        )
    finally:
        db.close()
    return {"result": result, "result_topic": "IDP"}


def diagnosis_node(state: AgentState) -> dict:
    db = SessionLocal()
    try:
        result = diagnosis_tool.run_org_diagnosis(
            db, department=state.get("department"), period=state.get("period")
        )
    finally:
        db.close()
    return {"result": result, "result_topic": "DIAGNOSIS"}


def chat_node(state: AgentState) -> dict:
    message = state.get("user_message", "")
    llm = get_llm_client()

    answer = None
    llm_used = False
    if llm.available():
        system_prompt, user_prompt = prompts.render_chat_prompt(message)
        answer = llm.invoke(system_prompt, user_prompt)
        llm_used = bool(answer)

    if not answer:
        answer = (
            "我是人才发展 Agent，目前可以做四件事：\n"
            "1. 人才盘点九宫格（绩效 × 潜力）\n"
            "2. 关键岗位继任地图与人才梯队分析\n"
            "3. 个人发展计划 IDP（70-20-10 发展法则）\n"
            "4. 组织诊断与健康度打分\n"
            "请告诉我你想先看哪一个，以及部门或考核周期。"
        )
    return {"answer": answer, "llm_used": llm_used}


def generate_answer(state: AgentState) -> dict:
    """用大模型解释真实计算结果；模型不可用时回退到模板输出。"""
    result = state.get("result")
    topic = state.get("result_topic") or state.get("active_topic") or ""

    # 偏好更新：没有工具结果，只做确认
    if not result:
        if state.get("request_type") == "PREFERENCE":
            preferences = state.get("preferences") or {}
            return {"answer": f"已更新筛选偏好：{preferences}。请继续提出你的盘点需求。"}
        conditions = {
            k: state.get(k)
            for k in ("department", "period", "job_level", "employee_name")
            if state.get(k)
        }
        hint = f"（当前条件：{conditions}）" if conditions else ""
        return {
            "answer": f"已更新盘点条件{hint}。请告诉我下一步要做什么，"
            "例如“做一次人才盘点”“看一下继任地图”“做个组织诊断”。"
        }

    if result.get("error"):
        return {"answer": result["error"]}

    if result.get("total") == 0 and topic == "TALENT_REVIEW":
        applied = {
            k: state.get(k)
            for k in ("department", "period", "job_level")
            if state.get(k)
        }
        preferences = state.get("preferences") or {}
        only_grid = preferences.get("only_grid")
        if only_grid:
            applied["只看格子"] = only_grid
        return {
            "answer": f"当前条件下没有参与盘点的员工（生效条件：{applied}）。"
            "请调整部门、职级或取消筛选偏好后重试。"
        }

    llm = get_llm_client()
    answer = None
    llm_used = False
    if llm.available():
        system_prompt, user_prompt = prompts.render_answer_prompt(
            state.get("user_message", ""), result
        )
        answer = llm.invoke(system_prompt, user_prompt)
        llm_used = bool(answer)

    if not answer:
        answer = format_result(topic, result)
    return {"answer": answer, "llm_used": llm_used}


# ---------------------------- 路由 ----------------------------


def route_by_intent(state: AgentState) -> str:
    request_type = state.get("request_type")
    if request_type == "CHAT":
        return "chat"
    if request_type == "PREFERENCE":
        return "extract_preferences"
    return "extract_info"


def route_by_topic(state: AgentState) -> str:
    """根据意图或最近的业务主题路由到对应 Tool 节点。"""
    request_type = state.get("request_type")
    if request_type in BUSINESS_INTENTS:
        topic = request_type
    else:
        # UPDATE 场景：沿用上一轮的业务主题重新计算
        topic = state.get("active_topic")

    mapping = {
        "TALENT_REVIEW": "talent_review",
        "SUCCESSION": "succession",
        "IDP": "idp",
        "DIAGNOSIS": "diagnosis",
    }
    return mapping.get(topic, "generate_answer")


# ---------------------------- 构建图 ----------------------------


def build_graph():
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(AgentState)

    graph.add_node("analyze_request", analyze_request)
    graph.add_node("extract_info", extract_info)
    graph.add_node("extract_preferences", extract_preferences)
    graph.add_node("talent_review", talent_review_node)
    graph.add_node("succession", succession_node)
    graph.add_node("idp", idp_node)
    graph.add_node("diagnosis", diagnosis_node)
    graph.add_node("chat", chat_node)
    graph.add_node("generate_answer", generate_answer)

    graph.add_edge(START, "analyze_request")

    graph.add_conditional_edges(
        "analyze_request",
        route_by_intent,
        {
            "extract_info": "extract_info",
            "extract_preferences": "extract_preferences",
            "chat": "chat",
        },
    )

    graph.add_conditional_edges(
        "extract_info",
        route_by_topic,
        {
            "talent_review": "talent_review",
            "succession": "succession",
            "idp": "idp",
            "diagnosis": "diagnosis",
            "generate_answer": "generate_answer",
        },
    )

    graph.add_edge("talent_review", "generate_answer")
    graph.add_edge("succession", "generate_answer")
    graph.add_edge("idp", "generate_answer")
    graph.add_edge("diagnosis", "generate_answer")
    # 设置偏好后沿用上一轮的业务主题重新计算，
    # 例如"做一次盘点"之后说"只看明星人才"会直接给出过滤后的结果。
    graph.add_conditional_edges(
        "extract_preferences",
        route_by_topic,
        {
            "talent_review": "talent_review",
            "succession": "succession",
            "idp": "idp",
            "diagnosis": "diagnosis",
            "generate_answer": "generate_answer",
        },
    )

    graph.add_edge("generate_answer", END)
    graph.add_edge("chat", END)

    return graph.compile(checkpointer=get_checkpointer())
