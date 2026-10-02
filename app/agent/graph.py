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
                              ├─ HRIS          → route_hris_module（二级路由）
                              │                     ├─ recruitment        → generate_answer
                              │                     ├─ compensation       → generate_answer
                              │                     ├─ performance        → generate_answer
                              │                     ├─ employee_relations → generate_answer
                              │                     ├─ learning           → generate_answer
                              │                     └─ workforce          → generate_answer
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
from app.tools import (
    compensation_tool,
    diagnosis_tool,
    employee_relations_tool,
    idp_tool,
    learning_tool,
    performance_tool,
    recruitment_tool,
    succession_tool,
    talent_review_tool,
    workforce_tool,
)

VALID_INTENTS = {
    "TALENT_REVIEW",
    "SUCCESSION",
    "IDP",
    "DIAGNOSIS",
    "HRIS",
    "UPDATE",
    "PREFERENCE",
    "CHAT",
}

BUSINESS_INTENTS = {
    "TALENT_REVIEW",
    "SUCCESSION",
    "IDP",
    "DIAGNOSIS",
    "HRIS",
}

# HRIS 六大子模块 → LangGraph 节点名
HRIS_MODULES = {
    "recruitment": "recruitment",
    "compensation": "compensation",
    "performance": "performance",
    "employee_relations": "employee_relations",
    "learning": "learning",
    "workforce": "workforce",
}

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


# ---------------- HRIS 六大模块节点 ----------------
# 每个模块内部再做一次动作级判断，result_topic 统一用 HRIS_<模块>_<动作> 命名。


def recruitment_node(state: AgentState) -> dict:
    """招聘管理：简历筛选 / 定 Offer / 面试安排 / 招聘漏斗。"""
    message = state.get("user_message", "")
    db = SessionLocal()
    try:
        department = state.get("department")
        if any(k in message for k in ["漏斗", "招聘进展", "招聘报表", "转化率"]):
            result = recruitment_tool.run_funnel(db, department=department)
            topic = "HRIS_RECRUITMENT_FUNNEL"
        elif any(k in message for k in ["定薪", "Offer", "offer", "薪资建议"]):
            result = recruitment_tool.run_suggest_offer(db, message)
            topic = "HRIS_RECRUITMENT_OFFER"
        elif any(k in message for k in ["面试安排", "安排面试", "面试时间", "推荐面试", "面试官"]):
            result = recruitment_tool.run_interview_proposal(db, message)
            topic = "HRIS_RECRUITMENT_INTERVIEW"
        else:
            result = recruitment_tool.run_screen_for_job(db, message)
            topic = "HRIS_RECRUITMENT_SCREEN"
    finally:
        db.close()
    return {"result": result, "result_topic": topic}


def compensation_node(state: AgentState) -> dict:
    """薪酬与福利：公平性 / 调薪预算 / 福利覆盖 / 个人薪酬单。"""
    message = state.get("user_message", "")
    db = SessionLocal()
    try:
        department = state.get("department")
        employee_name = state.get("employee_name")
        if any(k in message for k in ["调薪", "涨薪", "预算", "加薪"]):
            result = compensation_tool.run_salary_adjustment(db, message, department=department)
            topic = "HRIS_COMPENSATION_ADJUSTMENT"
        elif any(k in message for k in ["福利", "参保", "体检", "五险一金"]):
            result = compensation_tool.run_benefits(db, message, department=department)
            topic = "HRIS_COMPENSATION_BENEFITS"
        elif employee_name or any(k in message for k in ["薪酬总览", "薪资单", "我的薪酬"]):
            result = compensation_tool.run_compensation_summary(
                db, message, employee_name=employee_name
            )
            topic = "HRIS_COMPENSATION_SUMMARY"
        else:
            result = compensation_tool.run_compa_ratio(db, message, department=department)
            topic = "HRIS_COMPENSATION_COMPA"
    finally:
        db.close()
    return {"result": result, "result_topic": topic}


def performance_node(state: AgentState) -> dict:
    """绩效管理：目标达成 / 评价偏差 / 强制分布 / 改进计划。"""
    message = state.get("user_message", "")
    db = SessionLocal()
    try:
        department = state.get("department")
        period = state.get("period")
        if any(k in message for k in ["目标", "OKR", "okr", "KPI", "kpi", "达成"]):
            result = performance_tool.run_goal_achievement(
                db, message, department=department, period=period
            )
            topic = "HRIS_PERFORMANCE_GOAL"
        elif any(k in message for k in ["自评", "偏差", "认知", "评价一致"]):
            result = performance_tool.run_review_deviation(
                db, message, department=department, period=period
            )
            topic = "HRIS_PERFORMANCE_DEVIATION"
        elif any(k in message for k in ["校准", "强制分布", "分布", "比例"]):
            result = performance_tool.run_distribution_check(
                db, message, department=department, period=period
            )
            topic = "HRIS_PERFORMANCE_DISTRIBUTION"
        elif any(k in message for k in ["改进计划", "PIP", "pip", "绩效改进"]):
            result = performance_tool.run_improvement_tracking(
                db, message, department=department
            )
            topic = "HRIS_PERFORMANCE_IMPROVEMENT"
        else:
            result = performance_tool.run_goal_achievement(
                db, message, department=department, period=period
            )
            topic = "HRIS_PERFORMANCE_GOAL"
    finally:
        db.close()
    return {"result": result, "result_topic": topic}


def employee_relations_node(state: AgentState) -> dict:
    """员工关系：假期 / 考勤 / 关系事件 / 敬业度。"""
    message = state.get("user_message", "")
    db = SessionLocal()
    try:
        employee_name = state.get("employee_name")
        if any(k in message for k in ["纠纷", "申诉", "举报", "关系事件", "劳动"]):
            result = employee_relations_tool.run_relation_cases(db, message)
            topic = "HRIS_ER_CASES"
        elif any(k in message for k in ["敬业度", "满意度", "eNPS", "enps"]):
            result = employee_relations_tool.run_engagement(db, message)
            topic = "HRIS_ER_ENGAGEMENT"
        elif any(k in message for k in ["考勤", "出勤", "迟到", "缺勤"]):
            result = employee_relations_tool.run_attendance(
                db, message, employee_name=employee_name
            )
            topic = "HRIS_ER_ATTENDANCE"
        elif any(k in message for k in ["待审批", "待处理请假"]):
            result = employee_relations_tool.run_pending_leaves(db, message)
            topic = "HRIS_ER_LEAVE_PENDING"
        elif any(k in message for k in ["批准", "通过", "驳回", "拒绝"]):
            result = employee_relations_tool.run_approve_leave(db, message)
            topic = "HRIS_ER_LEAVE_APPROVE"
        elif any(k in message for k in ["提交", "申请", "我要请", "想请", "请个", "请假"]):
            result = employee_relations_tool.run_submit_leave(
                db, message, employee_name=employee_name
            )
            topic = "HRIS_ER_LEAVE_REQUEST"
        else:
            result = employee_relations_tool.run_leave_balance(
                db, message, employee_name=employee_name
            )
            topic = "HRIS_ER_LEAVE_BALANCE"
    finally:
        db.close()
    return {"result": result, "result_topic": topic}


def learning_node(state: AgentState) -> dict:
    """培训与开发：总览 / 必修合规 / 课程推荐 / 效果评估。"""
    message = state.get("user_message", "")
    db = SessionLocal()
    try:
        department = state.get("department")
        employee_name = state.get("employee_name")
        if any(k in message for k in ["推荐", "该学", "课程推荐", "学什么", "补什么"]):
            result = learning_tool.run_recommend_courses(
                db, message, employee_name=employee_name
            )
            topic = "HRIS_LEARNING_RECOMMEND"
        elif any(k in message for k in ["必修", "合规", "未完成", "补训"]):
            result = learning_tool.run_mandatory_compliance(
                db, message, department=department
            )
            topic = "HRIS_LEARNING_COMPLIANCE"
        elif any(k in message for k in ["效果", "满意度", "通过率", "投入产出"]):
            result = learning_tool.run_learning_effectiveness(
                db, message, department=department
            )
            topic = "HRIS_LEARNING_EFFECT"
        else:
            result = learning_tool.run_training_overview(
                db, message, department=department
            )
            topic = "HRIS_LEARNING_OVERVIEW"
    finally:
        db.close()
    return {"result": result, "result_topic": topic}


def workforce_node(state: AgentState) -> dict:
    """人力资源规划：编制 / 供需预测 / 离职风险 / 继任联动。"""
    message = state.get("user_message", "")
    db = SessionLocal()
    try:
        department = state.get("department")
        if any(k in message for k in ["离职风险", "流失风险", "谁要走", "保留"]):
            result = workforce_tool.run_attrition_risk(db, message, department=department)
            topic = "HRIS_WORKFORCE_ATTRITION"
        elif any(k in message for k in ["预测", "供需", "缺口测算", "需求"]):
            result = workforce_tool.run_supply_demand_forecast(
                db, message, department=department
            )
            topic = "HRIS_WORKFORCE_FORECAST"
        elif any(k in message for k in ["继任覆盖", "接班风险", "继任真空"]):
            result = workforce_tool.run_succession_coverage_link(db, message)
            topic = "HRIS_WORKFORCE_SUCCESSION_LINK"
        else:
            result = workforce_tool.run_headcount_review(db, message, department=department)
            topic = "HRIS_WORKFORCE_HEADCOUNT"
    finally:
        db.close()
    return {"result": result, "result_topic": topic}


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
            "我是智能人才发展与 HRIS Agent，目前可以做这些事：\n"
            "人才管理与组织发展：\n"
            "  1. 人才盘点九宫格（绩效 × 潜力）\n"
            "  2. 关键岗位继任地图与人才梯队分析\n"
            "  3. 个人发展计划 IDP（70-20-10 发展法则）\n"
            "  4. 组织诊断与健康度打分\n"
            "HRIS 六大模块：\n"
            "  5. 招聘管理：简历筛选、定 Offer、面试安排、招聘漏斗\n"
            "  6. 薪酬与福利：薪资公平性、调薪模拟、福利覆盖\n"
            "  7. 绩效管理：目标达成、评价偏差、强制分布、改进计划\n"
            "  8. 员工关系管理：假期、考勤、关系事件、敬业度\n"
            "  9. 培训与开发：培训总览、必修合规、课程推荐\n"
            "  10. 人力资源规划：编制达成、供需预测、离职风险\n"
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


def decide_hris_module(state: AgentState) -> dict:
    """HRIS 二级路由：决定具体进入哪个业务模块。

    大模型可用时让它判断，不可用时回退到关键词路由。
    """
    message = state.get("user_message", "")

    module = state.get("hris_module")
    llm = get_llm_client()
    llm_used = bool(llm.available()) and module is None

    if module is None and llm.available():
        system_prompt, user_prompt = prompts.render_hris_module_prompt(message)
        data = llm.invoke_json(system_prompt, user_prompt)
        if isinstance(data, dict) and data.get("module") in HRIS_MODULES:
            module = data["module"]

    if module not in HRIS_MODULES:
        module = rules.rule_hris_module(message) or "recruitment"

    return {"hris_module": module, "llm_used": llm_used}


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
        "HRIS": "decide_hris_module",
    }
    # UPDATE 沿用上一轮 HRIS 主题时，需要重新走一次二级路由，
    # 否则无法知道进入哪个具体模块。
    if topic == "HRIS" and request_type not in BUSINESS_INTENTS:
        return "decide_hris_module"
    return mapping.get(topic, "generate_answer")


def route_hris_module(state: AgentState) -> str:
    """按 hris_module 状态分发到六个具体业务节点。"""
    return HRIS_MODULES.get(state.get("hris_module") or "", "recruitment")


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
    graph.add_node("decide_hris_module", decide_hris_module)
    graph.add_node("recruitment", recruitment_node)
    graph.add_node("compensation", compensation_node)
    graph.add_node("performance", performance_node)
    graph.add_node("employee_relations", employee_relations_node)
    graph.add_node("learning", learning_node)
    graph.add_node("workforce", workforce_node)
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
            "decide_hris_module": "decide_hris_module",
            "generate_answer": "generate_answer",
        },
    )

    # HRIS 二级路由：一个 deciding 节点 → 六个具体业务节点
    graph.add_conditional_edges(
        "decide_hris_module",
        route_hris_module,
        {
            "recruitment": "recruitment",
            "compensation": "compensation",
            "performance": "performance",
            "employee_relations": "employee_relations",
            "learning": "learning",
            "workforce": "workforce",
        },
    )

    graph.add_edge("talent_review", "generate_answer")
    graph.add_edge("succession", "generate_answer")
    graph.add_edge("idp", "generate_answer")
    graph.add_edge("diagnosis", "generate_answer")
    graph.add_edge("recruitment", "generate_answer")
    graph.add_edge("compensation", "generate_answer")
    graph.add_edge("performance", "generate_answer")
    graph.add_edge("employee_relations", "generate_answer")
    graph.add_edge("learning", "generate_answer")
    graph.add_edge("workforce", "generate_answer")

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
            "decide_hris_module": "decide_hris_module",
            "generate_answer": "generate_answer",
        },
    )

    graph.add_edge("generate_answer", END)
    graph.add_edge("chat", END)

    return graph.compile(checkpointer=get_checkpointer())
