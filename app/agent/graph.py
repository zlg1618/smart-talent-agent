"""LangGraph Agent 工作流。

职责划分：
- 大模型：意图识别、信息抽取、自然语言解释
- Python：编制达成、人效指数、职级结构、任职资格匹配度、人才池活跃度
- 数据库：唯一真实数据来源

工作流：
    analyze_request
        ├─ CHAT          → chat
        └─ 其他           → extract_info
                              ├─ ORG_DEV    → 组织发展节点（四路动作分发）
                              ├─ TALENT_DEV → 人才发展节点（五路动作分发）
                              ├─ HRIS       → route_hris_module（二级路由）
                              │                  ├─ recruitment        → generate_answer
                              │                  ├─ compensation       → generate_answer
                              │                  ├─ performance        → generate_answer
                              │                  ├─ employee_relations → generate_answer
                              │                  ├─ learning           → generate_answer
                              │                  └─ workforce          → generate_answer
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
    employee_relations_tool,
    learning_tool,
    organization_tool,
    performance_tool,
    recruitment_tool,
    talent_development_tool,
    workforce_tool,
)

VALID_INTENTS = {"ORG_DEV", "TALENT_DEV", "HRIS", "UPDATE", "CHAT"}

BUSINESS_INTENTS = {"ORG_DEV", "TALENT_DEV", "HRIS"}

# 核心双域 → LangGraph 节点名
CORE_MODULES = {
    "organization_development": "org_dev",
    "talent_development": "talent_dev",
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

# 组织发展域内部动作关键词（顺序即优先级）
OD_ACTION_KEYWORDS = [
    ("DIAGNOSIS", ["组织诊断", "诊断", "健康度", "痛点", "瓶颈", "组织扫描",
                   "7S", "7s", "6-BOX", "6-box", "六盒", "五维"]),
    ("CULTURE", ["文化", "氛围", "敬业度", "价值观", "心理安全"]),
    ("STRATEGY", ["战略解码", "战略", "目标拆解", "目标对齐", "解码"]),
    ("CHANGE", ["组织变革", "变革", "合并", "拆分", "分拆", "扩编", "缩编",
                "新设", "重组", "并购", "转型", "调整"]),
    ("ARCHITECTURE", ["职级", "职族", "晋升率", "晋升通道", "金字塔", "带宽"]),
    ("EFFECTIVENESS", ["人效", "效能", "人均产出", "人工成本", "成本率"]),
    ("STRUCTURE", ["架构", "组织单元", "编制", "层级", "管理幅度", "汇报线", "管控", "权责"]),
]

# 人才发展域内部动作关键词（顺序即优先级）
TD_ACTION_KEYWORDS = [
    ("MENTORSHIP", ["导师", "带教", "师徒"]),
    ("IDP", ["IDP", "idp", "个人发展计划", "发展计划"]),
    ("PLACEMENT", ["任用", "晋升建议", "调整建议", "人员调整", "晋升名单",
                   "提拔", "淘汰", "保留方案"]),
    ("SUCCESSION", ["继任", "接班", "梯队", "后备", "关键岗位"]),
    ("POOL", ["人才池", "池子", "入池", "出池"]),
    ("PROGRAM", ["发展项目", "培养项目", "行动学习", "训练营", "轮岗", "内训"]),
    ("MODEL", ["胜任力", "素质模型", "能力模型", "能力项"]),
    ("REVIEW", ["盘点", "九宫格", "人才地图", "高潜", "360", "明星", "短板"]),
    ("STANDARD", ["任职资格", "人才标准", "匹配度", "够不够格", "晋升",
                  "下一职级", "晋升评审"]),
    ("COMPETENCY", ["能力", "差距", "画像"]),
]


def _all_periods(db) -> list[str]:
    return list(
        db.execute(select(PerformanceRecord.period).distinct()).scalars().all()
    )


def _pick_action(message: str, keywords: list[tuple[str, list[str]]], default: str) -> str:
    for action, words in keywords:
        if any(w in message for w in words):
            return action
    return default


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


# ---------------- 核心域 · 组织发展 ----------------


def org_dev_node(state: AgentState) -> dict:
    """组织发展：架构编制 / 组织效能 / 职级体系 / 变革模拟。"""
    message = state.get("user_message", "")
    action = _pick_action(message, OD_ACTION_KEYWORDS, "STRUCTURE")

    db = SessionLocal()
    try:
        department = state.get("department")
        period = state.get("period")
        if action == "DIAGNOSIS":
            result = organization_tool.run_org_diagnosis(
                db, message, department=department, period=period
            )
            topic = "OD_DIAGNOSIS"
        elif action == "CULTURE":
            result = organization_tool.run_org_culture(
                db, message, department=department, period=period
            )
            topic = "OD_CULTURE"
        elif action == "STRATEGY":
            result = organization_tool.run_strategy_decode(
                db, message, department=department, period=period
            )
            topic = "OD_STRATEGY"
        elif action == "CHANGE":
            result = organization_tool.run_org_change(db, message, department=department)
            topic = "OD_CHANGE"
        elif action == "ARCHITECTURE":
            result = organization_tool.run_job_architecture(db, message, department=department)
            topic = "OD_ARCHITECTURE"
        elif action == "EFFECTIVENESS":
            result = organization_tool.run_org_effectiveness(
                db, message, department=department, period=period
            )
            topic = "OD_EFFECTIVENESS"
        else:
            result = organization_tool.run_org_structure(
                db, message, department=department, period=period
            )
            topic = "OD_STRUCTURE"
    finally:
        db.close()
    return {
        "result": result,
        "result_topic": topic,
        "core_module": "organization_development",
    }


# ---------------- 核心域 · 人才发展 ----------------


def talent_dev_node(state: AgentState) -> dict:
    """人才发展：能力差距 / 任职资格 / 人才池 / 发展项目 / 导师制。"""
    message = state.get("user_message", "")
    action = _pick_action(message, TD_ACTION_KEYWORDS, "COMPETENCY")

    db = SessionLocal()
    try:
        department = state.get("department")
        employee_name = state.get("employee_name")
        job_level = state.get("job_level")
        period = state.get("period")
        if action == "MENTORSHIP":
            result = talent_development_tool.run_mentorship(db, message, department=department)
            topic = "TD_MENTORSHIP"
        elif action == "IDP":
            result = talent_development_tool.run_idp(
                db, message, employee_name=employee_name,
                department=department, period=period,
            )
            topic = "TD_IDP"
        elif action == "PLACEMENT":
            result = talent_development_tool.run_talent_placement(
                db, message, department=department, period=period
            )
            topic = "TD_PLACEMENT"
        elif action == "SUCCESSION":
            result = talent_development_tool.run_succession(db, message, department=department)
            topic = "TD_SUCCESSION"
        elif action == "POOL":
            result = talent_development_tool.run_talent_pool(db, message, department=department)
            topic = "TD_POOL"
        elif action == "PROGRAM":
            result = talent_development_tool.run_development_program(db, message)
            topic = "TD_PROGRAM"
        elif action == "MODEL":
            result = talent_development_tool.run_competency_model(
                db, message, employee_name=employee_name, job_level=job_level
            )
            topic = "TD_MODEL"
        elif action == "REVIEW":
            result = talent_development_tool.run_talent_review(
                db, message, department=department, period=period, job_level=job_level
            )
            topic = "TD_REVIEW"
        elif action == "STANDARD":
            result = talent_development_tool.run_talent_standard_match(
                db,
                message,
                employee_name=employee_name,
                department=department,
                job_level=job_level,
            )
            topic = "TD_STANDARD"
        else:
            result = talent_development_tool.run_competency_profile(
                db, message, employee_name=employee_name, department=department
            )
            topic = "TD_COMPETENCY"
    finally:
        db.close()
    return {
        "result": result,
        "result_topic": topic,
        "core_module": "talent_development",
    }


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
    """人力资源规划：编制 / 供需预测 / 离职风险。"""
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
            "我是组织发展与人才发展 Agent，目前可以做这些事：\n"
            "核心域 · 组织发展：\n"
            "  1. 组织架构与编制总览（层级深度、管理幅度、编制达成）\n"
            "  2. 组织效能与人效分析（人均产出、人工成本率、人效排名）\n"
            "  3. 岗位职级体系（金字塔分布、晋升率、职级拥堵）\n"
            "  4. 组织变革模拟（合并 / 拆分 / 扩编 / 缩编的影响与成本）\n"
            "核心域 · 人才发展：\n"
            "  5. 能力画像与差距（个人逐项 / 部门短板）\n"
            "  6. 任职资格匹配度（四维度加权比对）\n"
            "  7. 人才池视图（分层规模、在池流动与活跃度）\n"
            "  8. 发展项目跟踪（覆盖率、完成率、满意度、人均投入）\n"
            "  9. 导师制运行（配对、带教频次、导师负荷）\n"
            "HRIS 六大支撑模块：\n"
            "  10. 招聘管理：简历筛选、定 Offer、面试安排、招聘漏斗\n"
            "  11. 薪酬与福利：薪资公平性、调薪模拟、福利覆盖\n"
            "  12. 绩效管理：目标达成、评价偏差、强制分布、改进计划\n"
            "  13. 员工关系管理：假期、考勤、关系事件、敬业度\n"
            "  14. 培训与开发：培训总览、必修合规、课程推荐\n"
            "  15. 人力资源规划：编制达成、供需预测、离职风险\n"
            "请告诉我你想先看哪一个，以及部门或考核周期。"
        )
    return {"answer": answer, "llm_used": llm_used}


def generate_answer(state: AgentState) -> dict:
    """用大模型解释真实计算结果；模型不可用时回退到模板输出。"""
    result = state.get("result")
    topic = state.get("result_topic") or state.get("active_topic") or ""

    # 没有工具结果：只确认条件更新
    if not result:
        conditions = {
            k: state.get(k)
            for k in ("department", "period", "job_level", "employee_name")
            if state.get(k)
        }
        hint = f"（当前条件：{conditions}）" if conditions else ""
        return {
            "answer": f"已更新查询条件{hint}。请告诉我下一步要做什么，"
            "例如“看一下组织架构”“分析各部门人效”“看一下人才池”。"
        }

    if result.get("error"):
        return {"answer": result["error"]}

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
    if state.get("request_type") == "CHAT":
        return "chat"
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
        "ORG_DEV": "org_dev",
        "TALENT_DEV": "talent_dev",
        "HRIS": "decide_hris_module",
    }
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
    graph.add_node("org_dev", org_dev_node)
    graph.add_node("talent_dev", talent_dev_node)
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
            "chat": "chat",
        },
    )

    graph.add_conditional_edges(
        "extract_info",
        route_by_topic,
        {
            "org_dev": "org_dev",
            "talent_dev": "talent_dev",
            "decide_hris_module": "decide_hris_module",
            "generate_answer": "generate_answer",
        },
    )

    # HRIS 二级路由：一个 deciding 节点 → 六个具体业务节点
    graph.add_conditional_edges(
        "decide_hris_module",
        route_hris_module,
        dict(HRIS_MODULES),
    )

    for node in ("org_dev", "talent_dev"):
        graph.add_edge(node, "generate_answer")
    for node in HRIS_MODULES.values():
        graph.add_edge(node, "generate_answer")

    graph.add_edge("generate_answer", END)
    graph.add_edge("chat", END)

    return graph.compile(checkpointer=get_checkpointer())
