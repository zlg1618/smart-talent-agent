"""种子数据生成。

生成一套可演示的模拟人才数据：员工、绩效、潜力、能力模型，
以及组织发展（组织单元、组织效能、职级体系、变革方案）与
人才发展（任职资格、人才池、发展项目、导师带教）两类核心域数据。

用法：
    python seed_data.py            # 重建全部数据
    python seed_data.py --keep     # 保留已有数据，仅追加缺失部分
"""

import argparse
import random
import sys
from datetime import date, datetime, time as dtime, timedelta

from sqlalchemy import delete, select

from app.config.database import SessionLocal, init_db
from app.models import (
    Application,
    AttritionRisk,
    AttendanceRecord,
    BenefitPlan,
    CalibrationSession,
    Candidate,
    CandidateSkill,
    Competency,
    DevelopmentProgram,
    Employee,
    EmployeeBenefit,
    EmployeeCompensation,
    EmployeeCompetency,
    EngagementSurvey,
    HeadcountPlan,
    ImprovementPlan,
    InterviewSchedule,
    JobArchitecture,
    JobPost,
    LeaveRequest,
    Mentorship,
    OfferRecord,
    OrgChange,
    OrgEffectiveness,
    OrgUnit,
    PerformanceGoal,
    PerformanceRecord,
    PerformanceReview,
    PotentialAssessment,
    RelationCase,
    SalaryBand,
    TalentPool,
    TalentStandard,
    TrainingCourse,
    TrainingEnrollment,
    WorkforceForecast,
)
from datetime import time as dtime, timedelta

random.seed(42)

PERIODS = ["2024H2", "2025H1"]

SURNAMES = list("张王李赵刘陈杨黄周吴徐孙马朱胡林郭何高罗郑梁谢宋唐许韩冯邓曹彭曾田董袁潘蒋蔡余杜叶程苏魏吕丁任沈姚卢")
GIVEN_NAMES = [
    "伟", "芳", "娜", "敏", "静", "丽", "强", "磊", "洋", "勇",
    "军", "杰", "娟", "涛", "明", "超", "平", "刚", "华", "文博",
    "思远", "雨欣", "子轩", "浩然", "梓涵", "一诺", "若曦", "嘉言", "宇宁", "宜欣",
]

# levels 与 weights 一一对应：低职级人多、高职级人少，接近真实金字塔结构。
# 基层 P4 权重偏低，用于演示"基层储备断层"这一常见组织问题。
DEPARTMENTS = {
    "技术中心": {
        "family": "技术",
        "titles": ["后端工程师", "前端工程师", "测试工程师", "架构师", "技术经理", "技术总监"],
        "levels": ["P4", "P5", "P6", "P7", "P8", "M1", "M2", "M3"],
        "weights": [5, 7, 7, 4, 2, 2, 2, 1],
        "headcount": 22,
    },
    "产品部": {
        "family": "产品",
        "titles": ["产品经理", "高级产品经理", "产品专家", "产品总监"],
        "levels": ["P4", "P5", "P6", "P7", "M1", "M2"],
        "weights": [3, 4, 3, 2, 1, 1],
        "headcount": 12,
    },
    "销售部": {
        "family": "销售",
        "titles": ["销售代表", "大客户经理", "区域经理", "销售总监"],
        "levels": ["P4", "P5", "P6", "P7", "M1", "M2"],
        "weights": [4, 5, 4, 2, 1, 1],
        "headcount": 16,
    },
    "人力资源部": {
        "family": "职能",
        "titles": ["HRBP", "招聘经理", "薪酬绩效经理", "组织发展经理", "HR 总监"],
        "levels": ["P4", "P5", "P6", "M1", "M2"],
        "weights": [2, 3, 2, 1, 1],
        "headcount": 9,
    },
    "财务部": {
        "family": "职能",
        "titles": ["财务分析师", "会计", "财务经理", "财务总监"],
        "levels": ["P4", "P5", "P6", "M1"],
        "weights": [2, 3, 2, 1],
        "headcount": 8,
    },
}

CITIES = ["北京", "上海", "深圳", "杭州", "成都", "武汉", "广州"]

COMPETENCIES = [
    ("架构设计", "专业"),
    ("编码实现", "专业"),
    ("数据分析", "专业"),
    ("产品思维", "专业"),
    ("项目管理", "管理"),
    ("团队领导", "管理"),
    ("跨部门协作", "通用"),
    ("商业敏感", "通用"),
    ("沟通表达", "通用"),
]

# 各职级的薪酬带宽（元/月），用于岗位职级体系演示
LEVEL_BANDS = {
    "P4": (12000, 16000, 22000),
    "P5": (16000, 22000, 30000),
    "P6": (22000, 30000, 42000),
    "P7": (30000, 40000, 55000),
    "P8": (40000, 55000, 75000),
    "M1": (35000, 48000, 65000),
    "M2": (50000, 68000, 92000),
    "M3": (70000, 95000, 130000),
}

# 任职资格四维度及其权重
STANDARD_DIMENSIONS = ["专业能力", "业务贡献", "领导力", "学习敏锐"]

DIMENSION_WEIGHT = {
    "专业能力": 0.35,
    "业务贡献": 0.30,
    "领导力": 0.20,
    "学习敏锐": 0.15,
}

# 各职级达标线（1-5 分制）
LEVEL_PASS_SCORE = {
    "P4": 3.0, "P5": 3.2, "P6": 3.4, "P7": 3.6,
    "P8": 3.8, "M1": 3.6, "M2": 3.8, "M3": 4.0,
}

DIMENSION_REQUIREMENT = {
    "专业能力": "能独立承担本专业领域的完整任务并输出可复用的方法",
    "业务贡献": "在考核周期内交付可量化的业务结果并被业务方认可",
    "领导力": "能带领小组完成任务并进行目标分解与过程辅导",
    "学习敏锐": "面对新领域可在短期内完成学习并转化为产出",
}


def _unique_names(count: int) -> list[str]:
    names = set()
    while len(names) < count:
        names.add(random.choice(SURNAMES) + random.choice(GIVEN_NAMES))
    return list(names)


def _gauss(mean: float, std: float, low: float = 1.0, high: float = 5.0) -> float:
    value = random.gauss(mean, std)
    return round(min(high, max(low, value)), 2)


def _grade(score: float) -> str:
    if score >= 4.5:
        return "A"
    if score >= 3.8:
        return "B+"
    if score >= 3.0:
        return "B"
    return "C"


def _hire_date() -> date:
    year = random.randint(2017, 2025)
    month = random.randint(1, 12)
    return date(year, month, random.randint(1, 28))


def clear_all(db):
    for table in (
        # 核心双域：人才发展
        Mentorship,
        DevelopmentProgram,
        TalentPool,
        TalentStandard,
        # 核心双域：组织发展
        OrgChange,
        JobArchitecture,
        OrgEffectiveness,
        OrgUnit,
        # 人力资源规划
        AttritionRisk,
        WorkforceForecast,
        HeadcountPlan,
        # 培训与开发
        TrainingEnrollment,
        TrainingCourse,
        # 员工关系管理
        EngagementSurvey,
        RelationCase,
        AttendanceRecord,
        LeaveRequest,
        # 绩效管理
        ImprovementPlan,
        CalibrationSession,
        PerformanceReview,
        PerformanceGoal,
        # 薪酬与福利
        EmployeeBenefit,
        BenefitPlan,
        EmployeeCompensation,
        SalaryBand,
        # 招聘管理
        OfferRecord,
        InterviewSchedule,
        Application,
        CandidateSkill,
        Candidate,
        JobPost,
        # 人才管理与组织发展
                    EmployeeCompetency,
            Competency,
        PotentialAssessment,
        PerformanceRecord,
            Employee,
    ):
        db.execute(delete(table))
    db.commit()


def seed(db):
    now_dt = datetime.now()
    total = sum(d["headcount"] for d in DEPARTMENTS.values())
    names = _unique_names(total)

    # ---------- 能力模型 ----------
    for name, category in COMPETENCIES:
        db.add(Competency(name=name, category=category))
    db.flush()
    competencies = {
        c.name: c for c in db.execute(select(Competency)).scalars().all()
    }

    # ---------- 员工 ----------
    employees: list[Employee] = []
    idx = 0
    for dept, cfg in DEPARTMENTS.items():
        for _ in range(cfg["headcount"]):
            emp = Employee(
                employee_no=f"E{idx + 1:04d}",
                name=names[idx],
                department=dept,
                position_title=random.choice(cfg["titles"]),
                job_family=cfg["family"],
                job_level=random.choices(cfg["levels"], weights=cfg["weights"])[0],
                hire_date=_hire_date(),
                city=random.choice(CITIES),
                status="在职",
            )
            db.add(emp)
            employees.append(emp)
            idx += 1
    db.flush()

    # 保证高层职级一定存在，避免随机分布下 P8 / M3 为空导致梯队层级缺失
    tech_center = [e for e in employees if e.department == "技术中心"]
    if len(tech_center) >= 3:
        tech_center[0].job_level = "M3"
        tech_center[1].job_level = "P8"
        tech_center[2].job_level = "M2"
    db.flush()

    # ---------- 绩效与潜力 ----------
    for emp in employees:
        for period in PERIODS:
            perf_score = _gauss(3.45, 0.75)
            db.add(
                PerformanceRecord(
                    employee_id=emp.id,
                    period=period,
                    score=perf_score,
                    grade=_grade(perf_score),
                )
            )
            db.add(
                PotentialAssessment(
                    employee_id=emp.id,
                    period=period,
                    potential_score=_gauss(3.35, 0.8),
                    learning_agility=_gauss(3.4, 0.7),
                    leadership=_gauss(3.2, 0.8),
                    mobility=random.random() < 0.35,
                )
            )

    # ---------- 员工能力现状 ----------
    for emp in employees:
        picked = random.sample(list(competencies.values()), random.randint(4, 6))
        for comp in picked:
            current = random.randint(2, 4)
            required = min(5, current + random.choice([0, 1, 1, 2]))
            db.add(
                EmployeeCompetency(
                    employee_id=emp.id,
                    competency_id=comp.id,
                    current_level=current,
                    required_level=required,
                )
            )
    db.flush()

    # ---------- 组织发展：组织单元 ----------
    db.add(
        OrgUnit(
            name="公司总部",
            department="公司总部",
            parent_name=None,
            level=1,
            unit_type="公司",
            manager_name="CEO",
            planned_headcount=total,
            actual_headcount=total,
            period="2025H1",
        )
    )
    for dept, cfg in DEPARTMENTS.items():
        children_planned = 0
        for suffix in ("一组", "二组"):
            actual = (
                cfg["headcount"] // 2
                if suffix == "一组"
                else cfg["headcount"] - cfg["headcount"] // 2
            )
            planned = actual + random.choice([0, 0, 1, 2])
            children_planned += planned
            db.add(
                OrgUnit(
                    name=f"{dept}{suffix}",
                    department=dept,
                    parent_name=dept,
                    level=3,
                    unit_type="团队",
                    manager_name=f"{dept}{suffix}负责人",
                    planned_headcount=planned,
                    actual_headcount=actual,
                    period="2025H1",
                )
            )
        db.add(
            OrgUnit(
                name=dept,
                department=dept,
                parent_name="公司总部",
                level=2,
                unit_type="部门",
                manager_name=f"{dept}负责人",
                planned_headcount=children_planned,
                actual_headcount=cfg["headcount"],
                period="2025H1",
            )
        )

    # ---------- 组织发展：组织效能 ----------
    for dept, cfg in DEPARTMENTS.items():
        headcount = cfg["headcount"]
        revenue = round(headcount * random.uniform(55, 145), 1)
        labor_cost = round(revenue * random.uniform(0.32, 0.78), 1)
        db.add(
            OrgEffectiveness(
                department=dept,
                period="2025H1",
                headcount=headcount,
                revenue=revenue,
                labor_cost=labor_cost,
                attrition_rate=round(random.uniform(0.04, 0.26), 3),
                span_of_control=round(random.uniform(3.0, 16.0), 1),
            )
        )

    # ---------- 组织发展：岗位职级体系 ----------
    level_count: dict[tuple[str, str], int] = {}
    for emp in employees:
        key = (emp.department, emp.job_level)
        level_count[key] = level_count.get(key, 0) + 1
    for dept, cfg in DEPARTMENTS.items():
        for level in cfg["levels"]:
            band = LEVEL_BANDS.get(level, (15000, 20000, 28000))
            db.add(
                JobArchitecture(
                    department=dept,
                    job_family=cfg["family"],
                    job_level=level,
                    headcount=level_count.get((dept, level), 0),
                    target_ratio=round(random.uniform(0.08, 0.32), 3),
                    avg_tenure=round(random.uniform(0.8, 5.5), 1),
                    promotion_rate=round(random.uniform(0.03, 0.18), 3),
                    salary_min=band[0],
                    salary_mid=band[1],
                    salary_max=band[2],
                )
            )

    # ---------- 组织发展：组织变革方案 ----------
    change_defs = [
        ("技术中心平台与业务线拆分", "技术中心", "拆分", "技术中心", "平台组/业务组", 18, 96.0, "待审批"),
        ("产品部与设计中心合并", "产品部", "合并", "设计中心", "产品部", 12, -38.0, "进行中"),
        ("销售部区域扩编", "销售部", "扩编", "-", "销售部二组", 24, 260.0, "进行中"),
        ("财务部共享中心新设", "财务部", "新设", "-", "财务共享中心", 8, 74.0, "待审批"),
        ("人力资源部三支柱调整", "人力资源部", "调整", "人力资源部", "HRBP/COE/SSC", 9, 12.0, "已完成"),
        ("技术中心测试团队缩编", "技术中心", "缩编", "测试组", "-", 6, -55.0, "待审批"),
    ]
    for name, dept, ctype, src, tgt, affected, cost, status in change_defs:
        db.add(
            OrgChange(
                name=name,
                department=dept,
                change_type=ctype,
                source_unit=src,
                target_unit=tgt,
                affected_headcount=affected,
                cost_impact=cost,
                status=status,
                target_date=date(2025, random.choice([7, 8, 9, 10]), random.randint(1, 28)),
                note=f"{ctype}方案，影响 {affected} 人，成本影响 {cost} 万元/年",
            )
        )

    # ---------- 人才发展：任职资格标准 ----------
    for family in sorted({cfg["family"] for cfg in DEPARTMENTS.values()}):
        for level, pass_score in LEVEL_PASS_SCORE.items():
            for dim in STANDARD_DIMENSIONS:
                db.add(
                    TalentStandard(
                        job_family=family,
                        job_level=level,
                        dimension=dim,
                        requirement=DIMENSION_REQUIREMENT[dim],
                        weight=DIMENSION_WEIGHT[dim],
                        pass_score=pass_score,
                    )
                )

    # ---------- 人才发展：人才池 ----------
    pool_defs = [
        ("高潜人才池", "高潜", ["跨部门", "国际化", "复合背景"], 8),
        ("管理后备池", "后备", ["管理意愿", "带教经验"], 7),
        ("技术专家池", "专家", ["技术纵深", "架构能力"], 6),
    ]
    picked_ids: set[int] = set()
    for pool_name, pool_type, tags, size in pool_defs:
        candidates = [e for e in employees if e.id not in picked_ids]
        if len(candidates) < size:
            candidates = employees
        for emp in random.sample(candidates, min(size, len(candidates))):
            picked_ids.add(emp.id)
            db.add(
                TalentPool(
                    pool_name=pool_name,
                    pool_type=pool_type,
                    employee_id=emp.id,
                    stage=random.choices(["在池", "观察", "已出池"], weights=[7, 2, 1])[0],
                    tag=random.choice(tags),
                    score=round(random.uniform(62, 96), 1),
                    entered_at=date(2025, 1, 1),
                )
            )

    # ---------- 人才发展：发展项目 ----------
    program_defs = [
        ("青苗计划·应届生培养", "培养项目", "入职 1 年内员工", 30, 28, 24, 4.3, 18.0),
        ("扬帆计划·高潜训练营", "训练营", "高潜人才池成员", 20, 20, 19, 4.6, 32.0),
        ("领航计划·新任经理转身", "培养项目", "近一年晋升管理者", 12, 11, 8, 4.1, 24.0),
        ("业务突破行动学习", "行动学习", "跨部门骨干", 16, 14, 9, 3.9, 20.0),
        ("技术专家轮岗计划", "轮岗", "技术专家池成员", 10, 6, 4, 3.6, 12.0),
    ]
    for name, ptype, audience, capacity, enrolled, completed, sat, budget in program_defs:
        db.add(
            DevelopmentProgram(
                name=name,
                program_type=ptype,
                audience=audience,
                capacity=capacity,
                enrolled=enrolled,
                completed=completed,
                satisfaction=sat,
                budget=budget,
                start_date=date(2025, 3, 1),
                end_date=date(2025, random.choice([9, 10, 11, 12]), 28),
            )
        )

    # ---------- 人才发展：导师带教 ----------
    mentors = [
        e for e in employees
        if e.job_level.startswith("M") or e.job_level in ("P7", "P8")
    ]
    mentees = [e for e in employees if e.job_level in ("P4", "P5", "P6")]
    topics = [
        "技术纵深与架构思维", "从专业到管理的转身", "跨部门协作与影响力",
        "业务理解与商业敏感", "目标管理与过程辅导", "职业规划与能力补齐",
    ]
    for _ in range(14):
        if not mentors or not mentees:
            break
        planned = random.choice([4, 6, 8])
        done = random.randint(0, planned)
        db.add(
            Mentorship(
                mentor_id=random.choice(mentors).id,
                mentee_id=random.choice(mentees).id,
                topic=random.choice(topics),
                session_count=done,
                planned_sessions=planned,
                status="已完成" if done >= planned else "进行中",
                start_date=date(2025, 2, 1),
            )
        )

    # ---------- ATS 招聘需求 ----------
    job_defs = [
        ("高级前端开发工程师", "技术中心", 2, "bachelor", 5, 30000, 50000,
         "前端,JavaScript,CSS,React,Vue,Webpack,TypeScript"),
        ("高级后端开发工程师", "技术中心", 3, "bachelor", 5, 30000, 60000,
         "后端,Python,Java,MySQL,Redis,系统设计,Kafka"),
        ("产品经理", "产品部", 2, "bachelor", 3, 25000, 40000,
         "产品思维,用户研究,数据分析,商业敏感,沟通表达"),
        ("销售经理", "销售部", 1, "bachelor", 3, 20000, 35000,
         "销售管理,大客户管理,沟通表达,商业敏感"),
        ("财务分析师", "财务部", 1, "bachelor", 1, 15000, 25000,
         "财务分析,数据分析,商业敏感,沟通表达"),
    ]
    jobs: list[JobPost] = []
    tech_hm_emp = next((e for e in employees if e.department == "技术中心" and e.job_level == "M3"), None)
    product_hm = next((e for e in employees if e.department == "产品部" and e.job_level == "M2"), None)
    sales_hm = next((e for e in employees if e.department == "销售部" and e.job_level == "M2"), None)
    finance_hm = next((e for e in employees if e.department == "财务部" and e.job_level == "M1"), None)
    hiring_managers = {
        "技术中心": tech_hm_emp,
        "产品部": product_hm,
        "销售部": sales_hm,
        "财务部": finance_hm,
    }
    for title, dept, hc, degree, miny, smin, smax, skills in job_defs:
        jd_text = (
            f"岗位职责：负责 {title} 的开发与交付；"
            f"任职要求：{miny} 年以上相关经验，{degree} 及以上学历。"
        )
        j = JobPost(
            title=title,
            department=dept,
            headcount=hc,
            jd_text=jd_text,
            required_skills=skills,
            min_degree=degree,
            min_years=miny,
            salary_min=smin,
            salary_max=smax,
            hiring_manager_id=(hiring_managers.get(dept) and hiring_managers[dept].id),
            status="open",
            opened_at=date.today() - timedelta(days=random.randint(5, 60)),
        )
        db.add(j)
        jobs.append(j)
    db.flush()

    # ---------- 候选人 ----------
    candidate_defs = [
        ("郑一诺", "research1@example.com", "前端工程师", "字节跳动", 5.0, "bachelor", 28000, 38000,
         ["前端", "JavaScript", "CSS", "React", "Vue", "TypeScript"], [5, 5, 5, 5, 4, 3]),
        ("曹聪", "cong@example.com", "前端工程师", "腾讯", 7.0, "master", 35000, 50000,
         ["前端", "JavaScript", "CSS", "React", "Webpack", "TypeScript"], [5, 5, 4, 5, 5, 5]),
        ("冯浩然", "haoran@example.com", "前端工程师", "美团", 3.0, "bachelor", 22000, 30000,
         ["前端", "JavaScript", "CSS", "Vue"], [4, 4, 4, 4, 0, 0]),
        ("林俊", "linjun@example.com", "后端工程师", "阿里云", 6.0, "bachelor", 35000, 55000,
         ["后端", "Python", "Java", "MySQL", "Redis", "系统设计"], [5, 5, 5, 5, 5, 4]),
        ("韩丽", "hanli@example.com", "后端工程师", "滴滴", 4.0, "bachelor", 30000, 45000,
         ["后端", "Python", "MySQL", "Redis"], [4, 4, 4, 4, 0, 0]),
        ("潘思远", "sipan@example.com", "后端工程师", "网易", 8.0, "master", 40000, 65000,
         ["后端", "Java", "Python", "MySQL", "Redis", "Kafka", "系统设计"], [5, 5, 5, 5, 5, 4, 5]),
        ("蒋一鸣", "yiming@example.com", "产品经理", "小米", 4.0, "bachelor", 25000, 38000,
         ["产品思维", "用户研究", "数据分析", "沟通表达"], [5, 5, 4, 4, 0, 0]),
        ("钱若曦", "ruoxi@example.com", "高级产品经理", "快手", 6.0, "master", 35000, 55000,
         ["产品思维", "用户研究", "数据分析", "商业敏感", "沟通表达"], [5, 5, 5, 5, 5]),
        ("薛平", "xueping@example.com", "销售经理", "美的", 5.0, "bachelor", 20000, 32000,
         ["销售管理", "大客户管理", "沟通表达", "商业敏感"], [4, 5, 5, 4]),
        ("邓洋", "dengyang@example.com", "财务分析师", "京东", 2.0, "bachelor", 12000, 18000,
         ["财务分析", "数据分析"], [4, 3, 0, 0]),
        ("钱宇", "qianyu@example.com", "财务分析师", "联想", 4.0, "master", 18000, 28000,
         ["财务分析", "数据分析", "商业敏感", "沟通表达"], [5, 5, 4, 5]),
        ("范雨欣", "ifine@example.com", "前端工程师", "B站", 4.0, "bachelor", 32000, 48000,
         ["前端", "JavaScript", "React", "Vue", "Webpack"], [5, 5, 5, 5, 4]),
    ]
    candidates: list[Candidate] = []
    for cname, email, title, company, years, degree, esmin, esmax, skills, profs in candidate_defs:
        cand = Candidate(
            name=cname,
            email=email,
            phone=f"138{random.randint(10000000, 99999999)}",
            current_title=title,
            current_company=company,
            years_exp=years,
            degree=degree,
            expected_salary_min=esmin,
            expected_salary_max=esmax,
            resume_text=f"{cname}，{years} 年{title}经验，现就职于{company}。",
            source=random.choice(["招聘网站", "内推", "LinkedIn", "猎头"]),
        )
        db.add(cand)
        candidates.append(cand)
    db.flush()

    # 候选人技能
    for cand, cdef in zip(candidates, candidate_defs):
        skill_names = cdef[8]
        profs = cdef[9]
        for sname, prof in zip(skill_names, profs):
            db.add(
                CandidateSkill(
                    candidate_id=cand.id,
                    skill=sname,
                    proficiency=prof,
                    years_used=round(cand.years_exp * random.uniform(0.5, 1.0), 1),
                )
            )

    # ---------- 申请（招聘漏斗） ----------
    pipeline_template = [
        (0, 0, "screening", "简历筛选", 78.0),
        (1, 0, "interview", "HR 面", 88.5),
        (2, 0, "offer", "Offer 谈判", 65.0),
        (3, 1, "interview", "技术面", 85.0),
        (4, 1, "screening", "简历筛选", 72.0),
        (5, 1, "offer", "Offer 谈判", 92.0),
        (6, 2, "rejected", "已淘汰", 45.0),
        (7, 2, "interview", "终面", 87.0),
        (8, 3, "interview", "HR 面", 78.0),
        (9, 3, "screening", "简历筛选", 70.0),
        (10, 4, "screening", "简历筛选", 82.0),
        (11, 0, "screening", "简历筛选", 60.0),
    ]
    now_dt = now_dt
    applications: list[Application] = []
    for idx, (cand_idx, job_idx, status, round_name, score) in enumerate(pipeline_template):
        if cand_idx >= len(candidates) or job_idx >= len(jobs):
            continue
        app = Application(
            candidate_id=candidates[cand_idx].id,
            job_post_id=jobs[job_idx].id,
            applied_at=now_dt - timedelta(days=random.randint(2, 30)),
            status=status,
            current_round=round_name,
            overall_score=score,
        )
        db.add(app)
        applications.append(app)
    db.flush()

    # 面试安排：给 interview 状态的申请补充面试
    for app in applications:
        if app.status != "interview":
            continue
        interviewer = db.get(Employee, jobs[0].hiring_manager_id) if jobs[0].hiring_manager_id else None
        if not interviewer:
            interviewer = next((e for e in employees if e.department == "技术中心" and e.job_level in ["M1", "M2", "M3"]), None)
        if not interviewer:
            continue
        db.add(
            InterviewSchedule(
                application_id=app.id,
                round_name=app.current_round,
                interviewer_id=interviewer.id,
                scheduled_at=now_dt + timedelta(days=random.randint(1, 7)),
                mode="onsite",
                score=random.randint(3, 5),
                feedback="技术基础扎实，沟通良好。",
                decision="pending",
            )
        )

    # Offer 记录：给 offer 状态的申请
    for app in applications:
        if app.status != "offer":
            continue
        cand = db.get(Candidate, app.candidate_id)
        job = db.get(JobPost, app.job_post_id)
        base = int(job.salary_min + (job.salary_max - job.salary_min) * 0.85)
        bonus = int(base * 0.20)
        equity = int(base * 0.10)
        db.add(
            OfferRecord(
                application_id=app.id,
                base_salary=base,
                bonus=bonus,
                equity=equity,
                total_package=base + bonus + equity,
                compa_ratio=round(base / ((job.salary_min + job.salary_max) / 2), 2),
                start_date=date.today() + timedelta(days=30),
                expires_at=date.today() + timedelta(days=14),
                status="pending",
            )
        )

    # ---------- HRIS 事务：请假 + 考勤 ----------
    sample_employees = random.sample(employees, min(15, len(employees)))
    for emp in sample_employees:
        # 过去 30 天考勤：工作日出勤
        today = date.today()
        for d_offset in range(1, 31):
            d = today - timedelta(days=d_offset)
            if d.weekday() >= 5:
                continue
            late = random.random() < 0.08
            absent = random.random() < 0.03
            check_in = dtime(9, random.randint(0, 30)) if not late else dtime(9, random.randint(31, 59))
            check_out = dtime(18, random.randint(0, 59))
            hours = 8.5 if not absent else 0.0
            db.add(
                AttendanceRecord(
                    employee_id=emp.id,
                    date=d,
                    check_in=check_in,
                    check_out=check_out,
                    is_late=late,
                    is_absent=absent,
                    hours=hours,
                )
            )

    # 几条示例请假
    if len(sample_employees) >= 5:
        for emp, leave_type, days_ago, ndays in [
            (sample_employees[0], "annual", 12, 2),
            (sample_employees[1], "sick", 5, 1),
            (sample_employees[2], "personal", 25, 1),
            (sample_employees[3], "annual", 3, 3),
            (sample_employees[4], "compensatory", 60, 1),
        ]:
            start = date.today() - timedelta(days=days_ago)
            end = start + timedelta(days=ndays - 1)
            db.add(
                LeaveRequest(
                    employee_id=emp.id,
                    leave_type=leave_type,
                    start_date=start,
                    end_date=end,
                    days=float(ndays),
                    reason="年度休假",
                    status=random.choice(["approved", "pending", "approved"]),
                )
            )

    # ================= HRIS · 薪酬与福利 =================

    # 职级 × 城市薪酬带宽
    LEVEL_MEDIAN = {
        "P4": 220000, "P5": 300000, "P6": 400000, "P7": 550000,
        "P8": 750000, "M1": 600000, "M2": 850000, "M3": 1200000,
    }
    cities = ["上海", "北京", "深圳", "杭州"]
    for level, median in LEVEL_MEDIAN.items():
        for city in cities:
            # 一线城市系数差异：上海北京 1.0，深圳 0.95，杭州 0.9
            factor = {"上海": 1.0, "北京": 1.0, "深圳": 0.95, "杭州": 0.90}[city]
            m = int(median * factor)
            db.add(
                SalaryBand(
                    job_level=level,
                    city=city,
                    median=m,
                    minimum=int(m * 0.75),
                    maximum=int(m * 1.30),
                    effective_date=date(2025, 1, 1),
                )
            )
    db.flush()

    # 员工薪酬包：围绕带宽中位波动，刻意让一部分人低于下限
    for emp in employees:
        median = LEVEL_MEDIAN.get(emp.job_level, 300000)
        # 20% 的人低于带宽下限，15% 高于上限，其余落在健康区间
        r = random.random()
        if r < 0.20:
            base = int(median * random.uniform(0.62, 0.74))
        elif r < 0.35:
            base = int(median * random.uniform(1.12, 1.25))
        else:
            base = int(median * random.uniform(0.88, 1.08))
        exp_years = max(0, (date.today() - emp.hire_date).days // 365)
        bonus_pct = 10.0 if emp.job_level.startswith("P") else 20.0
        if emp.job_level in ("P7", "P8", "M2", "M3"):
            bonus_pct += 10.0
        equity = (
            int(base * random.uniform(0.10, 0.25))
            if emp.job_level in ("P7", "P8", "M1", "M2", "M3")
            else 0
        )
        db.add(
            EmployeeCompensation(
                employee_id=emp.id,
                employee_no=emp.employee_no,
                effective_date=date(2025, 1, 1),
                base_salary=base,
                target_bonus_pct=bonus_pct,
                equity_value=equity,
                pay_grade=emp.job_level,
                last_adjust_pct=round(random.uniform(-2.0, 12.0), 1),
                last_adjust_date=date(2025, 1, 1),
            )
        )
    db.flush()

    BENEFIT_PLANS = [
        ("补充医疗保险", "insurance", 3600, True),
        ("年度健康体检", "health", 1200, True),
        ("企业年金", "insurance", 8400, False),
        ("通讯补贴", "allowance", 2400, True),
        ("带薪病假额度", "leave", 0, True),
        ("股权激励计划", "equity", 0, False),
        ("员工心理关怀 EAP", "health", 600, False),
    ]
    plans = []
    for name, category, cost, is_core in BENEFIT_PLANS:
        p = BenefitPlan(
            name=name,
            category=category,
            annual_cost=cost,
            is_core=is_core,
            description=f"{name}（{category}）",
        )
        db.add(p)
        plans.append(p)
    db.flush()

    for emp in employees:
        for p in plans:
            if p.is_core:
                # 核心福利覆盖率保持在 90%~100% 之间，留出少量缺口演示排查
                enrolled = random.random() < 0.94
            else:
                enrolled = random.random() < 0.45
            if enrolled:
                db.add(
                    EmployeeBenefit(
                        employee_id=emp.id,
                        plan_id=p.id,
                        enrolled_at=date(2025, 1, 1),
                        employee_contribution=0,
                        status="active",
                    )
                )
    db.flush()

    # ================= HRIS · 绩效管理 =================

    GOAL_TEMPLATES = [
        "完成核心模块重构并上线",
        "季度营收目标达成",
        "客户满意度提升至 90%",
        "主导一次跨部门协作项目",
        "带领团队完成人才梯队搭建",
        "关键系统可用性提升至 99.9%",
    ]
    for emp in employees[:40]:
        for i in range(random.randint(1, 3)):
            target = float(random.choice([100, 100, 100, 80, 120, 50]))
            actual = round(target * random.uniform(0.35, 1.15), 1)
            status = (
                "completed" if actual >= target
                else "at_risk" if actual >= target * 0.6
                else "missed"
            )
            db.add(
                PerformanceGoal(
                    employee_id=emp.id,
                    period="2025H1",
                    title=f"{random.choice(GOAL_TEMPLATES)}",
                    goal_type=random.choice(["OKR", "KPI"]),
                    weight=round(1.0 / random.randint(1, 3), 2) or 0.5,
                    target_value=target,
                    actual_value=actual,
                    due_date=date(2025, 6, 30),
                    status=status,
                )
            )
    db.flush()

    latest = db.execute(
        select(PerformanceRecord).where(PerformanceRecord.period == "2025H1")
    ).scalars().all()
    perf_by_emp = {p.employee_id: p for p in latest}
    for emp in employees:
        p = perf_by_emp.get(emp.id)
        base_score = p.score if p else random.uniform(2.5, 4.5)
        self_score = round(min(5.0, max(1.0, base_score + random.uniform(-0.3, 1.2))), 1)
        mgr_score = round(min(5.0, max(1.0, base_score + random.uniform(-0.6, 0.4))), 1)
        calibrated = round((mgr_score + self_score) / 2, 1) if random.random() < 0.5 else mgr_score
        label = "S" if calibrated >= 4.5 else "A" if calibrated >= 4.0 else (
            "B" if calibrated >= 3.2 else "C" if calibrated >= 2.5 else "D"
        )
        db.add(
            PerformanceReview(
                employee_id=emp.id,
                period="2025H1",
                self_score=self_score,
                manager_score=mgr_score,
                calibrated_score=calibrated,
                rating_label=label,
                review_date=date(2025, 7, 10),
                comment="",
            )
        )
    db.flush()

    for dep in DEPARTMENTS:
        db.add(
            CalibrationSession(
                department=dep,
                period="2025H1",
                held_at=date(2025, 7, 15),
                participant_count=DEPARTMENTS[dep]["headcount"],
                before_distribution="{}",
                after_distribution="{}",
                adjusted_count=random.randint(0, 3),
                note="部门级绩效校准会",
            )
        )

    # 低绩效员工进入 PIP
    low_performers = [e for e in employees if (perf_by_emp.get(e.id).score if perf_by_emp.get(e.id) else 5) < 2.8]
    for emp in low_performers[:4]:
        db.add(
            ImprovementPlan(
                employee_id=emp.id,
                period="2025H1",
                start_date=date(2025, 7, 20),
                end_date=date(2025, 10, 20),
                reason="连续两个周期绩效未达标",
                target_score=3.0,
                outcome=random.choice(["ongoing", "ongoing", "passed", "failed"]),
            )
        )
    db.flush()

    # ================= HRIS · 培训与开发 =================

    COURSE_DEFS = [
        ("TR001", "新员工入职合规培训", "compliance", "online", 4.0, 200, True, None),
        ("TR002", "数据安全与隐私保护", "compliance", "online", 3.0, 150, True, None),
        ("TR003", "管理者角色认知", "leadership", "classroom", 12.0, 3000, False, None),
        ("TR004", "高潜人才领导力加速营", "leadership", "workshop", 24.0, 8000, False, None),
        ("TR005", "结构化思维与问题解决", "general", "online", 6.0, 800, False, None),
        ("TR006", "高效沟通与跨部门协作", "general", "classroom", 8.0, 2500, False, None),
        ("TR007", "系统架构设计实战", "professional", "workshop", 16.0, 6000, False, None),
        ("TR008", "数据分析与业务洞察", "professional", "online", 10.0, 1800, False, None),
        ("TR009", "销售谈判技巧进阶", "professional", "classroom", 12.0, 4000, False, None),
        ("TR010", "项目管理实战", "general", "online", 14.0, 2200, False, None),
    ]
    comp_list = list(competencies.values())
    courses = []
    for code, name, cat, mode, hours, cost, mandatory, _ in COURSE_DEFS:
        c = TrainingCourse(
            code=code,
            name=name,
            category=cat,
            delivery_mode=mode,
            duration_hours=hours,
            cost_per_head=cost,
            target_competency_id=random.choice(comp_list).id if comp_list else None,
            target_level=random.randint(3, 5),
            provider="内训" if mandatory else random.choice(["内训", "外部机构"]),
            is_mandatory=mandatory,
            description=name,
        )
        db.add(c)
        courses.append(c)
    db.flush()

    mandatory_courses = [c for c in courses if c.is_mandatory]
    for emp in employees:
        # 必修：故意让约 12% 的人没完成，演示合规排查
        for c in mandatory_courses:
            if random.random() < 0.88:
                db.add(
                    TrainingEnrollment(
                        employee_id=emp.id,
                        course_id=c.id,
                        enrolled_at=date(2025, 2, 1),
                        completed_at=date(2025, 3, 1),
                        status="completed",
                        score=round(random.uniform(75, 98), 1),
                        hours_spent=c.duration_hours,
                        feedback_score=round(random.uniform(3.4, 4.8), 1),
                    )
                )
        # 选修
        for c in random.sample([x for x in courses if not x.is_mandatory], k=random.randint(0, 3)):
            done = random.random() < 0.7
            db.add(
                TrainingEnrollment(
                    employee_id=emp.id,
                    course_id=c.id,
                    enrolled_at=date(2025, 3, 1),
                    completed_at=date(2025, 5, 1) if done else None,
                    status="completed" if done else random.choice(["enrolled", "dropped"]),
                    score=round(random.uniform(60, 95), 1) if done else 0.0,
                    hours_spent=c.duration_hours if done else round(c.duration_hours * 0.3, 1),
                    feedback_score=round(random.uniform(3.0, 5.0), 1) if done else 0.0,
                )
            )
    db.flush()

    # ================= HRIS · 人力资源规划 =================

    for dep, cfg in DEPARTMENTS.items():
        planned = cfg["headcount"] + random.randint(0, 4)
        actual = cfg["headcount"]
        db.add(
            HeadcountPlan(
                department=dep,
                period="2025H1",
                planned_headcount=planned,
                actual_headcount=actual,
                open_reqs=random.randint(0, 3),
                budget_amount=planned * 450000,
                actual_cost=actual * random.randint(380000, 470000),
                approved_at=date(2025, 1, 5),
                note="2025 上半年编制计划",
            )
        )

    for dep, cfg in DEPARTMENTS.items():
        for level in cfg["levels"]:
            supply = random.randint(1, 8)
            attrition = round(random.uniform(0.3, 2.5), 1)
            growth = round(random.uniform(0.2, 3.0), 1)
            internal = random.randint(0, supply)
            db.add(
                WorkforceForecast(
                    department=dep,
                    job_level=level,
                    period="2025H2",
                    current_supply=supply,
                    natural_attrition=attrition,
                    demand_growth=growth,
                    internal_supply=internal,
                    external_hire_need=max(0, int(attrition + growth - internal)),
                    scenario="baseline",
                )
            )

    # 离职风险：六因子加权。
    # 按人群分档构造因子，让风险分呈真实分布（约 15% 高风险、35% 中风险、50% 低风险），
    # 否则全部落在中间档，演示不出分级效果。
    for idx, emp in enumerate(employees):
        tenure_years = (date.today() - emp.hire_date).days / 365.25
        p = perf_by_emp.get(emp.id)
        comp = db.execute(
            select(EmployeeCompensation).where(
                EmployeeCompensation.employee_id == emp.id
            )
        ).scalars().first()
        median = LEVEL_MEDIAN.get(emp.job_level, 300000)
        ratio = (comp.base_salary / median) if comp and median else 1.0

        # 以固定间隔分档，保证三档人群都有代表
        bucket = idx % 20
        if bucket < 3:  # 15% 高风险
            level_hint = "high"
        elif bucket < 10:  # 35% 中风险
            level_hint = "medium"
        else:  # 50% 低风险
            level_hint = "low"

        def _factor(low: float, high: float) -> float:
            return round(random.uniform(low, high), 2)

        if level_hint == "high":
            f_tenure = _factor(0.55, 0.95)
            f_perf = _factor(0.45, 0.95)
            # 薪酬竞争力以相对带宽的实际位置为主，再叠加档位保底，
            # 否则全员 compa-ratio 偏高时会把该因子压成 0，失去区分度
            f_comp = round(min(1.0, max(0.55, 1.0 - ratio + _factor(0.10, 0.30))), 2)
            f_promo = _factor(0.60, 0.95)
            f_eng = _factor(0.55, 0.90)
            f_market = _factor(0.60, 0.95)
        elif level_hint == "medium":
            f_tenure = _factor(0.25, 0.60)
            f_perf = _factor(0.25, 0.60)
            f_comp = round(min(1.0, max(0.25, 1.0 - ratio + _factor(-0.05, 0.20))), 2)
            f_promo = _factor(0.30, 0.65)
            f_eng = _factor(0.25, 0.60)
            f_market = _factor(0.25, 0.65)
        else:
            f_tenure = _factor(0.05, 0.35)
            f_perf = _factor(0.05, 0.35)
            f_comp = round(min(1.0, max(0.05, 1.0 - ratio + _factor(-0.10, 0.10))), 2)
            f_promo = _factor(0.05, 0.35)
            f_eng = _factor(0.05, 0.35)
            f_market = _factor(0.05, 0.40)
        score = round(
            (f_tenure * 0.15 + f_perf * 0.15 + f_comp * 0.20
             + f_promo * 0.20 + f_eng * 0.15 + f_market * 0.15) * 100,
            1,
        )
        level = "high" if score >= 70 else "medium" if score >= 45 else "low"
        top = max(
            [("factor_tenure", f_tenure), ("factor_performance", f_perf),
             ("factor_compensation", f_comp), ("factor_promotion", f_promo),
             ("factor_engagement", f_eng), ("factor_market", f_market)],
            key=lambda x: x[1],
        )[0]
        reasons = {
            "factor_tenure": "入职时间较短，组织认同尚未建立",
            "factor_performance": "绩效表现好但缺少相应认可",
            "factor_compensation": "薪酬低于市场对标水平",
            "factor_promotion": "同一职级停留时间过长",
            "factor_engagement": "敬业度调查得分偏低",
            "factor_market": "所在职能外部机会活跃",
        }
        db.add(
            AttritionRisk(
                employee_id=emp.id,
                period="2025H1",
                risk_score=score,
                risk_level=level,
                factor_tenure=f_tenure,
                factor_performance=f_perf,
                factor_compensation=f_comp,
                factor_promotion=f_promo,
                factor_engagement=f_eng,
                factor_market=f_market,
                key_reason=reasons[top],
                retention_action="",
            )
        )

    # ================= HRIS · 员工关系管理（扩展） =================

    CASE_TYPES = ["dispute", "grievance", "care", "compliance"]
    for emp in random.sample(employees, k=min(14, len(employees))):
        opened = date.today() - timedelta(days=random.randint(1, 90))
        closed = opened + timedelta(days=random.randint(3, 40)) if random.random() < 0.6 else None
        db.add(
            RelationCase(
                employee_id=emp.id,
                case_type=random.choice(CASE_TYPES),
                severity=random.choice(["low", "medium", "high"]),
                opened_at=opened,
                closed_at=closed,
                owner="HRBP",
                description="员工关系事件记录",
                status="closed" if closed else "open",
                escalation_risk=round(random.uniform(0.1, 0.95), 2),
            )
        )

    for emp in employees:
        overall = round(random.uniform(2.4, 4.8), 1)
        db.add(
            EngagementSurvey(
                employee_id=emp.id,
                period="2025H1",
                overall_score=overall,
                score_work=round(random.uniform(2.8, 4.8), 1),
                score_manager=round(random.uniform(2.5, 4.7), 1),
                score_growth=round(random.uniform(2.2, 4.6), 1),
                score_reward=round(random.uniform(2.0, 4.5), 1),
                score_balance=round(random.uniform(2.4, 4.8), 1),
                is_promoter=overall >= 4.0 and random.random() < 0.8,
                comment="",
            )
        )

    db.commit()
    return {
        "employees": len(employees),
        "competencies": len(competencies),
        "org_units": len(DEPARTMENTS) * 3 + 1,
        "talent_pools": 3,
        "development_programs": 5,
        "mentorship_pairs": 14,
        "periods": PERIODS,
        "hris": {
            "recruitment": {
                "job_posts": len(jobs),
                "candidates": len(candidates),
                "applications": len(applications),
            },
            "compensation": {
                "salary_bands": len(LEVEL_MEDIAN) * len(cities),
                "compensation_records": len(employees),
                "benefit_plans": len(plans),
            },
            "performance": {
                "goals": len(db.execute(select(PerformanceGoal)).scalars().all()),
                "reviews": len(employees),
            },
            "employee_relations": {
                "relation_cases": 14,
                "engagement_surveys": len(employees),
            },
            "learning": {
                "courses": len(courses),
                "enrollments": len(db.execute(select(TrainingEnrollment)).scalars().all()),
            },
            "workforce": {
                "headcount_plans": len(DEPARTMENTS),
                "attrition_records": len(employees),
            },
        },
    }


def main():
    parser = argparse.ArgumentParser(description="生成 smart-talent-agent 演示数据")
    parser.add_argument("--keep", action="store_true", help="保留已有数据")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        if not args.keep:
            print("清空旧数据...")
            clear_all(db)
        stats = seed(db)
        print("种子数据生成完成：")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    except Exception as exc:
        db.rollback()
        print(f"生成失败：{exc}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
