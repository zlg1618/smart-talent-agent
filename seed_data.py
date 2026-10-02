"""种子数据生成。

生成一套可演示的模拟人才数据：员工、绩效、潜力、能力模型、
关键岗位、继任关系、学习资源、部门诊断指标。

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
    AttendanceRecord,
    Candidate,
    CandidateSkill,
    Competency,
    Course,
    DepartmentMetric,
    Employee,
    EmployeeCompetency,
    IDP,
    InterviewSchedule,
    JobPost,
    KeyPosition,
    LeaveRequest,
    OfferRecord,
    PerformanceRecord,
    PotentialAssessment,
    SuccessionPlan,
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

COURSE_FORMS = ["项目", "导师", "线上", "线下"]

READINESS = ["ready_now", "ready_1y", "ready_2y", "not_ready"]

# 部门诊断指标：刻意制造健康 / 关注 / 预警三种状态，便于演示
DEPARTMENT_METRICS = [
    ("技术中心", 22, 3.8, 0.08, 3.72, 0.18, 8.5, 2),
    ("产品部", 12, 2.6, 0.13, 3.35, 0.12, 6.0, -1),
    ("销售部", 16, 1.4, 0.26, 2.92, 0.07, 12.0, -6),
    ("人力资源部", 9, 4.2, 0.06, 3.68, 0.16, 4.5, 1),
    ("财务部", 8, 1.2, 0.09, 3.41, 0.11, 2.5, 0),
]


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
        OfferRecord,
        InterviewSchedule,
        Application,
        CandidateSkill,
        Candidate,
        JobPost,
        AttendanceRecord,
        LeaveRequest,
        IDP,
        SuccessionPlan,
        KeyPosition,
        EmployeeCompetency,
        Course,
        Competency,
        PotentialAssessment,
        PerformanceRecord,
        DepartmentMetric,
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

    # ---------- 学习资源 ----------
    for comp_name, comp in competencies.items():
        for form in COURSE_FORMS:
            target = random.randint(3, 5)
            db.add(
                Course(
                    name=f"{comp_name}·{form}提升（{target} 级）",
                    competency_id=comp.id,
                    target_level=target,
                    duration_hours={"项目": 40, "导师": 12, "线上": 8, "线下": 16}[form],
                    form=form,
                )
            )

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

    # ---------- 关键岗位 ----------
    key_position_defs = [
        ("技术总监", "技术中心", "M3", "高"),
        ("架构师", "技术中心", "P8", "高"),
        ("技术经理", "技术中心", "M1", "中"),
        ("产品总监", "产品部", "M2", "高"),
        ("高级产品经理", "产品部", "P7", "中"),
        ("销售总监", "销售部", "M2", "高"),
        ("区域经理", "销售部", "M1", "中"),
        ("HR 总监", "人力资源部", "M2", "高"),
        ("组织发展经理", "人力资源部", "P6", "中"),
        ("财务总监", "财务部", "M1", "高"),
        ("财务经理", "财务部", "P6", "低"),
    ]

    positions = []
    for title, dept, level, criticality in key_position_defs:
        candidates = [e for e in employees if e.department == dept]
        incumbent = random.choice(candidates) if candidates else None
        pos = KeyPosition(
            title=title,
            department=dept,
            job_level=level,
            incumbent_id=incumbent.id if incumbent else None,
            criticality=criticality,
        )
        db.add(pos)
        positions.append((pos, dept))
    db.flush()

    # ---------- 继任关系 ----------
    # 刻意让两个岗位没有候选人，制造继任风险
    no_successor_idx = {2, 10}
    for i, (pos, dept) in enumerate(positions):
        if i in no_successor_idx:
            continue
        pool = [e for e in employees if e.department == dept and e.id != pos.incumbent_id]
        if not pool:
            continue
        count = random.choice([1, 2, 2, 3])
        chosen = random.sample(pool, min(count, len(pool)))
        for emp in chosen:
            db.add(
                SuccessionPlan(
                    key_position_id=pos.id,
                    successor_id=emp.id,
                    readiness=random.choice(READINESS),
                    note=None,
                )
            )

    # ---------- 部门诊断指标 ----------
    for dept, headcount, tenure, turnover, perf, hp, span, change in DEPARTMENT_METRICS:
        db.add(
            DepartmentMetric(
                department=dept,
                period="2025H1",
                headcount=headcount,
                avg_tenure=tenure,
                turnover_rate=turnover,
                avg_performance=perf,
                high_potential_ratio=hp,
                span_of_control=span,
                headcount_change=change,
            )
        )

    # ---------- 示例 IDP ----------
    sample = employees[:5]
    goals = [
        "一年内向技术经理角色过渡",
        "补齐数据分析能力，支撑业务决策",
        "提升跨部门协作效率，主导重点项目",
        "强化团队领导能力，储备管理通道",
        "深化专业纵深，走专家序列",
    ]
    for emp, goal in zip(sample, goals):
        comp = random.choice(list(competencies.values()))
        db.add(
            IDP(
                employee_id=emp.id,
                period="2025H1",
                goal=goal,
                competency_id=comp.id,
                action_type=random.choice(["项目", "导师", "培训", "轮岗"]),
                action_name=f"{comp.name}专项提升",
                status="进行中",
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

    db.commit()
    return {
        "employees": len(employees),
        "competencies": len(competencies),
        "key_positions": len(positions),
        "periods": PERIODS,
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
