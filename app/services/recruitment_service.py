"""HRIS · 招聘管理域（Recruitment）确定性计算。

- 简历筛选：技能 / 经验 / 学历 / 期望薪资 / 职级五维加权打分，自动分档
- 漏斗统计：screening → interview → offer → hired 各阶段转化率
- 面试安排：按部门招聘经理 + 资深面试官 + HR 生成推荐人与时段
- 智能定薪：基于匹配分、岗位预算、经验年限给出三段式薪酬建议
- 录用转换：候选人转为正式员工，并初始化绩效 / 潜力记录

本模块的全部打分逻辑由 Python 完成，不依赖任何大模型输出。
"""

from collections import Counter
from datetime import date, datetime, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import (
    Application,
    Candidate,
    CandidateSkill,
    Employee,
    InterviewSchedule,
    JobPost,
    OfferRecord,
    PerformanceRecord,
    PotentialAssessment,
)


# ------------------ 常量 ------------------

DEGREE_RANK = {"high_school": 0, "associate": 1, "bachelor": 2, "master": 3, "phd": 4}

PIPELINE_STAGES = ["screening", "interview", "offer", "hired"]

PIPELINE_LABEL = {
    "screening": "简历筛选",
    "interview": "面试",
    "offer": "Offer 谈判",
    "hired": "已入职",
    "rejected": "已淘汰",
}

TIER_RULE = [
    (85, "强烈推荐面试"),
    (70, "推荐面试"),
    (55, "待定（可面试）"),
    (0, "不推荐"),
]


# ------------------ 简历筛选 ------------------


def _score_one(candidate: Candidate, skills: list[CandidateSkill], job: JobPost) -> dict:
    """对单个候选人打分，返回加权明细。"""
    jd_skills = [s.strip().lower() for s in (job.required_skills or "").split(",") if s.strip()]
    cand_skill_names = {s.skill.lower() for s in skills}

    # 技能匹配（40%）
    if jd_skills:
        matched = sum(1 for s in jd_skills if s in cand_skill_names)
        skill_score = round(matched / len(jd_skills) * 100, 2)
        matched_skills = [s for s in jd_skills if s in cand_skill_names]
        missing_skills = [s for s in jd_skills if s not in cand_skill_names]
    else:
        matched = 0
        skill_score = 60.0
        matched_skills = []
        missing_skills = []

    # 经验（20%）
    exp = candidate.years_exp
    min_exp = job.min_years
    if min_exp <= 0:
        exp_score = 100.0
    elif exp >= min_exp:
        exp_score = 100.0
    elif exp >= min_exp - 2:
        exp_score = 80.0
    elif exp >= min_exp - 5:
        exp_score = 40.0
    else:
        exp_score = 0.0

    # 学历（15%）
    cand_rank = DEGREE_RANK.get((candidate.degree or "").lower(), 1)
    req_rank = DEGREE_RANK.get((job.min_degree or "").lower(), 1)
    diff = cand_rank - req_rank
    if diff >= 0:
        degree_score = 100.0
    elif diff == -1:
        degree_score = 60.0
    else:
        degree_score = 20.0

    # 期望薪资（15%）：期望中位 vs 预算上限
    expected_mid = (
        candidate.expected_salary_min + candidate.expected_salary_max
    ) / 2
    salary_max = job.salary_max or 1
    if expected_mid <= salary_max:
        salary_score = 100.0
    elif expected_mid <= salary_max * 1.2:
        salary_score = 60.0
    else:
        salary_score = 20.0

    # 当前职级（10%）：无量化字段时按经验近似
    title_score = min(100.0, 40.0 + candidate.years_exp * 8)

    overall = round(
        skill_score * 0.40
        + exp_score * 0.20
        + degree_score * 0.15
        + salary_score * 0.15
        + title_score * 0.10,
        2,
    )

    tier = "不推荐"
    for threshold, label in TIER_RULE:
        if overall >= threshold:
            tier = label
            break

    return {
        "overall_score": overall,
        "tier": tier,
        "skill_score": skill_score,
        "skill_matched": matched,
        "skill_total": len(jd_skills),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "exp_score": exp_score,
        "degree_score": degree_score,
        "salary_score": salary_score,
        "title_score": title_score,
    }


def _get_job(db: Session, key: str | int | None) -> JobPost | None:
    if key is None:
        return db.execute(select(JobPost).order_by(desc(JobPost.id))).scalars().first()
    if isinstance(key, int) or (isinstance(key, str) and key.isdigit()):
        return db.get(JobPost, int(key))
    stmt = select(JobPost).where(JobPost.title.contains(str(key)))
    return db.execute(stmt).scalars().first()


def _get_candidate(db: Session, key: str | int) -> Candidate | None:
    if isinstance(key, int):
        return db.get(Candidate, key)
    cand = db.execute(
        select(Candidate).where(Candidate.name == key)
    ).scalars().first()
    if cand:
        return cand
    return db.execute(
        select(Candidate).where(Candidate.email == key)
    ).scalars().first()


def screen_candidate(
    db: Session, candidate_key: str | int, job_key: str | int | None = None
) -> dict:
    """对单个候选人按指定 JD 评分。"""
    candidate = _get_candidate(db, candidate_key)
    if not candidate:
        return {"error": f"未找到候选人：{candidate_key}"}

    job = _get_job(db, job_key)
    if not job:
        return {"error": "未找到对应招聘需求"}

    skills = list(
        db.execute(
            select(CandidateSkill).where(CandidateSkill.candidate_id == candidate.id)
        ).scalars().all()
    )
    detail = _score_one(candidate, skills, job)
    detail["candidate"] = {
        "id": candidate.id,
        "name": candidate.name,
        "current_title": candidate.current_title,
        "current_company": candidate.current_company,
        "years_exp": candidate.years_exp,
        "degree": candidate.degree,
        "expected_salary": [
            candidate.expected_salary_min,
            candidate.expected_salary_max,
        ],
        "source": candidate.source,
    }
    detail["job"] = {
        "id": job.id,
        "title": job.title,
        "department": job.department,
        "required_skills": job.required_skills.split(","),
        "salary_range": [job.salary_min, job.salary_max],
    }
    return detail


def screen_for_job(db: Session, job_key: str | int, top: int = 10) -> dict:
    """为某个职位评估所有候选人，按 Tier + 分排序返回前 N 名。"""
    job = _get_job(db, job_key)
    if not job:
        return {"error": "未找到对应招聘需求"}

    candidates = list(db.execute(select(Candidate)).scalars().all())
    skill_map: dict[int, list[CandidateSkill]] = {}
    if candidates:
        rows = db.execute(
            select(CandidateSkill).where(
                CandidateSkill.candidate_id.in_([c.id for c in candidates])
            )
        ).scalars().all()
        for s in rows:
            skill_map.setdefault(s.candidate_id, []).append(s)

    evaluated = []
    for c in candidates:
        detail = _score_one(c, skill_map.get(c.id, []), job)
        detail["candidate_id"] = c.id
        detail["name"] = c.name
        detail["current_company"] = c.current_company
        detail["current_title"] = c.current_title
        evaluated.append(detail)

    evaluated.sort(key=lambda x: -x["overall_score"])

    return {
        "job": {
            "id": job.id,
            "title": job.title,
            "department": job.department,
            "required_skills": job.required_skills.split(","),
            "salary_range": [job.salary_min, job.salary_max],
        },
        "total": len(evaluated),
        "ranking": evaluated[:top],
        "tier_summary": dict(
            Counter(e["tier"] for e in evaluated)
        ),
    }


# ------------------ 智能定薪 ------------------


def suggest_offer(
    db: Session,
    candidate_key: str | int,
    job_key: str | int,
    save: bool = False,
) -> dict:
    """为候选人产出 Offer 建议。"""
    candidate = _get_candidate(db, candidate_key)
    if not candidate:
        return {"error": f"未找到候选人：{candidate_key}"}
    job = _get_job(db, job_key)
    if not job:
        return {"error": "未找到对应招聘需求"}

    # 先打分（用以决定 base 档位）
    skills = list(
        db.execute(
            select(CandidateSkill).where(CandidateSkill.candidate_id == candidate.id)
        ).scalars().all()
    )
    score = _score_one(candidate, skills, job)

    overall = score["overall_score"]
    salary_min = job.salary_min
    salary_max = job.salary_max
    salary_mid = (salary_min + salary_max) / 2

    # base 按分数落在区间内
    if overall >= 85:
        base_pct = 0.95
    elif overall >= 70:
        base_pct = 0.80
    elif overall >= 55:
        base_pct = 0.60
    else:
        base_pct = 0.50

    suggested_base = int(salary_min + (salary_max - salary_min) * base_pct)

    # 期望校验
    expected_mid = (candidate.expected_salary_min + candidate.expected_salary_max) / 2
    if expected_mid > salary_max * 1.15:
        expected_warning = "候选人期望薪资显著超过岗位预算"
    elif expected_mid > salary_max:
        expected_warning = "候选人期望略高于岗位预算，需沟通"
    else:
        expected_warning = "候选人期望在岗位预算内"

    # 奖金：按经验年限
    exp = candidate.years_exp
    if exp >= 10:
        bonus_rate = 0.30
    elif exp >= 6:
        bonus_rate = 0.20
    elif exp >= 3:
        bonus_rate = 0.15
    else:
        bonus_rate = 0.10
    suggested_bonus = int(suggested_base * bonus_rate)

    # RSU / 股权：高分高经验
    if overall >= 85 and exp >= 5:
        equity = int(suggested_base * 0.20)
    elif overall >= 70 and exp >= 3:
        equity = int(suggested_base * 0.10)
    else:
        equity = 0

    total = suggested_base + suggested_bonus + equity
    compa_ratio = round(suggested_base / salary_mid, 2) if salary_mid else 0.0

    rationale = (
        f"候选人综合分 {overall}（{score['tier']}），匹配 {score['skill_matched']}/"
        f"{score['skill_total']} 项关键技能；经验 {exp} 年对岗位 {job.min_years} 年要求"
        f"{'达标' if exp >= job.min_years else '略低'}；"
        f"base 落在预算的 {round(base_pct * 100)}% 位置（compa-ratio {compa_ratio}），"
        f"奖金按经验年限设 {round(bonus_rate * 100)}%。"
    )

    result = {
        "candidate": {
            "id": candidate.id,
            "name": candidate.name,
            "current_title": candidate.current_title,
            "years_exp": candidate.years_exp,
        },
        "job": {
            "id": job.id,
            "title": job.title,
            "department": job.department,
            "salary_range": [salary_min, salary_max],
        },
        "score": score,
        "suggested_base": suggested_base,
        "suggested_bonus": suggested_bonus,
        "suggested_equity": equity,
        "total_package": total,
        "compa_ratio": compa_ratio,
        "bonus_rate": bonus_rate,
        "expected_warning": expected_warning,
        "expected_mid": int(expected_mid),
        "rationale": rationale,
    }

    if save:
        # 找到或创建申请
        app = db.execute(
            select(Application).where(
                Application.candidate_id == candidate.id,
                Application.job_post_id == job.id,
            )
        ).scalars().first()
        if not app:
            app = Application(
                candidate_id=candidate.id,
                job_post_id=job.id,
                applied_at=datetime.now(),
                status="offer",
                current_round="Offer 谈判",
                overall_score=overall,
            )
            db.add(app)
            db.flush()

        today = date.today()
        offer = OfferRecord(
            application_id=app.id,
            base_salary=suggested_base,
            bonus=suggested_bonus,
            equity=equity,
            total_package=total,
            compa_ratio=compa_ratio,
            start_date=today + timedelta(days=30),
            expires_at=today + timedelta(days=14),
            status="pending",
        )
        db.add(offer)
        db.commit()
        result["saved_offer_id"] = offer.id

    return result


# ------------------ 漏斗统计 ------------------


def recruitment_funnel(db: Session, department: str | None = None) -> dict:
    """招聘漏斗与转化率。"""
    stmt = (
        select(Application.status, func.count(Application.id))
        .group_by(Application.status)
    )
    if department:
        stmt = stmt.join(JobPost, JobPost.id == Application.job_post_id).where(
            JobPost.department == department
        )
    counts = dict(db.execute(stmt).all())

    total_received = sum(counts.values())
    total_rejected = counts.get("rejected", 0)
    total_hired = counts.get("hired", 0)
    total_screening = counts.get("screening", 0)
    total_interview = counts.get("interview", 0)
    total_offer = counts.get("offer", 0)

    active_count = total_received - total_rejected - total_hired

    def pct(part: int, whole: int) -> float:
        return round(part / whole * 100, 1) if whole else 0.0

    return {
        "department": department or "全部部门",
        "received": total_received,
        "active": active_count,
        "rejected": total_rejected,
        "hired": total_hired,
        "stage_counts": {
            "简历筛选": total_screening,
            "面试": total_interview,
            "Offer 谈判": total_offer,
            "已入职": total_hired,
            "已淘汰": total_rejected,
        },
        "conversion_rates": {
            "筛选→面试": pct(total_interview, max(total_screening + total_interview, 1)),
            "面试→Offer": pct(total_offer, max(total_interview + total_offer, 1)),
            "Offer→入职": pct(total_hired, max(total_offer + total_hired, 1)),
            "整体淘汰率": pct(total_rejected, total_received),
        },
    }


# ------------------ 面试安排 ------------------


def recommend_interviewers(db: Session, job: JobPost) -> list[dict]:
    """推荐 3 位面试官：招聘经理 + 同部门 P7+ 资深员工 + HR。"""
    candidates: list[Employee] = []
    if job.hiring_manager_id:
        mgr = db.get(Employee, job.hiring_manager_id)
        if mgr:
            candidates.append(mgr)
    seniors = list(
        db.execute(
            select(Employee).where(
                Employee.department == job.department,
                Employee.status == "在职",
                Employee.id != (job.hiring_manager_id or 0),
                Employee.job_level.in_(["P7", "P8", "M1", "M2", "M3"]),
            ).limit(2)
        ).scalars().all()
    )
    candidates.extend(seniors)
    hr = db.execute(
        select(Employee).where(Employee.department == "人力资源部")
        .order_by(desc(Employee.job_level))
        .limit(1)
    ).scalars().first()
    if hr:
        candidates.append(hr)

    seen: set[int] = set()
    unique: list[Employee] = []
    for c in candidates:
        if c.id not in seen:
            unique.append(c)
            seen.add(c.id)

    return [
        {
            "id": e.id,
            "name": e.name,
            "department": e.department,
            "position_title": e.position_title,
            "job_level": e.job_level,
            "role": (
                "招聘经理"
                if job.hiring_manager_id == e.id
                else "技术面试官" if e.department == job.department
                else "HR 面试官"
            ),
        }
        for e in unique[:3]
    ]


def propose_interview_slots(
    job: JobPost, start: date | None = None, days: int = 7, per_day: int = 2
) -> list[dict]:
    """生成未来 N 天的工作日可推荐时段。"""
    slots: list[dict] = []
    cur = start or date.today()
    pointer = 0
    while pointer < days:
        candidate = cur + timedelta(days=pointer + 1)
        if candidate.weekday() >= 5:
            pointer += 1
            continue
        for hour in (10, 14)[:per_day]:
            slots.append(
                {
                    "date": candidate.isoformat(),
                    "time": f"{hour:02d}:00",
                    "mode": "线上",
                }
            )
        pointer += 1
    return slots


# ------------------ 录用转换 ------------------


def convert_to_employee(
    db: Session, application_id: int, target_period: str | None = None
) -> dict:
    """将通过的候选人转为正式员工，并初始化绩效/潜力记录。"""
    app = db.get(Application, application_id)
    if not app:
        return {"error": f"未找到申请：{application_id}"}

    candidate = db.get(Candidate, app.candidate_id)
    job = db.get(JobPost, app.job_post_id)
    if not candidate or not job:
        return {"error": "申请关联数据缺失"}

    # 生成员工编号
    max_no = db.execute(
        select(func.max(Employee.employee_no))
    ).scalar()
    if max_no and max_no.startswith("E"):
        try:
            next_no = f"E{int(max_no[1:]) + 1:04d}"
        except ValueError:
            next_no = f"E{app.candidate_id + 100:04d}"
    else:
        next_no = f"E{app.candidate_id + 100:04d}"

    emp = Employee(
        employee_no=next_no,
        name=candidate.name,
        department=job.department,
        position_title=job.title,
        job_family="招聘转入",
        job_level="P5",
        hire_date=date.today(),
        city="-",
        status="在职",
    )
    db.add(emp)
    db.flush()

    period = target_period or "2025H1"
    db.add(
        PerformanceRecord(
            employee_id=emp.id, period=period, score=3.5, grade="B"
        )
    )
    db.add(
        PotentialAssessment(
            employee_id=emp.id,
            period=period,
            potential_score=3.4,
            learning_agility=3.5,
            leadership=3.0,
            mobility=False,
        )
    )

    app.status = "hired"
    db.commit()

    return {
        "converted_employee_id": emp.id,
        "employee_no": next_no,
        "name": emp.name,
        "department": emp.department,
        "position_title": emp.position_title,
    }