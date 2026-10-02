"""ATS 业务测试：简历筛选、智能定薪、漏斗、面试安排。

用法：python test_ats.py
"""

from app.config.database import SessionLocal
from app.services import ats_service


def main():
    db = SessionLocal()
    try:
        print("=" * 60)
        print("1. 招聘漏斗")
        print("=" * 60)
        funnel = ats_service.recruitment_funnel(db)
        print(f"收到 {funnel['received']} 份，活跃 {funnel['active']}，"
              f"淘汰 {funnel['rejected']}，已入职 {funnel['hired']}")
        print("转化率：", funnel["conversion_rates"])

        print()
        print("=" * 60)
        print("2. 简历筛选：高级前端开发工程师")
        print("=" * 60)
        result = ats_service.screen_for_job(db, 1)
        print(f"评估 {result['total']} 名，分档：{result['tier_summary']}")
        for r in result["ranking"][:5]:
            print(
                f"  {r['tier']:<14} {r['name']:<6} "
                f"综合 {r['overall_score']:<5} 技能 {r['skill_score']:<5} "
                f"命中 {r['skill_matched']}/{r['skill_total']}"
            )

        print()
        print("=" * 60)
        print("3. 智能定薪")
        print("=" * 60)
        for cand_name in ["曹聪", "林俊"]:
            offer = ats_service.suggest_offer(db, cand_name, 1)
            print(
                f"{cand_name} → 高级前端开发工程师："
                f"base ¥{offer['suggested_base']:,}, 奖金 ¥{offer['suggested_bonus']:,}, "
                f"股权 ¥{offer['suggested_equity']:,}, 总包 ¥{offer['total_package']:,}, "
                f"compa-ratio {offer['compa_ratio']}"
            )

        print()
        print("=" * 60)
        print("4. 面试安排推荐")
        print("=" * 60)
        from app.models import JobPost
        from sqlalchemy import select

        job = db.execute(
            select(JobPost).where(JobPost.title == "高级后端开发工程师")
        ).scalars().first()
        interviewers = ats_service.recommend_interviewers(db, job)
        for i in interviewers:
            print(f"  [{i['role']}] {i['name']}（{i['position_title']} · {i['job_level']}）")

        slots = ats_service.propose_interview_slots(job)
        print(f"推荐时段（前 3 个）：")
        for s in slots[:3]:
            print(f"  - {s['date']} {s['time']}（{s['mode']}）")

        print()
        print("全部 ATS 测试通过。")
    finally:
        db.close()


if __name__ == "__main__":
    main()