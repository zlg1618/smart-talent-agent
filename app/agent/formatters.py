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


def _yen(v) -> str:
    try:
        return f"¥{int(v):,}"
    except (TypeError, ValueError):
        return str(v)


def _pct(v) -> str:
    try:
        return f"{round(float(v) * 100, 1)}%"
    except (TypeError, ValueError):
        return str(v)


def _conclusion(result: dict) -> str:
    return result.get("conclusion") or ""


def format_compa(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无薪酬分析数据")
    lines = [
        f"薪酬公平性分析 · {result['department']} · {result['job_level']}",
        f"参与比对 {result['employee_count']} 人，平均 compa-ratio "
        f"{result['avg_compa_ratio']}（健康区间 {result['healthy_ratio_label']}）",
        f"低于下限 {result['below_band_count']} 人，高于上限 {result['above_band_count']} 人",
        "",
    ]
    if result["below_band"]:
        lines.append("低于带宽下限（优先调薪对象）：")
        for d in result["below_band"][:8]:
            lines.append(
                f"- {d['name']}（{d['department']} / {d['job_level']}）："
                f"base {_yen(d['base_salary'])}，compa-ratio {d['compa_ratio']}"
            )
    if result["above_band"]:
        lines.append("")
        lines.append("高于带宽上限（建议冻结固定薪）：")
        for d in result["above_band"][:8]:
            lines.append(
                f"- {d['name']}（{d['department']} / {d['job_level']}）："
                f"base {_yen(d['base_salary'])}，compa-ratio {d['compa_ratio']}"
            )
    lines.append("")
    lines.append(_conclusion(result))
    return "\n".join(lines)


def format_salary_adjustment(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无调薪模拟数据")
    lines = [
        f"调薪预算模拟 · {result['department']}",
        f"调薪池 {result['budget_pct']}% = {_yen(result['budget_amount'])}，"
        f"可为 {result['adjusted_count']} 人补齐，支出 {_yen(result['used_amount'])}，"
        f"剩余 {_yen(result['remain_amount'])}",
        "",
    ]
    for p in result["plan"][:10]:
        lines.append(
            f"- {p['name']}（{p['department']} / {p['job_level']}）："
            f"{_yen(p['current_base'])} → +{_yen(p['grant'])}（+{p['raise_pct']}%），"
            f"调整后 compa-ratio {p['new_compa_ratio']}"
        )
    if result["unaddressed_count"]:
        lines.append("")
        lines.append(f"另有 {result['unaddressed_count']} 人因预算不足未覆盖。")
    lines.append("")
    lines.append(_conclusion(result))
    return "\n".join(lines)


def format_benefits(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无福利数据")
    lines = [
        f"福利覆盖分析 · {result['department']}",
        f"在职 {result['employee_count']} 人，{result['plan_count']} 项福利"
        f"（核心 {result['core_plan_count']} 项），人均年成本 "
        f"{_yen(result['avg_cost_per_head'])}",
        "",
    ]
    for r in result["plans"][:10]:
        flag = "［核心］" if r["is_core"] else "［可选］"
        lines.append(
            f"- {flag} {r['plan_name']}（{r['category']}）：参保 {r['enrolled']} 人，"
            f"覆盖率 {_pct(r['coverage_rate'])}，{r['gap']}"
        )
    lines.append("")
    lines.append(_conclusion(result))
    return "\n".join(lines)


def format_compensation_summary(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无该员工薪酬数据")
    e = result["employee"]
    lines = [
        f"薪酬总览 · {e['name']}（{e['department']} / {e['position_title']} / {e['job_level']}）",
        f"生效日期 {result['effective_date']}",
        "",
        f"固定薪　　　{_yen(result['base_salary'])}",
        f"目标奖金　　{_yen(result['target_bonus'])}（比例 {result['target_bonus_pct']}%）",
        f"长期激励　　{_yen(result['equity_value'])}",
        f"总现金薪酬　{_yen(result['tcc'])}",
        f"福利成本　　{_yen(result['benefit_cost'])}",
        f"总直接薪酬　{_yen(result['tdc'])}",
        "",
        f"带宽位置：compa-ratio {result['compa_ratio']}，"
        f"处于带宽的 {round(result['penetration'] * 100)}% 位置",
    ]
    if result["benefits"]:
        lines.append("")
        lines.append(
            "已享福利："
            + "、".join(f"{b['name']}（{_yen(b['cost'])}）" for b in result["benefits"])
        )
    lines.append("")
    lines.append(_conclusion(result))
    return "\n".join(lines)


def format_performance_goal(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无目标达成数据")
    lines = [
        f"目标达成分析 · {result['period']} · {result['department']}",
        f"跟踪 {result['goal_count']} 条目标，覆盖 {result['employee_count']} 人，"
        f"平均达成率 {_pct(result['avg_achievement'])}",
        "",
        "达成率最高：",
    ]
    for r in result["top10"][:5]:
        lines.append(
            f"- {r['name']}（{r['department']}）：{_pct(r['achievement_rate'])}，"
            f"{r['completed_count']}/{r['goal_count']} 条已完成"
        )
    if result["bottom10"]:
        lines.append("")
        lines.append("达成率最低：")
        for r in result["bottom10"][-5:]:
            lines.append(
                f"- {r['name']}（{r['department']}）：{_pct(r['achievement_rate'])}，"
                f"{r['at_risk_count']} 条处于风险"
            )
    lines.append("")
    lines.append(_conclusion(result))
    return "\n".join(lines)


def format_performance_deviation(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无评价偏差数据")
    lines = [
        f"绩效认知偏差 · {result['period']} · {result['department']}",
        f"{result['review_count']} 条评估，平均绝对偏差 {result['avg_abs_gap']} 分，"
        f"其中 {result['big_gap_count']} 人偏差超过 1 分",
        "",
    ]
    for x in result["big_gap_people"][:8]:
        lines.append(
            f"- {x['name']}（{x['department']}）：自评 {x['self_score']} / "
            f"主管评 {x['manager_score']}，偏差 {x['delta']}（{x['kind']}）"
        )
    lines.append("")
    lines.append(_conclusion(result))
    return "\n".join(lines)


def format_performance_distribution(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无分布校验数据")
    lines = [
        f"强制分布校验 · {result['period']} · {result['department']}",
        f"参与校准 {result['total_reviewed']} 人，"
        f"{result['deviation_count']} 个等级偏离标准",
        "",
    ]
    for r in result["distribution"]:
        flag = "OK" if r["within_standard"] else "偏离"
        lines.append(
            f"- {r['rating']}：{r['count']} 人（{_pct(r['share'])}），"
            f"标准 {_pct(r['standard'][0])}~{_pct(r['standard'][1])}　{flag}"
        )
    if result["deviations"]:
        lines.append("")
        lines.append("调整建议：")
        for d in result["deviations"]:
            lines.append(
                f"- {d['rating']} {d['direction']}，建议调整约 "
                f"{d['adjust_count']} 人：{d['advice']}"
            )
    lines.append("")
    lines.append(_conclusion(result))
    return "\n".join(lines)


def format_improvement(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无改进计划数据")
    lines = [
        f"绩效改进计划 · {result['department']}",
        f"共 {result['total']} 份：进行中 {result['ongoing']}、"
        f"已通过 {result['passed']}、未通过 {result['failed']}",
        "",
    ]
    for p in result["people"][:10]:
        lines.append(
            f"- {p['name']}（{p['department']}）：目标 {p['target_score']} / "
            f"当前 {p['current_score']}，差 {p['gap']}　{p['outcome']}"
        )
    lines.append("")
    lines.append(_conclusion(result))
    return "\n".join(lines)


def format_relation_cases(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无关系事件数据")
    lines = [
        f"员工关系事件 · {result['department']}",
        f"共 {result['total_cases']} 起，未闭环 {result['open_cases']} 起，"
        f"超期 {result['overdue_cases']} 起，"
        f"高升级风险 {result['high_escalation_risk']} 起",
        "",
    ]
    if result["overdue_list"]:
        lines.append("已超期：")
        for r in result["overdue_list"][:8]:
            lines.append(
                f"- {r['employee']}（{r['department']}）：{r['case_type']}，"
                f"已开 {r['days_open']} 天（时限 {r['sla_days']} 天），级别 {r['severity']}"
            )
    if result["high_risk_list"]:
        lines.append("")
        lines.append("升级风险较高：")
        for r in result["high_risk_list"][:8]:
            lines.append(
                f"- {r['employee']}（{r['department']}）：{r['case_type']}，"
                f"风险系数 {r['escalation_risk']}"
            )
    lines.append("")
    lines.append(_conclusion(result))
    return "\n".join(lines)


def format_engagement(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无敬业度数据")
    lines = [
        f"敬业度分析 · {result['period']} · {result['department']}",
        f"样本 {result['survey_count']} 人，平均 {result['avg_score']} 分，"
        f"eNPS {result['enps']}（推荐者 {result['promoter_percent']}%）",
        "",
        "五维得分：",
    ]
    for d in result["dimension_scores"]:
        lines.append(f"- {d['dimension']}：{d['score']} 分")
    if result["low_score_people"]:
        lines.append("")
        lines.append("低分预警（低于 3 分）：")
        for p in result["low_score_people"][:8]:
            lines.append(
                f"- {p['name']}（{p['department']}）：{p['overall_score']} 分，"
                f"最弱维度「{p['lowest_dimension']}」{p['lowest_score']} 分"
            )
    lines.append("")
    lines.append(_conclusion(result))
    return "\n".join(lines)


def format_learning_overview(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无培训数据")
    return "\n".join(
        [
            f"培训总览 · {result['department']}",
            f"在职 {result['employee_count']} 人，报名 "
            f"{result['enrollment_count']} 人次，完成 {result['completed_count']} 人次",
            f"覆盖率 {_pct(result['training_coverage'])}，"
            f"完课率 {_pct(result['completion_rate'])}",
            f"累计学时 {result['total_hours']} 小时，人均培训成本 "
            f"{_yen(result['avg_cost_per_employee'])}",
            "",
            _conclusion(result),
        ]
    )


def format_learning_compliance(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无必修合规数据")
    lines = [
        f"必修培训合规 · {result['department']}",
        f"必修 {result['mandatory_course_count']} 门，应完成 "
        f"{result['required_completions']} 人次，"
        f"实际完成 {result['actual_completions']} 人次，"
        f"合规率 {_pct(result['compliance_rate'])}",
        "",
    ]
    for g in result["gaps"][:10]:
        lines.append(
            f"- {g['name']}（{g['department']}）：缺 {g['missing_count']} 门，"
            f"需补训 {g['missing_hours']} 学时"
        )
    lines.append("")
    lines.append(_conclusion(result))
    return "\n".join(lines)


def format_learning_recommend(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无推荐数据")
    e = result["employee"]
    lines = [
        f"课程推荐 · {e['name']}（{e['department']} / {e['position_title']}）",
        f"存在 {result['gap_count']} 项能力差距",
        "",
    ]
    for g in result["gaps"][:6]:
        lines.append(
            f"- {g['competency']}：现 {g['current_level']} 级 → 目标 "
            f"{g['required_level']} 级（差 {g['gap']} 级）"
        )
    lines.append("")
    lines.append("推荐课程：")
    for r in result["recommendations"]:
        lines.append(
            f"- ［{r['priority']}优先］{r['course']}（{r['delivery_mode']}，"
            f"{r['duration_hours']} 学时，{_yen(r['cost_per_head'])}）"
        )
    lines.append("")
    lines.append(f"合计 {result['total_hours']} 学时，预算 {_yen(result['total_cost'])}")
    lines.append(_conclusion(result))
    return "\n".join(lines)


def format_learning_effect(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无培训效果数据")
    lines = [
        f"培训效果评估 · {result['department']}",
        f"{result['course_count']} 门课程，{result['total_enrollments']} 人次，"
        f"总投入 {_yen(result['total_cost'])}",
        "",
    ]
    for r in result["courses"][:10]:
        lines.append(
            f"- {r['course_name']}（{r['category']}）：通过率 {_pct(r['pass_rate'])}，"
            f"平均 {r['avg_score']} 分，满意度 {r['avg_feedback']}"
        )
    lines.append("")
    lines.append(_conclusion(result))
    return "\n".join(lines)


def format_headcount(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无编制数据")
    lines = [
        f"编制达成审查 · {result['period']} · {result['department']}",
        f"整体达成率 {_pct(result['overall_fill_rate'])}"
        f"（在编 {result['total_actual']} / 编制 {result['total_planned']}），"
        f"缺口 {result['total_gap']} 人",
        "",
    ]
    for r in result["plans"]:
        lines.append(
            f"- {r['department']}：{r['actual']}/{r['planned']} 人（{r['status']}），"
            f"缺口 {r['gap']} 人，在招 {r['open_reqs']} 个，"
            f"预算执行 {_pct(r['budget_usage'])}"
        )
    lines.append("")
    lines.append(_conclusion(result))
    return "\n".join(lines)


def format_forecast(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无人力预测数据")
    lines = [
        f"人力供需预测 · {result['scenario']} 情景 · {result['department']}",
        f"净需求 {result['total_net_demand']} 人，内部可供给 "
        f"{result['total_internal_supply']} 人，"
        f"需外部招聘 {result['total_external_hire']} 人",
        "",
    ]
    for r in result["rows"][:8]:
        lines.append(
            f"- {r['department']} / {r['job_level']}：净需求 {r['net_demand']} 人，"
            f"内部供给 {r['internal_supply']} 人，"
            f"外部需 {r['external_hire_need']} 人（{r['status']}）"
        )
    lines.append("")
    lines.append(_conclusion(result))
    return "\n".join(lines)


def format_attrition(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无离职风险数据")
    lines = [
        f"离职风险扫描 · {result['department']}",
        f"扫描 {result['scanned_count']} 人，高风险 {result['high_risk_count']} 人，"
        f"中风险 {result['medium_risk_count']} 人，"
        f"其中关键岗位 {result['critical_position_risk']} 人",
        "",
    ]
    for p in result["people"][:10]:
        lines.append(
            f"- {p['name']}（{p['department']} / {p['position_title']}）："
            f"风险 {p['risk_score']}（{p['risk_level']}），"
            f"首要因子「{p['top_factor_label']}」"
        )
    if result["critical_position_people"]:
        lines.append("")
        lines.append("关键岗位高风险（最高优先级）：")
        for p in result["critical_position_people"][:5]:
            lines.append(f"- {p['name']}：建议 {p['retention_action']}")
    lines.append("")
    lines.append(_conclusion(result))
    return "\n".join(lines)


def format_succession_link(result: dict) -> str:
    if not result or result.get("error"):
        return result.get("error", "暂无继任联动数据")
    lines = [
        "离职风险 × 继任覆盖交叉分析",
        f"高风险 {result['high_risk_total']} 人中，"
        f"{result['uncovered_high_risk']} 人所在岗位没有继任候选人",
        "",
    ]
    for p in result["uncovered_people"][:10]:
        lines.append(
            f"- {p['name']}（{p['department']} / {p['position_title']}）："
            f"风险 {p['risk_score']}"
        )
    lines.append("")
    lines.append(_conclusion(result))
    return "\n".join(lines)


FORMATTERS = {
    # 人才管理与组织发展
    "TALENT_REVIEW": format_talent_review,
    "SUCCESSION": format_succession,
    "PIPELINE": format_pipeline,
    "IDP": format_idp,
    "DIAGNOSIS": format_diagnosis,
    # HRIS · 招聘管理
    "HRIS_RECRUITMENT_SCREEN": format_ats_screen,
    "HRIS_RECRUITMENT_OFFER": format_ats_offer,
    "HRIS_RECRUITMENT_FUNNEL": format_ats_funnel,
    "HRIS_RECRUITMENT_INTERVIEW": format_ats_interview,
    # HRIS · 薪酬与福利
    "HRIS_COMPENSATION_COMPA": format_compa,
    "HRIS_COMPENSATION_ADJUSTMENT": format_salary_adjustment,
    "HRIS_COMPENSATION_BENEFITS": format_benefits,
    "HRIS_COMPENSATION_SUMMARY": format_compensation_summary,
    # HRIS · 绩效管理
    "HRIS_PERFORMANCE_GOAL": format_performance_goal,
    "HRIS_PERFORMANCE_DEVIATION": format_performance_deviation,
    "HRIS_PERFORMANCE_DISTRIBUTION": format_performance_distribution,
    "HRIS_PERFORMANCE_IMPROVEMENT": format_improvement,
    # HRIS · 员工关系管理
    "HRIS_ER_LEAVE_BALANCE": format_hr_leave_balance,
    "HRIS_ER_LEAVE_REQUEST": format_hr_leave_request,
    "HRIS_ER_LEAVE_APPROVE": format_hr_leave_approve,
    "HRIS_ER_ATTENDANCE": format_hr_attendance,
    "HRIS_ER_LEAVE_PENDING": format_hr_pending,
    "HRIS_ER_CASES": format_relation_cases,
    "HRIS_ER_ENGAGEMENT": format_engagement,
    # HRIS · 培训与开发
    "HRIS_LEARNING_OVERVIEW": format_learning_overview,
    "HRIS_LEARNING_COMPLIANCE": format_learning_compliance,
    "HRIS_LEARNING_RECOMMEND": format_learning_recommend,
    "HRIS_LEARNING_EFFECT": format_learning_effect,
    # HRIS · 人力资源规划
    "HRIS_WORKFORCE_HEADCOUNT": format_headcount,
    "HRIS_WORKFORCE_FORECAST": format_forecast,
    "HRIS_WORKFORCE_ATTRITION": format_attrition,
    "HRIS_WORKFORCE_SUCCESSION_LINK": format_succession_link,
}

# CHAT 也会经过 generate_answer；为安全起见提供兜底
FORMATTERS.setdefault("CHAT", lambda r: r if isinstance(r, str) else str(r))


def format_result(topic: str, result: dict) -> str:
    formatter = FORMATTERS.get(topic)
    if not formatter:
        return str(result)
    return formatter(result)
