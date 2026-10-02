"""业务计算 Tool 测试（不依赖大模型）。

用法：python test_tool.py
验证九宫格定位、继任覆盖、梯队供给比、IDP 生成、组织诊断的正确性。
"""

from app.config.database import SessionLocal
from app.services import (
    diagnosis_service,
    idp_service,
    succession_service,
    talent_review_service,
)


def main():
    db = SessionLocal()
    try:
        print("=" * 60)
        print("1. 人才盘点九宫格")
        print("=" * 60)
        review = talent_review_service.build_talent_review(db)
        print(f"周期：{review['period']}  参与人数：{review['total']}")
        print(f"高潜占比：{round(review['high_potential_ratio'] * 100, 1)}%")
        print(f"明星人才：{review['star_talent']}")
        total_in_grid = sum(c["count"] for row in review["grid_matrix"] for c in row)
        print(f"九宫格人数合计校验：{total_in_grid}（应等于 {review['total']}）")
        assert total_in_grid == review["total"], "九宫格人数不一致"

        print()
        print("=" * 60)
        print("2. 关键岗位继任地图")
        print("=" * 60)
        succession = succession_service.build_succession_map(db)
        cov = succession["coverage"]
        print(
            f"关键岗位 {cov['total']} 个，覆盖率 {round(cov['coverage_rate'] * 100, 1)}%，"
            f"立即就绪率 {round(cov['ready_now_rate'] * 100, 1)}%，平均深度 {cov['avg_depth']}"
        )
        print(f"风险岗位 {len(succession['risk_positions'])} 个")
        for pos in succession["risk_positions"][:3]:
            print(f"  - {pos['title']}：{pos['risk_reason']}")

        print()
        print("=" * 60)
        print("3. 人才梯队")
        print("=" * 60)
        pipeline = succession_service.build_talent_pipeline(db)
        print("职级分布：", pipeline["level_distribution"])
        for p in pipeline["pipeline"]:
            print(
                f"  {p['from_level']} → {p['to_level']}：{p['supply']}/{p['demand']}"
                f" = {p['supply_ratio']}，{p['health']}"
            )
        print("结论：")
        for c in pipeline["conclusion"]:
            print(f"  - {c}")

        print()
        print("=" * 60)
        print("4. 个人发展计划 IDP")
        print("=" * 60)
        name = review["employees"][0]["name"]
        idp = idp_service.build_idp(db, name=name)
        print(f"员工：{idp['employee']['name']} ｜ 九宫格：{idp['grid_name']}")
        print(f"能力差距 {idp['summary']['gap_count']} 项，行动 {idp['summary']['action_count']} 项")
        print(f"70-20-10 投入：{idp['summary']['by_70_20_10']}")
        for item in idp["plan"][:5]:
            print(f"  - [{item['bucket']}] {item['competency']}｜{item['action_name']}")

        print()
        print("=" * 60)
        print("5. 组织诊断")
        print("=" * 60)
        diag = diagnosis_service.build_org_diagnosis(db)
        print(f"组织健康分：{diag['org_health_score']}（{diag['org_health_level']}）")
        for d in diag["departments"]:
            print(
                f"  - {d['department']}：{d['health_score']}（{d['health_level']}）"
                f"，问题 {len(d['issues'])} 项"
            )
        print(f"最需要关注的部门：{diag['worst_department']}")

        print()
        print("全部 Tool 测试通过。")
    finally:
        db.close()


if __name__ == "__main__":
    main()
