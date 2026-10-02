"""规则降级引擎。

当大模型不可用（未安装 Ollama、未配置 Key）时，
使用关键词规则完成意图识别与信息抽取，保证完整流程依然可跑。
这也是本项目的兜底安全网：规则不会编造数据库中不存在的部门与员工。
"""

import re

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import Employee, PerformanceRecord

INTENT_KEYWORDS = [
    ("DIAGNOSIS", ["组织诊断", "组织健康", "健康度", "诊断", "离职率", "组织问题"]),
    ("SUCCESSION", ["继任", "接班", "梯队", "后备", "关键岗位", "继任地图"]),
    ("IDP", ["发展计划", "IDP", "idp", "培养", "发展方案", "提升计划", "学习路径"]),
    (
        "TALENT_REVIEW",
        ["盘点", "九宫格", "人才地图", "绩效潜力", "人才分布", "明星人才", "高潜"],
    ),
]

UPDATE_KEYWORDS = ["改成", "改为", "修改为", "换成", "切换", "改成 ", "更新为", "改成"]
PREFERENCE_KEYWORDS = ["只看", "只要", "仅仅看", "排除", "不考虑", "不包括", "剔除"]


def rule_intent(message: str) -> str:
    text = message or ""

    # 优先级：修改条件 > 筛选偏好 > 业务意图。
    # 偏好必须早于业务关键词判断，否则"只看明星人才"会被误判成重新盘点。
    has_update = any(k in text for k in UPDATE_KEYWORDS)
    has_business = any(
        k in text for keywords in dict(INTENT_KEYWORDS).values() for k in keywords
    )

    if has_update and not has_business:
        return "UPDATE"
    if any(k in text for k in PREFERENCE_KEYWORDS):
        return "PREFERENCE"
    if has_update and len(text) <= 20:
        return "UPDATE"

    for intent, keywords in INTENT_KEYWORDS:
        if any(k in text for k in keywords):
            return intent

    if has_update:
        return "UPDATE"
    return "CHAT"


def rule_extract(db: Session, message: str) -> dict:
    text = message or ""

    # 部门：只在数据库真实存在的部门中匹配
    departments = list(
        db.execute(select(Employee.department).distinct()).scalars().all()
    )
    department = next((d for d in departments if d and d in text), None)

    # 周期：形如 2025H1 / 2024H2
    period = None
    m = re.search(r"(20\d{2})\s*[Hh]([12])", text)
    if m:
        period = f"{m.group(1)}H{m.group(2)}"
    else:
        m2 = re.search(r"(20\d{2})年?\s*(上|下)半年", text)
        if m2:
            period = f"{m2.group(1)}H{'1' if m2.group(2) == '上' else '2'}"

    # 职级：P4-P8 / M1-M3
    job_level = None
    m3 = re.search(r"\b([PMpm][1-8])\b", text)
    if m3:
        job_level = m3.group(1).upper()

    # 员工姓名：只在数据库真实存在的姓名中匹配
    names = list(db.execute(select(Employee.name).distinct()).scalars().all())
    employee_name = next((n for n in names if n and n in text), None)

    return {
        "department": department,
        "period": period,
        "job_level": job_level,
        "employee_name": employee_name,
    }


def latest_period(db: Session) -> str | None:
    stmt = (
        select(PerformanceRecord.period)
        .distinct()
        .order_by(desc(PerformanceRecord.period))
    )
    return db.execute(stmt).scalars().first()


def rule_preference(message: str) -> dict:
    text = message or ""
    result: dict = {"only_grid": None, "criticality": None, "exclude_readiness": None}

    if "明星" in text or "高绩效高潜" in text:
        result["only_grid"] = ["高-高"]
    elif "高潜" in text and ("只看" in text or "只要" in text):
        result["only_grid"] = ["高-高", "中-高", "低-高"]
    elif "待优化" in text or "低效" in text:
        result["only_grid"] = ["低-低"]
    elif "待改进" in text:
        result["only_grid"] = ["低-中", "低-低"]

    if "最高" in text or "最重要" in text or "核心关键" in text:
        result["criticality"] = "高"
    elif "中等重要" in text:
        result["criticality"] = "中"

    if "未就绪" in text or "不成熟" in text:
        result["exclude_readiness"] = ["not_ready"]
    elif "两年" in text:
        result["exclude_readiness"] = ["not_ready", "ready_2y"]

    return result
