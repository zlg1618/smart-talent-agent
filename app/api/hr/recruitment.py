"""HRIS · 招聘管理域接口：JD、简历筛选、Offer、面试、漏斗。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.tools import recruitment_tool

router = APIRouter(prefix="/recruitment", tags=["HRIS-招聘管理"])


@router.get("/jobs")
def jobs(db: Session = Depends(get_db)):
    from sqlalchemy import select

    from app.models import JobPost

    rows = list(db.execute(select(JobPost)).scalars().all())
    return [
        {
            "id": j.id,
            "req_no": j.req_no,
            "title": j.title,
            "department": j.department,
            "headcount": j.headcount,
            "status": j.status,
            "salary_range": [j.salary_min, j.salary_max],
            "required_skills": j.required_skills.split(","),
            "min_degree": j.min_degree,
            "min_years": j.min_years,
        }
        for j in rows
    ]


@router.post("/screen")
def screen(
    job: str = Query(..., description="目标岗位标题或 ID"),
    candidate: str | None = Query(None, description="指定候选人姓名或 ID"),
    top: int = Query(10, description="未指定候选人时返回前 N"),
    db: Session = Depends(get_db),
):
    message = f"{candidate or ''} {job}".strip()
    if candidate:
        return recruitment_tool.run_screen_candidate(db, message)
    return recruitment_tool.run_screen_for_job(db, message)


@router.post("/offer")
def offer(
    candidate: str = Query(..., description="候选人姓名或 ID"),
    job: str = Query(..., description="目标岗位"),
    save: bool = Query(False, description="是否落库 Offer 记录"),
    db: Session = Depends(get_db),
):
    return recruitment_tool.run_suggest_offer(db, f"{candidate} {job}", save=save)


@router.get("/funnel")
def funnel(
    department: str | None = Query(None, description="部门过滤"),
    db: Session = Depends(get_db),
):
    return recruitment_tool.run_funnel(db, department=department)


@router.post("/interview/proposal")
def interview_proposal(
    job: str = Query(..., description="岗位标题"),
    db: Session = Depends(get_db),
):
    return recruitment_tool.run_interview_proposal(db, job)
