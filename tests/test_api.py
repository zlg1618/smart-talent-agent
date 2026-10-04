"""API 端点冒烟测试。"""

CORE_ENDPOINTS = [
    "/api/core/modules",
    "/api/core/organization-development/structure",
    "/api/core/organization-development/structure?department=技术中心",
    "/api/core/organization-development/effectiveness",
    "/api/core/organization-development/job-architecture",
    "/api/core/organization-development/change",
    "/api/core/organization-development/change?change_type=合并",
    "/api/core/organization-development/diagnosis",
    "/api/core/organization-development/diagnosis?framework=seven_s",
    "/api/core/organization-development/strategy",
    "/api/core/organization-development/culture",
    "/api/core/talent-development/competency",
    "/api/core/talent-development/competency?department=技术中心",
    "/api/core/talent-development/standard-match",
    "/api/core/talent-development/standard-match?department=产品部",
    "/api/core/talent-development/review",
    "/api/core/talent-development/review?department=技术中心",
    "/api/core/talent-development/competency-model",
    "/api/core/talent-development/succession",
    "/api/core/talent-development/pool",
    "/api/core/talent-development/program",
    "/api/core/talent-development/idp",
    "/api/core/talent-development/mentorship",
    "/api/core/talent-development/placement",
]

HRIS_ENDPOINTS = [
    "/api/hris/modules",
    "/api/hris/recruitment/funnel",
    "/api/hris/compensation/compa-ratio",
    "/api/hris/performance/goals",
    "/api/hris/employee-relations/engagement",
    "/api/hris/learning/overview",
    "/api/hris/workforce/headcount",
    "/api/hris/workforce/attrition-risk",
    "/api/integrations/backends",
]


def test_root_and_ui(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "smart-talent-agent"
    assert body["ui"] == "/ui/"

    ui = client.get("/ui/")
    assert ui.status_code == 200
    assert "Smart Talent Agent" in ui.text


def test_health(client):
    assert client.get("/api/health").status_code == 200


def test_core_endpoints(client):
    for url in CORE_ENDPOINTS:
        r = client.get(url)
        assert r.status_code == 200, f"{url} -> {r.status_code}"
        body = r.json()
        assert "conclusion" in body or "modules" in body, f"{url} 缺少结论字段"


def test_hris_endpoints(client):
    for url in HRIS_ENDPOINTS:
        assert client.get(url).status_code == 200, url


def test_core_module_registry(client):
    r = client.get("/api/core/modules").json()
    keys = {m["key"] for m in r["modules"]}
    assert keys == {"organization_development", "talent_development"}


def test_deleted_modules_are_gone(client):
    """上一版已下线的顶层模块必须不可访问。"""
    for url in ("/api/talent", "/api/succession", "/api/idp", "/api/diagnosis"):
        assert client.get(url).status_code == 404, f"{url} 仍然存在"
