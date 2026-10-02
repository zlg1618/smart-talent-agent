"""结果格式化。

大模型不可用时使用这里的模板输出，保证任何环境下都有可读结果。
"""

READINESS_LABEL = {
    "ready_now": "立即就绪",
    "ready_1y": "1 年内",
    "ready_2y": "2 年内",
    "not_ready": "未就绪",
}


def _pct(value: float) -> str:
    return f"{round(value * 100, 1)}%"


def format_talent_review(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无盘点结果")

    lines = [
        f"人才盘点九宫格 · {result['period']} · {result['department']} · {result['job_level']}",
        f"参与盘点 {result['total']} 人，高潜占比 {_pct(result['high_potential_ratio'])}",
        "",
        f"{'':<8}{'低绩效':<14}{'中绩效':<14}{'高绩效':<14}",
    ]

    for row in result["grid_matrix"]:
        band = row[0]["grid_key"].split("-")[1] + "潜力"
        cells = [f"{c['grid_name']}({c['count']})" for c in row]
        lines.append(f"{band:<8}" + "".join(f"{c:<14}" for c in cells))

    if result["star_talent"]:
        lines.append("")
        lines.append("明星人才：" + "、".join(result["star_talent"][:10]))
    if result["high_potential"]:
        lines.append("高潜人才：" + "、".join(result["high_potential"][:15]))
    if result["risk_talent"]:
        lines.append("风险人才：" + "、".join(result["risk_talent"][:10]))

    lines.append("")
    lines.append("管理动作建议：")
    seen = set()
    for row in result["grid_matrix"]:
        for cell in row:
            if cell["count"] and cell["grid_name"] not in seen:
                seen.add(cell["grid_name"])
                lines.append(f"- {cell['grid_name']}（{cell['count']} 人）：{cell['action']}")

    return "\n".join(lines)


def format_succession(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无继任数据")

    cov = result["coverage"]
    lines = [
        f"关键岗位继任地图 · {result['department']}",
        f"关键岗位 {cov['total']} 个，继任覆盖 {cov['with_successor']} 个（{_pct(cov['coverage_rate'])}），"
        f"立即就绪覆盖 {_pct(cov['ready_now_rate'])}，平均候选深度 {cov['avg_depth']} 人",
        "",
    ]

    for pos in result["positions"]:
        names = "、".join(
            f"{s['name']}({READINESS_LABEL.get(s['readiness'], s['readiness'])})"
            for s in pos["successors"]
        )
        lines.append(
            f"- [{pos['criticality']}重要] {pos['title']}（{pos['department']}）"
            f"现任：{pos['incumbent'] or '空缺'}"
        )
        lines.append(f"    候选人：{names or '无'} ｜ 风险：{pos['risk_level']}（{pos['risk_reason']}）")

    if result["risk_positions"]:
        lines.append("")
        lines.append("需优先处理的岗位：")
        for pos in result["risk_positions"][:8]:
            lines.append(f"- {pos['title']}：{pos['risk_reason']}")

    return "\n".join(lines)


def format_pipeline(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无梯队数据")

    lines = [f"人才梯队分析 · {result['department']}", ""]

    for track in result.get("tracks", []):
        dist = "、".join(
            f"{d['job_level']} {d['count']} 人" for d in track["level_distribution"]
        )
        lines.append(f"{track['track']}职级分布：{dist}")
        lines.append("梯队供给比（下一级人数 / 上一级岗位数）：")
        for p in track["pipeline"]:
            lines.append(
                f"- {p['from_level']} → {p['to_level']}：{p['supply']} / {p['demand']} = "
                f"{p['supply_ratio']}，{p['health']}"
            )
        lines.append("")

    if not result.get("tracks"):
        dist = "、".join(
            f"{d['job_level']} {d['count']} 人" for d in result["level_distribution"]
        )
        lines.append(f"职级分布：{dist}")

    lines.append("")
    lines.append("结论：")
    for c in result["conclusion"]:
        lines.append(f"- {c}")

    return "\n".join(lines)


def format_idp(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无发展计划数据")

    emp = result["employee"]
    lines = [
        f"个人发展计划 · {emp['name']}（{emp['department']} · {emp['position_title']} · {emp['job_level']}）",
        f"九宫格定位：{result.get('grid_name') or '未知'}，人才类型：{result.get('talent_type') or '未知'}",
        "",
        "能力差距：",
    ]
    for g in result["gaps"]:
        lines.append(
            f"- {g['competency']}：现状 {g['current_level']} 级 / 目标 {g['required_level']} 级，差距 {g['gap']} 级"
        )

    lines.append("")
    lines.append(f"发展行动（遵循 {result['principle']}）：")
    for item in result["plan"]:
        hours = f"{item['duration_hours']} 小时" if item["duration_hours"] else "时长待定"
        lines.append(
            f"- [{item['bucket'] or '待补充'}] {item['competency']}｜{item['action_type']}："
            f"{item['action_name']}（{hours}）"
        )

    s = result["summary"]
    lines.append("")
    lines.append(
        f"合计 {s['action_count']} 项行动，投入 {s['total_hours']} 小时；"
        f"项目历练 {s['by_70_20_10']['70% 项目历练']} 小时，"
        f"导师辅导 {s['by_70_20_10']['20% 导师辅导']} 小时，"
        f"正式培训 {s['by_70_20_10']['10% 正式培训']} 小时"
    )
    if result.get("grid_action"):
        lines.append(f"管理建议：{result['grid_action']}")

    return "\n".join(lines)


def format_diagnosis(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无组织诊断数据")

    lines = [
        f"组织诊断 · {result['period']} · {result['department']}",
        f"组织健康分 {result['org_health_score']}（{result['org_health_level']}），"
        f"覆盖 {result['department_count']} 个部门，{result['alert_issue_count']} 项预警",
        "",
    ]
    for d in result["departments"]:
        m = d["metrics"]
        lines.append(
            f"- {d['department']}：健康分 {d['health_score']}（{d['health_level']}）｜"
            f"在职 {d['headcount']} 人，离职率 {_pct(m['turnover_rate'])}，"
            f"平均绩效 {m['avg_performance']}，高潜占比 {_pct(m['high_potential_ratio'])}，"
            f"管理幅度 {m['span_of_control']}"
        )
        for issue in d["issues"]:
            lines.append(f"    · [{issue['level']}] {issue['name']}：{issue['detail']}")
            lines.append(f"      建议：{issue['suggestion']}")

    if result["top_issues"]:
        lines.append("")
        lines.append("优先处理事项：")
        for issue in result["top_issues"]:
            lines.append(f"- {issue['name']}：{issue['suggestion']}")

    return "\n".join(lines)


def format_ats_screen(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无简历筛选结果")

    if "ranking" in result:
        job = result["job"]
        lines = [
            f"简历筛选 · {job['title']}（{job['department']}）",
            f"关键技能：{'、'.join(job['required_skills'])}",
            f"预算：{job['salary_range'][0]} – {job['salary_range'][1]}",
            f"共评估 {result['total']} 名候选人，分档统计：{result['tier_summary']}",
            "",
            "Top 排名：",
        ]
        for r in result["ranking"]:
            lines.append(
                f"- [{r['tier']}] {r['name']}（{r['current_title']} @ {r['current_company']}）"
                f"综合分 {r['overall_score']}｜技能 {r['skill_score']}（{r['skill_matched']}/{r['skill_total']}）"
                f"｜经验 {r['exp_score']}｜学历 {r['degree_score']}"
            )
            if r.get("matched_skills"):
                lines.append(f"    命中：{'、'.join(r['matched_skills'])}")
            if r.get("missing_skills"):
                lines.append(f"    缺口：{'、'.join(r['missing_skills'])}")
        return "\n".join(lines)

    c = result["candidate"]
    job = result["job"]
    s = result
    lines = [
        f"简历评估 · {c['name']} → {job['title']}（{job['department']}）",
        f"现职：{c['current_title']} @ {c['current_company']}，经验 {c['years_exp']} 年，"
        f"学历 {c['degree']}",
        f"期望薪资：{c['expected_salary'][0]} – {c['expected_salary'][1]}",
        "",
        f"综合分：{s['overall_score']} → 等级：{s['tier']}",
        f"技能：{s['skill_score']}（命中 {s['skill_matched']}/{s['skill_total']}）",
        f"经验：{s['exp_score']}｜学历：{s['degree_score']}｜期望薪资：{s['salary_score']}｜当前职级：{s['title_score']}",
    ]
    if s.get("matched_skills"):
        lines.append(f"命中技能：{'、'.join(s['matched_skills'])}")
    if s.get("missing_skills"):
        lines.append(f"缺口技能：{'、'.join(s['missing_skills'])}")
    return "\n".join(lines)


def format_ats_offer(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无 Offer 建议")

    lines = [
        f"Offer 建议 · {result['candidate']['name']} → {result['job']['title']}",
        f"评级 {result['score']['tier']}（综合分 {result['score']['overall_score']}）",
        "",
        f"建议 base：¥{result['suggested_base']:,}",
        f"建议奖金：¥{result['suggested_bonus']:,}（{round(result['bonus_rate']*100)}% 比例）",
        f"建议股权/长期激励：¥{result['suggested_equity']:,}",
        f"总包：¥{result['total_package']:,}",
        f"compa-ratio：{result['compa_ratio']}（岗位中位值 ¥{(result['job']['salary_range'][0]+result['job']['salary_range'][1])//2:,}）",
        f"候选人期望中位：¥{result['expected_mid']:,} → {result['expected_warning']}",
        "",
        f"决策依据：{result['rationale']}",
    ]
    if "saved_offer_id" in result:
        lines.append(f"已落库，Offer ID：{result['saved_offer_id']}")
    return "\n".join(lines)


def format_ats_funnel(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无漏斗数据")
    sc = result["stage_counts"]
    cr = result["conversion_rates"]
    lines = [
        f"招聘漏斗 · {result['department']}",
        f"收到申请 {result['received']} 份，活跃 {result['active']}，淘汰 {result['rejected']}，已入职 {result['hired']}",
        "",
        "各阶段：",
    ]
    for k, v in sc.items():
        lines.append(f"- {k}：{v} 人")
    lines.append("")
    lines.append("转化率：")
    for k, v in cr.items():
        lines.append(f"- {k}：{v}%")
    return "\n".join(lines)


def format_ats_interview(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无面试建议")
    job = result["job"]
    lines = [
        f"面试安排建议 · {job['title']}（{job['department']}）",
        "",
        "推荐面试官：",
    ]
    for i in result["recommended_interviewers"]:
        lines.append(
            f"- [{i['role']}] {i['name']}（{i['position_title']} · {i['job_level']}）"
        )
    lines.append("")
    lines.append(f"可选时段（{result['total_slots']} 个，前 6 个）：")
    for s in result["available_slots"]:
        lines.append(f"- {s['date']} {s['time']}（{s['mode']}）")
    return "\n".join(lines)


def format_hr_leave_balance(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无年假信息")
    emp = result["employee"]
    lines = [
        f"年假余额 · {emp['name']}（{emp['department']}）",
        f"入职日期 {emp['hire_date']}，工龄 {emp['years_of_service']} 年",
        f"法定年假 {result['annual_entitlement']} 天，已用 {result['annual_used']} 天，剩余 {result['annual_remaining']} 天",
    ]
    if result.get("pending_requests"):
        lines.append("待审批申请：")
        for p in result["pending_requests"]:
            lines.append(
                f"- 申请 #{p['id']}：{p['leave_type']} {p['start_date']} 至 {p['end_date']} 共 {p['days']} 天（{p['reason']}）"
            )
    return "\n".join(lines)


def format_hr_leave_request(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "请假提交失败")
    lines = [
        f"请假申请已提交",
        f"员工：{result['employee_name']}",
        f"类型：{result['leave_type']}",
        f"时间：{result['start_date']} 至 {result['end_date']}（{result['days']} 天）",
        f"状态：{result['status']}（申请 ID：{result['request_id']}）",
    ]
    if result.get("warning"):
        lines.append(f"提示：{result['warning']}")
    return "\n".join(lines)


def format_hr_leave_approve(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "审批失败")
    return f"请假申请 #{result['request_id']}：{result['status']}（审批人：{result['approver']}）"


def format_hr_attendance(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无考勤数据")
    emp = result["employee"]
    lines = [
        f"考勤汇总 · {emp['name']}（{emp['department']}）",
        f"区间：{result['range']['start']} 至 {result['range']['end']}",
        f"总记录 {result['days_total']} 天，出勤 {result['workdays']} 天，缺勤 {result['absent_days']} 天，迟到 {result['late_count']} 次",
        f"出勤率：{result['attendance_rate']}%，累计工时 {result['total_hours']} 小时，日均 {result['avg_hours']} 小时",
    ]
    return "\n".join(lines)


def format_hr_pending(result: dict) -> str:
    if not result:
        return "暂无待审批申请"
    pending = result.get("pending", [])
    if not pending:
        return "当前没有待审批的请假申请"
    lines = [f"待审批请假申请（{len(pending)} 条）："]
    for p in pending:
        lines.append(
            f"- #{p['request_id']} {p['employee_name']}（{p['department']}）："
            f"{p['leave_type']} {p['start_date']} 至 {p['end_date']} 共 {p['days']} 天（{p['reason']}）"
        )
    return "\n".join(lines)


FORMATTERS = {
    "TALENT_REVIEW": format_talent_review,
    "SUCCESSION": format_succession,
    "PIPELINE": format_pipeline,
    "IDP": format_idp,
    "DIAGNOSIS": format_diagnosis,
    "ATS_SCREEN": format_ats_screen,
    "ATS_OFFER": format_ats_offer,
    "ATS_FUNNEL": format_ats_funnel,
    "ATS_INTERVIEW": format_ats_interview,
    "HR_LEAVE_BALANCE": format_hr_leave_balance,
    "HR_LEAVE_REQUEST": format_hr_leave_request,
    "HR_LEAVE_APPROVE": format_hr_leave_approve,
    "HR_ATTENDANCE": format_hr_attendance,
    "HR_LEAVE_PENDING": format_hr_pending,
}

# CHAT 也会经过 generate_answer；为安全起见提供兜底
FORMATTERS.setdefault("CHAT", lambda r: r if isinstance(r, str) else str(r))


def format_result(topic: str, result: dict) -> str:
    formatter = FORMATTERS.get(topic)
    if not formatter:
        return str(result)
    return formatter(result)
