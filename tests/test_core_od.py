"""核心域 · 组织发展（OD）计算测试。"""

from app.services import organization_service as od


def test_org_structure_counts(db):
    r = od.org_structure(db)
    assert r["total_units"] > 0
    assert r["total_planned"] >= r["total_actual"]
    assert 0 <= r["overall_fill_rate"] <= 1.5
    assert r["max_depth"] >= 1
    assert "basis" in r


def test_org_structure_control_design(db):
    """架构与管控设计：三种分布必须有值。"""
    r = od.org_structure(db)
    assert r["org_model_distribution"], "缺少组织模式分布"
    assert r["control_mode_distribution"], "缺少管控模式分布"
    assert r["authority_distribution"], "缺少集权分权分布"
    assert all(u["control_mode"] for u in r["units"])


def test_org_effectiveness_ranking(db):
    r = od.org_effectiveness(db)
    assert r["total"] > 0
    assert r["overall_output_per_head"] > 0
    assert len(r["ranking"]) == r["total"]
    # 排名必须按人均产出降序
    values = [x["output_per_head"] for x in r["ranking"]]
    assert values == sorted(values, reverse=True)


def test_job_architecture_shape(db):
    r = od.job_architecture(db)
    assert r["total_levels"] > 0
    for f in r["by_department"]:
        assert f["base"] + f["mid"] + f["senior"] == f["total"]
        assert f["shape"] in ("腰部拥堵", "基层偏重", "倒金字塔", "结构均衡")


def test_org_diagnosis_frameworks(db):
    r = od.org_diagnosis(db)
    assert r["org_health_score"] > 0
    assert r["health_dimensions"], "缺少健康度维度"
    assert r["scan_total"] > 0
    for fw in ("seven_s", "six_box", "five_dim"):
        one = od.org_diagnosis(db, framework=fw)
        assert one["scan_total"] > 0, f"{fw} 框架无扫描数据"


def test_strategy_decode_levels(db):
    r = od.strategy_decode(db)
    assert r["total"] > 0
    assert r["company_goals"], "缺少公司级目标"
    assert 0 <= r["weighted_achievement"] <= 1.5
    for g in r["lagging_goals"]:
        assert g["flag"] in ("有风险", "严重滞后")


def test_org_culture_dimensions(db):
    r = od.org_culture(db)
    assert r["total_dimensions"] > 0
    assert 1 <= r["overall_score"] <= 5
    for d in r["dimensions"]:
        assert d["advice"]


def test_org_change_stage_and_resistance(db):
    r = od.org_change_simulation(db)
    assert r["total"] > 0
    assert r["stage_distribution"], "缺少变革阶段分布"
    for p in r["plans"]:
        assert p["stage"] in ("宣贯", "试点", "推广", "固化")
        assert p["resistance"] in ("高", "中", "低")
        assert p["resistance_advice"]
