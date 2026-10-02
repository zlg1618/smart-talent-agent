"""HRIS 适配器接入接口。

通过 ?backend=local|sap_successfactors 切换适配器，
六大模块（招聘 / 薪酬福利 / 绩效 / 员工关系 / 培训 / 人力规划）共用同一套通道。

默认 backend=local，直接读写本地 SQLite / MySQL；
对接 SAP SuccessFactors 需配置 SAP_SF_* 环境变量。
"""

import os
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.integrations import (
    HRISCapability,
    LocalHRISAdapter,
    SAPSuccessFactorsAdapter,
    build_sf_adapter_from_env,
)
from app.integrations.hris_adapter import (
    AttendanceRecordDTO,
    CompensationDTO,
    HeadcountDTO,
    HRISEmployee,
    LeaveRequestDTO,
    PerformanceReviewDTO,
    TrainingRecordDTO,
)

router = APIRouter(prefix="/api/integrations", tags=["HRIS 集成"])


def _adapter(backend: str, db: Session):
    backend = backend.lower()
    if backend == "local":
        return LocalHRISAdapter(db)
    if backend == "sap_successfactors":
        sf = build_sf_adapter_from_env()
        if sf is None:
            raise HTTPException(
                400,
                "SAP SuccessFactors 适配器未配置：请设置 SAP_SF_BASE_URL / SAP_SF_COMPANY_ID "
                "等环境变量后再调用。详细配置见 env.example。",
            )
        return sf
    raise HTTPException(400, f"未知的 backend：{backend}")


def _require_capability(adapter, capability: str):
    """调用模块接口前声明能力，避免打到不支持的端点。"""
    if not adapter.supports(capability):
        raise HTTPException(
            400,
            f"适配器 {adapter.name} 不支持该模块："
            f"{HRISCapability.LABELS.get(capability, capability)}",
        )


@router.get("/ping")
def ping(
    backend: str = Query("local"),
    db: Session = Depends(get_db),
):
    return _adapter(backend, db).ping()


@router.get("/employee/{employee_no}")
def get_employee(
    employee_no: str,
    backend: str = Query("local"),
    db: Session = Depends(get_db),
):
    emp = _adapter(backend, db).get_employee(employee_no)
    if not emp:
        raise HTTPException(404, "未找到员工")
    return emp.__dict__


class EmployeePayload(BaseModel):
    employee_no: str
    name: str
    department: str
    position_title: str
    job_level: str
    hire_date: date
    city: str = "-"
    status: str = "在职"


class AttendancePayload(BaseModel):
    employee_no: str
    date: date
    check_in: str = ""
    check_out: str = ""
    is_late: bool = False
    is_absent: bool = False
    hours: float = 0.0


class LeavePayload(BaseModel):
    employee_no: str
    leave_type: str
    start_date: date
    end_date: date
    days: float
    reason: str = ""


class CompensationPayload(BaseModel):
    employee_no: str
    effective_date: date
    base_salary: int
    target_bonus_pct: float = 0.0
    equity_value: int = 0
    currency: str = "CNY"


class PerformanceReviewPayload(BaseModel):
    employee_no: str
    period: str
    manager_score: float
    rating_label: str = ""
    self_score: float = 0.0


class TrainingRecordPayload(BaseModel):
    employee_no: str
    course_code: str
    course_name: str
    completed: bool
    hours: float = 0.0
    score: float = 0.0


@router.post("/employee")
def upsert_employee(
    payload: EmployeePayload,
    backend: str = Query("local"),
    db: Session = Depends(get_db),
):
    emp = HRISEmployee(**payload.model_dump())
    return _adapter(backend, db).upsert_employee(emp).__dict__


# ---------------- 招聘管理 ----------------


@router.get("/recruitment/applications")
def pull_applications(
    req_no: str | None = Query(None, description="招聘需求编号"),
    backend: str = Query("local"),
    db: Session = Depends(get_db),
):
    adapter = _adapter(backend, db)
    _require_capability(adapter, HRISCapability.RECRUITMENT)
    return adapter.pull_applications(req_no).__dict__


# ---------------- 薪酬与福利 ----------------


@router.get("/compensation")
def pull_compensation(
    employee_nos: str | None = Query(None, description="工号，逗号分隔"),
    backend: str = Query("local"),
    db: Session = Depends(get_db),
):
    adapter = _adapter(backend, db)
    _require_capability(adapter, HRISCapability.COMPENSATION)
    nos = [n.strip() for n in employee_nos.split(",")] if employee_nos else None
    return adapter.pull_compensation(nos).__dict__


@router.post("/compensation")
def push_compensation(
    records: list[CompensationPayload],
    backend: str = Query("local"),
    db: Session = Depends(get_db),
):
    adapter = _adapter(backend, db)
    _require_capability(adapter, HRISCapability.COMPENSATION)
    dtos = [CompensationDTO(**r.model_dump()) for r in records]
    return adapter.push_compensation(dtos).__dict__


# ---------------- 绩效管理 ----------------


@router.post("/performance/reviews")
def push_performance_review(
    records: list[PerformanceReviewPayload],
    backend: str = Query("local"),
    db: Session = Depends(get_db),
):
    adapter = _adapter(backend, db)
    _require_capability(adapter, HRISCapability.PERFORMANCE)
    dtos = [PerformanceReviewDTO(**r.model_dump()) for r in records]
    return adapter.push_performance_review(dtos).__dict__


# ---------------- 员工关系管理 ----------------


@router.post("/attendance")
def push_attendance(
    records: list[AttendancePayload],
    backend: str = Query("local"),
    db: Session = Depends(get_db),
):
    adapter = _adapter(backend, db)
    _require_capability(adapter, HRISCapability.EMPLOYEE_RELATIONS)
    dtos = [AttendanceRecordDTO(**r.model_dump()) for r in records]
    return adapter.push_attendance(dtos).__dict__


@router.post("/leave")
def push_leave(
    payload: LeavePayload,
    backend: str = Query("local"),
    db: Session = Depends(get_db),
):
    adapter = _adapter(backend, db)
    _require_capability(adapter, HRISCapability.EMPLOYEE_RELATIONS)
    dto = LeaveRequestDTO(**payload.model_dump())
    return adapter.push_leave_request(dto).__dict__


# ---------------- 培训与开发 ----------------


@router.post("/learning/records")
def push_training_record(
    records: list[TrainingRecordPayload],
    backend: str = Query("local"),
    db: Session = Depends(get_db),
):
    adapter = _adapter(backend, db)
    _require_capability(adapter, HRISCapability.LEARNING)
    dtos = [TrainingRecordDTO(**r.model_dump()) for r in records]
    return adapter.push_training_record(dtos).__dict__


# ---------------- 人力资源规划 ----------------


@router.get("/workforce/headcount")
def pull_headcount(
    department: str | None = Query(None),
    backend: str = Query("local"),
    db: Session = Depends(get_db),
):
    adapter = _adapter(backend, db)
    _require_capability(adapter, HRISCapability.WORKFORCE)
    return adapter.pull_headcount(department).__dict__


@router.get("/backends")
def backends():
    """列出当前可用的后端与各自支持的模块。"""
    return {
        "available": ["local", "sap_successfactors"],
        "current_env_sap_sf_configured": bool(
            os.getenv("SAP_SF_BASE_URL") and os.getenv("SAP_SF_COMPANY_ID")
        ),
        "capabilities": {
            "local": list(LocalHRISAdapter.capabilities),
            "sap_successfactors": list(SAPSuccessFactorsAdapter.capabilities),
        },
        "capability_labels": HRISCapability.LABELS,
    }