"""员工与部门接口。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.services import employee_service

router = APIRouter(prefix="/api/employees", tags=["员工"])


@router.get("")
def list_employees(
    department: str | None = Query(None, description="部门过滤"),
    job_level: str | None = Query(None, description="职级过滤，如 P6"),
    keyword: str | None = Query(None, description="姓名或岗位关键词"),
    db: Session = Depends(get_db),
):
    employees = employee_service.list_employees(
        db, department=department, job_level=job_level, keyword=keyword
    )
    return [
        {
            "id": e.id,
            "employee_no": e.employee_no,
            "name": e.name,
            "department": e.department,
            "position_title": e.position_title,
            "job_family": e.job_family,
            "job_level": e.job_level,
            "city": e.city,
            "hire_date": str(e.hire_date),
            "status": e.status,
        }
        for e in employees
    ]


@router.get("/departments")
def departments(db: Session = Depends(get_db)):
    return {"departments": employee_service.list_departments(db)}


@router.get("/periods")
def periods(db: Session = Depends(get_db)):
    from sqlalchemy import desc, select

    from app.models import PerformanceRecord

    rows = (
        db.execute(
            select(PerformanceRecord.period)
            .distinct()
            .order_by(desc(PerformanceRecord.period))
        )
        .scalars()
        .all()
    )
    return {"periods": list(rows)}
