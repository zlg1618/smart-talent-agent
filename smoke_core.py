"""核心双域 + HRIS 六模块端点冒烟测试。"""

from fastapi.testclient import TestClient

from app.config.database import init_db
from app.main import app

init_db()
client = TestClient(app)

CASES = [
    # 核心域 · 组织发展
    ("GET", "/api/core/modules", None, "核心双域清单"),
    ("GET", "/api/core/organization-development/structure", None, "组织架构"),
    ("GET", "/api/core/organization-development/structure?department=技术中心", None, "架构(部门)"),
    ("GET", "/api/core/organization-development/effectiveness", None, "组织效能"),
    ("GET", "/api/core/organization-development/job-architecture", None, "职级体系"),
    ("GET", "/api/core/organization-development/change", None, "组织变革"),
    ("GET", "/api/core/organization-development/change?change_type=合并", None, "变革(合并)"),
    # 核心域 · 人才发展
    ("GET", "/api/core/talent-development/competency", None, "能力差距(全员)"),
    ("GET", "/api/core/talent-development/competency?department=技术中心", None, "能力(部门)"),
    ("GET", "/api/core/talent-development/standard-match", None, "任职资格匹配"),
    ("GET", "/api/core/talent-development/standard-match?department=产品部", None, "匹配(部门)"),
    ("GET", "/api/core/talent-development/pool", None, "人才池"),
    ("GET", "/api/core/talent-development/program", None, "发展项目"),
    ("GET", "/api/core/talent-development/mentorship", None, "导师制"),
    # HRIS
    ("GET", "/api/hris/modules", None, "HRIS 模块清单"),
    ("GET", "/api/hris/workforce/headcount", None, "编制审查"),
    ("GET", "/api/hris/workforce/attrition-risk", None, "离职风险"),
    ("GET", "/api/hris/compensation/compa-ratio", None, "薪酬公平性"),
    ("GET", "/api/hris/learning/overview", None, "培训总览"),
    ("GET", "/api/hris/performance/goals", None, "绩效目标"),
    ("GET", "/api/hris/recruitment/funnel", None, "招聘漏斗"),
    ("GET", "/api/hris/employee-relations/engagement", None, "敬业度"),
    ("GET", "/api/integrations/backends", None, "适配器清单"),
    ("GET", "/", None, "根路径"),
]

# Agent 路由冒烟：核心双域 + HRIS 六模块各命中一次
ROUTE_CASES = [
    ("看一下公司组织架构和编制达成", "ORG_DEV", "organization_development", "OD_STRUCTURE"),
    ("分析各部门人效", "ORG_DEV", "organization_development", "OD_EFFECTIVENESS"),
    ("技术中心的职级体系健康吗", "ORG_DEV", "organization_development", "OD_ARCHITECTURE"),
    ("模拟一下组织变革方案", "ORG_DEV", "organization_development", "OD_CHANGE"),
    ("技术中心的能力差距在哪", "TALENT_DEV", "talent_development", "TD_COMPETENCY"),
    ("谁能晋升到下一职级", "TALENT_DEV", "talent_development", "TD_STANDARD"),
    ("看一下人才池", "TALENT_DEV", "talent_development", "TD_POOL"),
    ("发展项目完成得怎么样", "TALENT_DEV", "talent_development", "TD_PROGRAM"),
    ("导师制运行情况", "TALENT_DEV", "talent_development", "TD_MENTORSHIP"),
    ("帮我筛选一下候选人", "HRIS", None, "HRIS_RECRUITMENT_SCREEN"),
    ("薪酬公平性怎么样", "HRIS", None, "HRIS_COMPENSATION_COMPA"),
    ("绩效目标达成情况", "HRIS", None, "HRIS_PERFORMANCE_GOAL"),
    ("大家还有多少年假", "HRIS", None, "HRIS_ER_LEAVE_BALANCE"),
    ("培训覆盖率如何", "HRIS", None, "HRIS_LEARNING_OVERVIEW"),
    ("编制达成情况", "HRIS", None, "HRIS_WORKFORCE_HEADCOUNT"),
    ("谁有离职风险", "HRIS", None, "HRIS_WORKFORCE_ATTRITION"),
]


def test_routes():
    from app.services.ai_service import AIService

    service = AIService()
    ok = fail = 0
    for i, (message, intent, module, topic) in enumerate(ROUTE_CASES):
        try:
            resp = service.chat(thread_id=f"smoke-{i}", message=message)
        except Exception as exc:  # 路由异常直接算失败
            print(f"[FAIL] {message} -> {exc}")
            fail += 1
            continue
        got_intent = resp.get("request_type")
        result_topic = resp.get("result_topic")
        passed = got_intent == intent and (module is None or resp.get("core_module") == module)
        # 动作级分发是否正确，用 result_topic 校验
        if topic:
            passed = passed and result_topic == topic
        if passed and not resp.get("answer"):
            passed = False
        status = "OK " if passed else "FAIL"
        if passed:
            ok += 1
        else:
            fail += 1
        print(
            f"[{status}] {message[:18]:<20} intent={got_intent} "
            f"module={resp.get('core_module') or resp.get('hris_module')} "
            f"topic={result_topic}"
        )
    print(f"\nAgent 路由通过 {ok} / {len(ROUTE_CASES)}，失败 {fail}")
    return fail


def main():
    ok = fail = 0
    for method, url, _, label in CASES:
        resp = client.request(method, url)
        status = "OK " if resp.status_code == 200 else "FAIL"
        if resp.status_code == 200:
            ok += 1
        else:
            fail += 1
        print(f"[{status}] {resp.status_code} {label:<16} {url}")
    print(f"\n端点通过 {ok} / {len(CASES)}，失败 {fail}")
    return fail + test_routes()


if __name__ == "__main__":
    raise SystemExit(main())
