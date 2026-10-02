"""HRIS 事务测试：年假、请假提交与审批、考勤汇总。

用法：python test_hr.py
"""

from datetime import date, timedelta

from sqlalchemy import select

from app.config.database import SessionLocal
from app.models import Employee
from app.services import hr_transaction_service


def main():
    db = SessionLocal()
    try:
        emp = db.execute(select(Employee).limit(1)).scalars().first()
        print("=" * 60)
        print(f"员工：{emp.name}（{emp.department}）")
        print("=" * 60)

        print()
        print("1. 年假余额")
        balance = hr_transaction_service.get_leave_balance(db, emp.name)
        print(
            f"工龄 {balance['employee']['years_of_service']} 年，"
            f"法定 {balance['annual_entitlement']} 天，"
            f"已用 {balance['annual_used']} 天，"
            f"剩余 {balance['annual_remaining']} 天"
        )

        print()
        print("2. 提交请假申请")
        start = date.today() + timedelta(days=10)
        end = start + timedelta(days=2)
        req = hr_transaction_service.submit_leave_request(
            db, emp.name, "annual", start, end, "家庭旅行"
        )
        print(
            f"申请 #{req['request_id']}：{req['leave_type']} {req['start_date']} 至 {req['end_date']}"
            f"（{req['days']} 天），状态 {req['status']}"
        )

        print()
        print("3. 审批请假")
        approved = hr_transaction_service.approve_leave(
            db, req["request_id"], "叶一鸣", approve=True
        )
        print(f"审批结果：{approved}")

        print()
        print("4. 审批后再次查询余额")
        balance2 = hr_transaction_service.get_leave_balance(db, emp.name)
        print(
            f"已用 {balance2['annual_used']} 天，剩余 {balance2['annual_remaining']} 天"
        )

        print()
        print("5. 考勤汇总（默认最近 30 天）")
        summary = hr_transaction_service.get_attendance_summary(db, emp.name)
        print(
            f"出勤 {summary['workdays']} 天，迟到 {summary['late_count']} 次，"
            f"缺勤 {summary['absent_days']} 天，出勤率 {summary['attendance_rate']}%"
        )

        print()
        print("6. 待审批申请列表")
        pending = hr_transaction_service.list_pending_leaves(db)
        print(f"共 {len(pending)} 条")
        for p in pending[:3]:
            print(
                f"  #{p['request_id']} {p['employee_name']}（{p['department']}）："
                f"{p['leave_type']} {p['start_date']} – {p['end_date']}（{p['days']} 天）"
            )

        print()
        print("全部 HRIS 事务测试通过。")
    finally:
        db.close()


if __name__ == "__main__":
    main()