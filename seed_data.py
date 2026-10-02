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
from datetime import date

from sqlalchemy import delete, select

from app.config.database import SessionLocal, init_db
from app.models import (
    Competency,
    Course,
    DepartmentMetric,
    Employee,
    EmployeeCompetency,
    IDP,
    KeyPosition,
    PerformanceRecord,
    PotentialAssessment,
    SuccessionPlan,
)

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
