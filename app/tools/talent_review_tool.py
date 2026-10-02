"""人才盘点 Tool：封装九宫格计算服务。"""

from sqlalchemy.orm import Session

from app.services import talent_review_service


def run_talent_review(
    db: Session,
    department: str | None = None,
    period: str | None = None,
    job_level: str | None = None,
    only_grid: list[str] | None = None,
) -> dict:
    """生成九宫格人才盘点结果。"""
    return talent_review_service.build_talent_review(
        db,
        department=department,
        period=period,
        job_level=job_level,
        only_grid=only_grid,
    )


def run_locate_employee(db: Session, name: str, period: str | None = None) -> dict:
    """定位单个员工的九宫格位置。"""
    result = talent_review_service.locate_employee(db, name, period)
    if not result:
        return {"error": f"数据库中未找到员工：{name}"}
    return result
