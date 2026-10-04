"""规则降级引擎。

当大模型不可用（未安装 Ollama、未配置 Key）时，
使用关键词规则完成意图识别与信息抽取，保证完整流程依然可跑。
这也是本项目的兜底安全网：规则不会编造数据库中不存在的部门与员工。
"""

import re

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import Employee, PerformanceRecord

# 核心双域 → 意图
CORE_MODULE_INTENT = {
    "organization_development": "ORG_DEV",
    "talent_development": "TALENT_DEV",
}

# 核心双域的关键词路由表。
# 顺序即优先级：组织发展在前，避免"组织变革"被归入人力资源规划。
CORE_MODULE_KEYWORDS = [
    (
        "organization_development",
        [
            "组织架构", "组织单元", "组织效能", "组织变革", "组织调整", "重组",
            "人效", "人均产出", "人工成本", "成本率", "职级体系", "职族",
            "晋升率", "晋升通道", "管理幅度", "汇报线", "层级", "金字塔",
            "合并", "拆分", "分拆", "扩编", "缩编", "新设",
            # 组织诊断 / 战略解码 / 文化氛围
            "组织诊断", "诊断", "健康度", "痛点", "瓶颈", "组织扫描",
            "7S", "7s", "6-BOX", "六盒", "五维",
            "战略解码", "战略", "目标拆解", "目标对齐", "解码",
            "文化", "氛围", "敬业度", "价值观", "心理安全",
            "管控", "权责", "定岗定编",
        ],
    ),
    (
        "talent_development",
        [
            "人才发展", "能力差距", "能力画像", "能力模型", "任职资格", "人才标准",
            "匹配度", "够不够格", "人才池", "后备池", "专家池",
            "晋升", "下一职级", "晋升评审", "能否胜任", "任职达标",
            "发展项目", "培养项目", "行动学习", "训练营", "轮岗", "内训",
            "导师", "带教", "师徒",
            # 人才盘点 / 胜任力 / 继任梯队 / IDP / 任用
            "盘点", "九宫格", "人才地图", "高潜", "360", "明星", "短板",
            "胜任力", "素质模型", "能力项",
            "继任", "接班", "梯队", "后备", "关键岗位",
            "IDP", "idp", "个人发展计划", "发展计划",
            "任用", "提拔", "人员调整", "淘汰",
        ],
    ),
]

INTENT_KEYWORDS = [
    ("ORG_DEV", ["组织发展", "架构", "效能"]),
    ("TALENT_DEV", ["人才发展", "发展计划", "培养", "提升计划"]),
    ("HRIS", ["HRIS", "人力资源", "人事", "HR 系统"]),
]

UPDATE_KEYWORDS = ["改成", "改为", "修改为", "换成", "切换", "改成 ", "更新为", "改成"]

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
            "培训", "课程", "必修", "学时", "报名", "讲师", "赋能",
            "能力差距", "培训计划", "补训", "上课",
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
            "招聘规划",
        ],
    ),
]


def rule_core_module(message: str) -> str | None:
    """在核心双域内决定进入组织发展还是人才发展，命中不了返回 None。"""
    text = message or ""
    for module, keywords in CORE_MODULE_KEYWORDS:
        for k in keywords:
            if k in text:
                return module
    return None


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

    # 优先级：修改条件 > 业务意图。
    # 短句里同时出现修改词与业务词时，更像是在改条件。
    has_update = any(k in text for k in UPDATE_KEYWORDS)
    has_business = any(
        k in text for keywords in dict(INTENT_KEYWORDS).values() for k in keywords
    )
    has_core = rule_core_module(text) is not None
    has_hris = rule_hris_module(text) is not None

    if has_update and not (has_business or has_core or has_hris):
        return "UPDATE"
    if has_update and (has_business or has_core or has_hris) and len(text) <= 20:
        return "UPDATE"

    # 核心双域优先于 HRIS，保证"组织发展""人才发展"这类主打能力优先命中
    if has_core:
        return CORE_MODULE_INTENT[rule_core_module(text)]
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
