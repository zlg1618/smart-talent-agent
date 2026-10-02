"""本地 HRIS 适配器：直接读写 SQLite / MySQL。

这是默认适配器，承担"无外部 HRIS 时也能完整演示整套业务"的职责。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.hris_adapter import (
    AttendanceRecordDTO,
    HRISAdapter,
    HRISCapability,
    HRISEmployee,
    LeaveRequestDTO,
    SyncResult,
)
from app.models import AttendanceRecord, Employee, LeaveRequest


class LocalHRISAdapter(HRISAdapter):
    name = "local"
    capabilities = (
        HRISCapability.EMPLOYEE,
        HRISCapability.ATTENDANCE,
        HRISCapability.LEAVE,
    )

    def __init__(self, db: Session):
        self.db = db

    def ping(self) -> dict:
        try:
            self.db.execute(select(1))
            return {"reachable": True, "backend": "local SQLite/MySQL"}
        except Exception as exc:
            return {"reachable": False, "error": str(exc)}

    def get_employee(self, employee_no: str) -> HRISEmployee | None:
        emp = self.db.execute(
            select(Employee).where(Employee.employee_no == employee_no)
        ).scalars().first()
        if not emp:
            return None
        return HRISEmployee(
            employee_no=emp.employee_no,
            name=emp.name,
            department=emp.department,
            position_title=emp.position_title,
            job_level=emp.job_level,
            hire_date=emp.hire_date,
            city=emp.city,
            status=emp.status,
            manager_id=str(emp.manager_id) if emp.manager_id else None,
        )

    def upsert_employee(self, employee: HRISEmployee) -> SyncResult:
        emp = self.db.execute(
            select(Employee).where(Employee.employee_no == employee.employee_no)
        ).scalars().first()
        if emp:
            emp.name = employee.name
            emp.department = employee.department
            emp.position_title = employee.position_title
            emp.job_level = employee.job_level
            emp.hire_date = employee.hire_date
            emp.city = employee.city
            emp.status = employee.status
            action = "updated"
        else:
            self.db.add(
                Employee(
                    employee_no=employee.employee_no,
                    name=employee.name,
                    department=employee.department,
                    position_title=employee.position_title,
                    job_level=employee.job_level,
                    hire_date=employee.hire_date,
                    city=employee.city,
                    status=employee.status,
                    job_family=employee.extras.get("job_family", "-"),
                )
            )
            action = "created"
        try:
            self.db.commit()
            return SyncResult(
                adapter=self.name,
                ok=True,
                total=1,
                succeeded=1,
                extra={"action": action, "employee_no": employee.employee_no},
            )
        except Exception as exc:
            self.db.rollback()
            return SyncResult(
                adapter=self.name,
                ok=False,
                total=1,
                failed=1,
                errors=[str(exc)],
            )

    def push_attendance(self, records: list[AttendanceRecordDTO]) -> SyncResult:
        succeeded = 0
        errors: list[str] = []
        for r in records:
            emp = self.db.execute(
                select(Employee).where(Employee.employee_no == r.employee_no)
            ).scalars().first()
            if not emp:
                errors.append(f"未找到员工：{r.employee_no}")
                continue
            self.db.add(
                AttendanceRecord(
                    employee_id=emp.id,
                    date=r.date,
                    check_in=r.check_in or None,
                    check_out=r.check_out or None,
                    is_late=r.is_late,
                    is_absent=r.is_absent,
                    hours=r.hours,
                )
            )
            succeeded += 1
        try:
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            return SyncResult(
                adapter=self.name,
                ok=False,
                total=len(records),
                failed=len(records),
                errors=[str(exc)],
            )
        return SyncResult(
            adapter=self.name,
            ok=not errors,
            total=len(records),
            succeeded=succeeded,
            failed=len(errors),
            errors=errors,
        )

    def push_leave_request(self, leave_request: LeaveRequestDTO) -> SyncResult:
        emp = self.db.execute(
            select(Employee).where(Employee.employee_no == leave_request.employee_no)
        ).scalars().first()
        if not emp:
            return SyncResult(
                adapter=self.name,
                ok=False,
                total=1,
                failed=1,
                errors=[f"未找到员工：{leave_request.employee_no}"],
            )
        self.db.add(
            LeaveRequest(
                employee_id=emp.id,
                leave_type=leave_request.leave_type,
                start_date=leave_request.start_date,
                end_date=leave_request.end_date,
                days=leave_request.days,
                reason=leave_request.reason,
                status="pending",
            )
        )
        try:
            self.db.commit()
            return SyncResult(
                adapter=self.name,
                ok=True,
                total=1,
                succeeded=1,
                extra={"employee_no": leave_request.employee_no},
            )
        except Exception as exc:
            self.db.rollback()
            return SyncResult(
                adapter=self.name,
                ok=False,
                total=1,
                failed=1,
                errors=[str(exc)],
            )