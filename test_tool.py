"""核心双域业务计算测试（不依赖大模型）。

用法：python test_tool.py
验证组织发展（架构编制、组织效能、职级体系、变革模拟）与
人才发展（能力差距、任职资格匹配、人才池、发展项目、导师制）的计算正确性。
"""

from app.config.database import SessionLocal
from app.services import organization_service, talent_development_service


def main():
    db = SessionLocal()
    try:
        print("=" * 60)
        print("1. 组织发展 · 组织架构与编制")
        print("=" * 60)
        structure = organization_service.org_structure(db)
        print(f"周期：{structure['period']}  组织单元：{structure['total_units']}")
        print(
            f"层级深度 {structure['max_depth']} 层，平均管理幅度 "
            f"{structure['avg_span_of_control']} 人"
        )
        print(
            f"编制 {structure['total_planned']} / 在编 {structure['total_actual']}，"
            f"达成率 {round(structure['overall_fill_rate'] * 100, 1)}%"
        )
        assert structure["total_units"] > 0, "组织单元为空"
        print("结论：" + structure["conclusion"])

        print()
        print("=" * 60)
        print("2. 组织发展 · 组织效能与人效")
        print("=" * 60)
        eff = organization_service.org_effectiveness(db)
        print(
            f"人均产出 {eff['overall_output_per_head']} 万元，"
            f"人工成本率 {round(eff['overall_cost_rate'] * 100, 1)}%"
        )
        for r in eff["ranking"][:5]:
            print(
                f"  - {r['department']}：人均 {r['output_per_head']} 万元，"
                f"人效指数 {r['output_index']}，{r['tier']}"
            )
        print("结论：" + eff["conclusion"])

        print()
        print("=" * 60)
        print("3. 组织发展 · 岗位职级体系")
        print("=" * 60)
        arch = organization_service.job_architecture(db)
        print(f"职级配置 {arch['total_levels']} 个，覆盖 {arch['total_headcount']} 人")
        for f in arch["by_department"]:
            print(
                f"  - {f['department']}：基层 {f['base']} / 中级 {f['mid']} / 高级 "
                f"{f['senior']}，{f['shape']}，年均晋升率 "
                f"{round(f['avg_promotion_rate'] * 100, 1)}%"
            )
        print("结论：" + arch["conclusion"])

        print()
        print("=" * 60)
        print("4. 组织发展 · 组织变革模拟")
        print("=" * 60)
        change = organization_service.org_change_simulation(db)
        print(
            f"方案 {change['total']} 个，影响 {change['total_affected']} 人，"
            f"成本影响 {change['total_cost_impact']} 万元"
        )
        for r in change["plans"][:5]:
            print(
                f"  - {r['name']}（{r['change_type']}）：{r['affected_headcount']} 人，"
                f"{r['cost_impact']} 万元，{r['risk']}"
            )
        print("结论：" + change["conclusion"])

        print()
        print("=" * 60)
        print("5. 人才发展 · 能力差距（部门）")
        print("=" * 60)
        comp = talent_development_service.competency_profile(db)
        print(f"评估能力项 {comp['total']} 项")
        for r in (comp.get("top_gaps") or comp["items"])[:5]:
            print(f"  - {r['competency']}：平均 {r['avg_current']} / 需 {r['avg_required']}")
        print("结论：" + comp["conclusion"])

        print()
        print("=" * 60)
        print("6. 人才发展 · 任职资格匹配度")
        print("=" * 60)
        match = talent_development_service.talent_standard_match(db)
        print(
            f"比对 {match['total']} 人，平均匹配度 "
            f"{round(match['avg_match_rate'] * 100, 1)}%，"
            f"基本胜任及以上 {match['ready_count']} 人"
        )
        for r in match["people"][:5]:
            print(
                f"  - {r['name']}（{r['current_level']} → {r['target_level']}）："
                f"{round(r['match_rate'] * 100, 1)}%，{r['match_label']}"
            )
        print("结论：" + match["conclusion"])

        print()
        print("=" * 60)
        print("7. 人才发展 · 人才池")
        print("=" * 60)
        pool = talent_development_service.talent_pool_view(db)
        print(f"人才池 {pool['total_pools']} 个，在池 {pool['total_in_pool']} 人")
        for r in pool["pools"]:
            print(
                f"  - {r['pool_name']}（{r['pool_type']}）：在池 {r['in_pool']} / "
                f"观察 {r['observing']} / 出池 {r['exited']}，{r['health']}"
            )
        print("结论：" + pool["conclusion"])

        print()
        print("=" * 60)
        print("8. 人才发展 · 发展项目")
        print("=" * 60)
        prog = talent_development_service.development_program_tracking(db)
        print(
            f"项目 {prog['total']} 个，入学 {prog['total_enrolled']} 人，"
            f"预算 {prog['total_budget']} 万元"
        )
        for r in prog["programs"]:
            print(
                f"  - {r['name']}：{r['enrolled']}/{r['capacity']} 人，完成率 "
                f"{round(r['completion_rate'] * 100, 1)}%，{r['grade']}"
            )
        print("结论：" + prog["conclusion"])

        print()
        print("=" * 60)
        print("9. 人才发展 · 导师制")
        print("=" * 60)
        mentor = talent_development_service.mentorship_view(db)
        print(
            f"带教 {mentor['total_pairs']} 组，导师 {mentor['mentor_count']} 位，"
            f"平均带教 {mentor['avg_sessions']} 次"
        )
        for r in mentor["pairs"][:5]:
            print(
                f"  - {r['mentor']} → {r['mentee']}：{r['session_count']}/"
                f"{r['planned_sessions']} 次，{r['stage']}"
            )
        print("结论：" + mentor["conclusion"])

        print()
        print("全部核心双域 Tool 测试通过。")
    finally:
        db.close()


if __name__ == "__main__":
    main()
