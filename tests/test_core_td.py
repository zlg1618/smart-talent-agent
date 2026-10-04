"""核心域 · 人才发展（TD）计算测试。"""

from app.services import talent_development_service as td


def test_talent_review_grid_consistency(db):
    r = td.talent_review(db)
    assert r["total"] > 0
    # 九宫格各格人数之和必须等于参与人数
    grid_sum = sum(c["count"] for row in r["grid_matrix"] for c in row)
    assert grid_sum == r["total"], f"九宫格合计 {grid_sum} != 参与 {r['total']}"
    assert r["high_potential_count"] == len(
        [p for p in r["people"] if p["is_high_potential"]]
    )


def test_talent_review_360_cognition(db):
    r = td.talent_review(db)
    if not r["review_360"]:
        return  # 没有 360 数据时跳过
    for item in r["review_360"]:
        if item["cognition_gap"] is None:
            continue
        gap = abs(item["cognition_gap"])
        if gap >= 0.5:
            assert item["cognition"] in ("自评偏高", "自评偏低")
        else:
            assert item["cognition"] == "认知一致"


def test_competency_model(db):
    r = td.competency_model(db)
    assert r["total_competencies"] > 0
    assert r["total_level_definitions"] > 0
    assert 0 <= r["requirement_coverage"] <= 1
    one = td.competency_model(db, job_family="技术", job_level="P7")
    assert one["job_family"] == "技术"


def test_talent_standard_match(db):
    r = td.talent_standard_match(db)
    assert r["total"] > 0
    assert 0 <= r["avg_match_rate"] <= 1
    for p in r["people"]:
        assert 0 <= p["match_rate"] <= 1
        assert p["match_label"] in ("完全胜任", "基本胜任", "尚有差距", "差距明显")


def test_succession_plan(db):
    r = td.succession_plan(db)
    assert r["total"] > 0
    assert 0 <= r["coverage_rate"] <= 1
    assert 0 <= r["ready_now_rate"] <= 1
    # 立即就绪率不可能高于覆盖率
    assert r["ready_now_rate"] <= r["coverage_rate"]
    for p in r["positions"]:
        assert p["advice"]


def test_talent_pool(db):
    r = td.talent_pool_view(db)
    assert r["total_pools"] > 0
    for p in r["pools"]:
        assert p["in_pool"] + p["observing"] + p["exited"] == p["total"]
        assert p["health"] in ("活跃", "正常", "流失偏高")


def test_development_program(db):
    r = td.development_program_tracking(db)
    assert r["total"] > 0
    for p in r["programs"]:
        assert 0 <= p["completion_rate"] <= 1
        assert p["grade"] in ("效果良好", "基本达标", "需改进")


def test_idp_view(db):
    r = td.idp_view(db)
    assert r["total_people"] > 0
    assert r["total_actions"] > 0
    assert set(r["by_70_20_10"]) == {"70", "20", "10"}
    assert 0 <= r["overall_completion_rate"] <= 1


def test_mentorship(db):
    r = td.mentorship_view(db)
    assert r["total_pairs"] > 0
    assert r["mentor_count"] > 0
    for p in r["pairs"]:
        assert p["stage"] in ("已完成", "推进中", "刚起步")


def test_talent_placement_groups(db):
    r = td.talent_placement(db)
    assert r["total"] > 0
    labels = {g["suggestion"] for g in r["groups"]}
    assert labels == {"晋升提拔", "重点保留", "激活换岗", "调整或淘汰", "持续观察"}
    grouped = sum(g["count"] for g in r["groups"])
    assert grouped == r["total"]
    # 晋升建议的人必须都满足匹配度门槛
    promote = next(g for g in r["groups"] if g["suggestion"] == "晋升提拔")
    for p in promote["people"]:
        assert p["match_rate"] >= 0.75
