"""HRIS 六大模块测试。

覆盖：
    招聘管理       简历筛选、Offer 定薪、面试安排、招聘漏斗
    薪酬与福利     compa-ratio、调薪模拟、福利覆盖、个人薪酬单
    绩效管理       目标达成、评价偏差、强制分布、改进计划
    员工关系管理   假期余额、考勤、关系事件、敬业度
    培训与开发     培训总览、必修合规、课程推荐、培训效果
    人力资源规划   编制审查、供需预测、离职风险

运行：python test_hris.py
"""

from app.config.database import SessionLocal
from app.services import (
    compensation_service,
    employee_relations_service,
    learning_service,
    performance_service,
    recruitment_service,
    workforce_service,
)

SEPARATOR = "=" * 66


def show(title: str, result: dict, keys: tuple[str, ...] = ()):
    print(f"\n{title}")
    if not result:
        print("  （无结果）")
        return
    if result.get("error"):
        print(f"  ERROR: {result['error']}")
        return
    for k in keys:
        if k in result:
            print(f"  {k}: {result[k]}")
    if result.get("conclusion"):
        print(f"  结论：{result['conclusion']}")


def main():
    db = SessionLocal()
    try:
        print(SEPARATOR)
        print("HRIS · 招聘管理")
        print(SEPARATOR)
        show(
            "简历筛选（高级前端开发工程师）",
            recruitment_service.screen_for_job(db, "高级前端开发工程师", top=5),
            ("total", "tier_summary"),
        )
        show(
            "Offer 定薪（曹聪 → 高级前端开发工程师）",
            recruitment_service.suggest_offer(db, "曹聪", "高级前端开发工程师"),
            ("suggested_base", "suggested_bonus", "suggested_equity",
             "total_package", "compa_ratio"),
        )
        show("招聘漏斗", recruitment_service.recruitment_funnel(db),
             ("received", "hired"))

        print(f"\n{SEPARATOR}")
        print("HRIS · 薪酬与福利")
        print(SEPARATOR)
        show("薪酬公平性", compensation_service.compa_ratio_analysis(db),
             ("employee_count", "avg_compa_ratio", "below_band_count", "above_band_count"))
        show("调薪预算模拟（5%）", compensation_service.salary_adjustment_simulation(db, budget_pct=5.0),
             ("budget_amount", "used_amount", "adjusted_count"))
        show("福利覆盖", compensation_service.benefits_analysis(db),
             ("plan_count", "avg_cost_per_head", "under_covered_count"))

        print(f"\n{SEPARATOR}")
        print("HRIS · 绩效管理")
        print(SEPARATOR)
        show("目标达成", performance_service.goal_achievement(db),
             ("goal_count", "employee_count", "avg_achievement"))
        show("评价偏差", performance_service.review_deviation(db),
             ("review_count", "avg_abs_gap", "big_gap_count"))
        show("强制分布校验", performance_service.distribution_check(db),
             ("total_reviewed", "deviation_count"))
        show("改进计划", performance_service.improvement_tracking(db),
             ("total", "ongoing", "passed", "failed"))

        print(f"\n{SEPARATOR}")
        print("HRIS · 员工关系管理")
        print(SEPARATOR)
        emp = db.execute(
            __import__("sqlalchemy").select(
                __import__("app.models", fromlist=["Employee"]).Employee
            ).limit(1)
        ).scalar()
        show(f"假期余额（{emp.name}）",
             employee_relations_service.get_leave_balance(db, emp.name))
        show("考勤汇总", employee_relations_service.get_attendance_summary(db, emp.name),
             ("workdays", "late_count", "attendance_rate"))
        show("关系事件", employee_relations_service.relation_case_analysis(db),
             ("total_cases", "open_cases", "overdue_cases"))
        show("敬业度", employee_relations_service.engagement_analysis(db),
             ("survey_count", "avg_score", "enps"))

        print(f"\n{SEPARATOR}")
        print("HRIS · 培训与开发")
        print(SEPARATOR)
        show("培训总览", learning_service.training_overview(db),
             ("employee_count", "training_coverage", "completion_rate", "total_hours"))
        show("必修合规", learning_service.mandatory_compliance(db),
             ("compliance_rate", "non_compliant_count"))
        show(f"课程推荐（{emp.name}）", learning_service.recommend_courses(db, emp.name),
             ("gap_count", "total_hours", "total_cost"))
        show("培训效果", learning_service.learning_effectiveness(db),
             ("course_count", "total_enrollments"))

        print(f"\n{SEPARATOR}")
        print("HRIS · 人力资源规划")
        print(SEPARATOR)
        show("编制审查", workforce_service.headcount_review(db),
             ("total_planned", "total_actual", "overall_fill_rate"))
        show("供需预测", workforce_service.supply_demand_forecast(db),
             ("total_net_demand", "total_internal_supply", "total_external_hire"))
        show("离职风险", workforce_service.attrition_risk_scan(db),
             ("scanned_count", "high_risk_count", "medium_risk_count"))
    finally:
        db.close()
    print(f"\n{SEPARATOR}")
    print("HRIS 六大模块测试完成")


if __name__ == "__main__":
    main()
