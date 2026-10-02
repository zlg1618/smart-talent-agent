"""ATS Tool：简历筛选、智能定薪、面试安排、漏斗统计。"""

import re
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Candidate, JobPost
from app.services import ats_service


def _find_candidate(db: Session, message: str) -> Candidate | None:
    candidates = list(db.execute(select(Candidate).distinct()).scalars().all())
    for c in candidates:
        if c.name and c.name in message:
            return c
    return None


def _find_job(db: Session, message: str) -> JobPost | None:
    jobs = list(db.execute(select(JobPost)).scalars().all())
    for job in jobs:
        if job.title and job.title in message:
            return job
    for job in jobs:
        if job.department and job.department in message:
            return job
    return None


def run_screen_candidate(db: Session, message: str) -> dict:
    candidate = _find_candidate(db, message)
    job = _find_job(db, message)
    if not candidate:
        return {"error": "请指定候选人姓名，例如：给候选人李雷做一次简历评估"}
    if not job:
        return {"error": "请指定目标岗位，例如：评估他能否胜任高级前端开发岗位"}
    return ats_service.screen_candidate(db, candidate.id, job.id)


def run_screen_for_job(db: Session, message: str) -> dict:
    candidate = _find_candidate(db, message)
    if candidate:
        job = _find_job(db, message)
        if not job:
            return {"error": "请指定目标岗位"}
        return ats_service.screen_candidate(db, candidate.id, job.id)
    job = _find_job(db, message)
    if not job:
        return {"error": "请指定目标岗位，例如：对高级前端开发岗位做一次简历筛选"}
    return ats_service.screen_for_job(db, job.id)


def run_suggest_offer(db: Session, message: str, save: bool = False) -> dict:
    candidate = _find_candidate(db, message)
    job = _find_job(db, message)
    if not candidate:
        return {"error": "请指定候选人姓名，例如：给候选人李雷定 Offer"}
    if not job:
        return {"error": "请指定目标岗位，例如：给候选人李雷定 Offer 高级前端开发岗位"}
    return ats_service.suggest_offer(db, candidate.id, job.id, save=save)


def run_funnel(db: Session, department: str | None = None) -> dict:
    return ats_service.recruitment_funnel(db, department=department)


def run_interview_proposal(db: Session, message: str) -> dict:
    job = _find_job(db, message)
    if not job:
        return {"error": "请指定岗位，例如：给高级前端开发岗位安排面试"}

    interviewers = ats_service.recommend_interviewers(db, job)
    slots = ats_service.propose_interview_slots(job)

    return {
        "job": {
            "id": job.id,
            "title": job.title,
            "department": job.department,
            "salary_range": [job.salary_min, job.salary_max],
        },
        "recommended_interviewers": interviewers,
        "available_slots": slots[:6],
        "total_slots": len(slots),
    }


_DAYS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*天")


def extract_leave_days(message: str) -> float | None:
    m = _DAYS_RE.search(message)
    return float(m.group(1)) if m else None


def run_propose_interview(db: Session, message: str) -> dict:
    return run_interview_proposal(db, message)