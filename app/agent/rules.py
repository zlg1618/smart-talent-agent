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
    ("HRIS", ["HRIS", "人力资源", "人事", "HR 系统"]),
]

UPDATE_KEYWORDS = ["改成", "改为", "修改为", "换成", "切换", "改成 ", "更新为", "改成"]
PREFERENCE_KEYWORDS = ["只看", "只要", "仅仅看", "排除", "不考虑", "不包括", "剔除"]

# HRIS 六大子模块的关键词路由表。
# 顺序即优先级：越具体的短语排越前，避免"招聘开会"被归入员工关系。
HRIS_MODULE_KEYWORDS = [
    (
        "recruitment",
        [
            "简历筛选", "候选人", "招聘需求", "面试安排", "招聘漏斗", "漏斗",
            "定 Offer", "智能定薪", "Offer", "offer", "JD", "招聘",
            "录用", "人才甄选", "筛选简历",
        ],
    ),
    (
        "compensation",
        [
            "薪酬", "薪资", "调薪", "compa", "公平性", "福利", "参保", "带宽",
            "定薪", "奖金", "股权", "总包", "五险一金", "体检",
        ],
    ),
    (
        "performance",
        [
            "绩效", "OKR", "okr", "KPI", "kpi", "目标达成", "绩效校准", "校准",
            "强制分布", "PIP", "pip", "改进计划", "自评", "绩效面谈", "绩效评价",
        ],
    ),
    (
        "learning",
        [
            "培训", "课程", "课", "必修", "学习", "学时", "报名", "讲师", "赋能",
            "能力差距", "培训计划", "训练营", "补训", "上课",
        ],
    ),
    (
        "employee_relations",
        [
            "请假", "年假", "病假", "事假", "调休", "产假", "陪产假", "考勤",
            "出勤", "迟到", "缺勤", "关系事件", "纠纷", "申诉", "敬业度", "满意度调查",
        ],
    ),
    (
        "workforce",
        [
            "编制", "人力规划", "供需", "预测", "离职风险", "人力缺口", "headcount",
            "招聘规划", "人才盘点需求", "扩编",
        ],
    ),
]


def rule_hris_module(message: str) -> str | None:
    """在 HRIS 域内决定具体走哪个子模块，命中不了返回 None。"""
    text = message or ""
    for module, keywords in HRIS_MODULE_KEYWORDS:
        for k in keywords:
            if k in text:
                return module
    return None


def rule_intent(message: str) -> str:
    text = message or ""

    # 优先级：修改条件 > 筛选偏好 > 业务意图。
    # 偏好必须早于业务关键词判断，否则"只看明星人才"会被误判成重新盘点。
    has_update = any(k in text for k in UPDATE_KEYWORDS)
    has_business = any(
        k in text for keywords in dict(INTENT_KEYWORDS).values() for k in keywords
    )
    has_hris = rule_hris_module(text) is not None

    if has_update and (has_business or has_hris):
        # 同时含修改词与业务词时按长度判断：短句更像改条件
        if len(text) <= 20:
            return "UPDATE"
    if has_update and not (has_business or has_hris):
        return "UPDATE"
    if any(k in text for k in PREFERENCE_KEYWORDS):
        return "PREFERENCE"

    # HRIS 六大模块的关键词优先于盘点类，否则"招聘"会被误判为人才盘点
    if has_hris:
        return "HRIS"

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
