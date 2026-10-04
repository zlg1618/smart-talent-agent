"""Agent 意图与动作路由测试。"""

from app.services.ai_service import AIService

# (问法, 期望意图, 期望核心域/模块, 期望动作 topic)
CASES = [
    ("看一下公司组织架构和编制达成", "ORG_DEV", "organization_development", "OD_STRUCTURE"),
    ("分析各部门人效", "ORG_DEV", "organization_development", "OD_EFFECTIVENESS"),
    ("技术中心的职级体系健康吗", "ORG_DEV", "organization_development", "OD_ARCHITECTURE"),
    ("模拟一下组织变革方案", "ORG_DEV", "organization_development", "OD_CHANGE"),
    ("做一次组织诊断", "ORG_DEV", "organization_development", "OD_DIAGNOSIS"),
    ("战略解码做得怎么样", "ORG_DEV", "organization_development", "OD_STRATEGY"),
    ("公司文化氛围怎么样", "ORG_DEV", "organization_development", "OD_CULTURE"),
    ("技术中心的能力差距在哪", "TALENT_DEV", "talent_development", "TD_COMPETENCY"),
    ("谁能晋升到下一职级", "TALENT_DEV", "talent_development", "TD_STANDARD"),
    ("做一次人才盘点", "TALENT_DEV", "talent_development", "TD_REVIEW"),
    ("胜任力模型搭得怎么样", "TALENT_DEV", "talent_development", "TD_MODEL"),
    ("关键岗位继任情况", "TALENT_DEV", "talent_development", "TD_SUCCESSION"),
    ("看一下人才池", "TALENT_DEV", "talent_development", "TD_POOL"),
    ("发展项目完成得怎么样", "TALENT_DEV", "talent_development", "TD_PROGRAM"),
    ("IDP 进展如何", "TALENT_DEV", "talent_development", "TD_IDP"),
    ("导师制运行情况", "TALENT_DEV", "talent_development", "TD_MENTORSHIP"),
    ("有哪些人可以提拔", "TALENT_DEV", "talent_development", "TD_PLACEMENT"),
]


def test_core_routing():
    service = AIService()
    for i, (message, intent, module, topic) in enumerate(CASES):
        resp = service.chat(thread_id=f"pytest-{i}", message=message)
        assert resp["request_type"] == intent, f"{message} -> {resp['request_type']}"
        assert resp["core_module"] == module, f"{message} -> {resp['core_module']}"
        assert resp["result_topic"] == topic, f"{message} -> {resp['result_topic']}"
        assert resp["answer"], f"{message} 没有产出回答"


def test_hris_routing():
    service = AIService()
    cases = [
        ("帮我筛选一下候选人", "recruitment"),
        ("薪酬公平性怎么样", "compensation"),
        ("绩效目标达成情况", "performance"),
        ("大家还有多少年假", "employee_relations"),
        ("培训覆盖率如何", "learning"),
        ("编制达成情况", "workforce"),
    ]
    for i, (message, module) in enumerate(cases):
        resp = service.chat(thread_id=f"pytest-hris-{i}", message=message)
        assert resp["request_type"] == "HRIS", message
        assert resp["hris_module"] == module, f"{message} -> {resp['hris_module']}"


def test_multi_turn_condition_update():
    """改部门后必须按新条件重算。"""
    service = AIService()
    tid = "pytest-multiturn"
    service.chat(thread_id=tid, message="看一下组织架构")
    resp = service.chat(thread_id=tid, message="部门改成销售部")
    assert resp["conditions"]["department"] == "销售部"
    again = service.chat(thread_id=tid, message="重新看一下")
    assert "销售部" in (again["result"] or {}).get("department", "")


def test_chat_fallback():
    service = AIService()
    resp = service.chat(thread_id="pytest-chat", message="今天天气怎么样")
    assert resp["request_type"] == "CHAT"
    assert resp["answer"]
