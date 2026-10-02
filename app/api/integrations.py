"""HRIS 适配器接入接口：ping、推送员工与事务。

通过 ?backend=local|sap_successfactors 切换适配器。
默认 backend=local，直接读写本地 SQLite / MySQL；如需对接 SAP SuccessFactors，
请配置 SAP_SF_* 环境变量并指定 backend=sap_successfactors。
"""

import os
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.integrations import (
    LocalHRISAdapter,
    SAPSuccessFactorsAdapter,
    build_sf_adapter_from_env,
)
from app.integrations.hris_adapter import (
    AttendanceRecordDTO,
    HRISEmployee,
    LeaveRequestDTO,
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


@router.post("/employee")
def upsert_employee(
    payload: EmployeePayload,
    backend: str = Query("local"),
    db: Session = Depends(get_db),
):
    emp = HRISEmployee(**payload.model_dump())
    return _adapter(backend, db).upsert_employee(emp).__dict__


@router.post("/attendance")
def push_attendance(
    records: list[AttendancePayload],
    backend: str = Query("local"),
    db: Session = Depends(get_db),
):
    dtos = [AttendanceRecordDTO(**r.model_dump()) for r in records]
    return _adapter(backend, db).push_attendance(dtos).__dict__


@router.post("/leave")
def push_leave(
    payload: LeavePayload,
    backend: str = Query("local"),
    db: Session = Depends(get_db),
):
    dto = LeaveRequestDTO(**payload.model_dump())
    return _adapter(backend, db).push_leave_request(dto).__dict__


@router.get("/backends")
def backends():
    """列出当前可用的后端。"""
    return {
        "available": ["local", "sap_successfactors"],
        "current_env_sap_sf_configured": bool(
            os.getenv("SAP_SF_BASE_URL") and os.getenv("SAP_SF_COMPANY_ID")
        ),
    }