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


FORMATTERS = {
    "TALENT_REVIEW": format_talent_review,
    "SUCCESSION": format_succession,
    "PIPELINE": format_pipeline,
    "IDP": format_idp,
    "DIAGNOSIS": format_diagnosis,
}


def format_result(topic: str, result: dict) -> str:
    formatter = FORMATTERS.get(topic)
    if not formatter:
        return str(result)
    return formatter(result)
