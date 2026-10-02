"""本地 HRIS 适配器：直接读写 SQLite / MySQL。

这是默认适配器，承担"无外部 HRIS 时也能完整演示整套业务"的职责，
六大模块全部落地为本地库表的读写。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.hris_adapter import (
    AttendanceRecordDTO,
    CompensationDTO,
    HeadcountDTO,
    HRISAdapter,
    HRISCapability,
    HRISEmployee,
    LeaveRequestDTO,
    PerformanceReviewDTO,
    SyncResult,
    TrainingRecordDTO,
)
from app.models import (
    Application,
    AttendanceRecord,
    BenefitPlan,
    Candidate,
    Employee,
    EmployeeBenefit,
    EmployeeCompensation,
    HeadcountPlan,
    JobPost,
    LeaveRequest,
    PerformanceReview,
    TrainingCourse,
    TrainingEnrollment,
)


class LocalHRISAdapter(HRISAdapter):
    name = "local"
    capabilities = HRISCapability.ALL

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

    # ---------------- recruitment ----------------

    def pull_applications(self, req_no: str | None = None) -> SyncResult:
        """从本地库读取投递申请。"""
        stmt = select(Application)
        if req_no:
            job = self.db.execute(
                select(JobPost).where(JobPost.req_no == req_no)
            ).scalars().first()
            if not job:
                return SyncResult(
                    adapter=self.name, ok=False, total=0,
                    errors=[f"未找到招聘需求编号：{req_no}"],
                )
            stmt = stmt.where(Application.job_post_id == job.id)

        rows = list(self.db.execute(stmt).scalars().all())
        data = []
        for a in rows:
            cand = self.db.get(Candidate, a.candidate_id)
            job = self.db.get(JobPost, a.job_post_id)
            data.append(
                {
                    "application_id": a.id,
                    "req_no": job.req_no if job else "",
                    "job_title": job.title if job else "",
                    "candidate": cand.name if cand else "",
                    "status": a.status,
                    "overall_score": a.overall_score,
                }
            )
        return SyncResult(
            adapter=self.name, ok=True, total=len(data), succeeded=len(data),
            extra={"applications": data},
        )

    # ---------------- compensation ----------------

    def pull_compensation(self, employee_nos: list[str] | None = None) -> SyncResult:
        rows = list(self.db.execute(select(EmployeeCompensation)).scalars().all())
        data = []
        for c in rows:
            emp = self.db.get(Employee, c.employee_id)
            if not emp:
                continue
            if employee_nos and emp.employee_no not in employee_nos:
                continue
            data.append(
                {
                    "employee_no": emp.employee_no,
                    "name": emp.name,
                    "effective_date": c.effective_date.isoformat(),
                    "base_salary": c.base_salary,
                    "target_bonus_pct": c.target_bonus_pct,
                    "equity_value": c.equity_value,
                }
            )
        return SyncResult(
            adapter=self.name, ok=True, total=len(data), succeeded=len(data),
            extra={"compensations": data},
        )

    def push_compensation(self, records: list[CompensationDTO]) -> SyncResult:
        succeeded, errors = 0, []
        for r in records:
            emp = self.db.execute(
                select(Employee).where(Employee.employee_no == r.employee_no)
            ).scalars().first()
            if not emp:
                errors.append(f"未找到员工：{r.employee_no}")
                continue
            self.db.add(
                EmployeeCompensation(
                    employee_id=emp.id,
                    employee_no=r.employee_no,
                    effective_date=r.effective_date,
                    base_salary=r.base_salary,
                    target_bonus_pct=r.target_bonus_pct,
                    equity_value=r.equity_value,
                    currency=r.currency,
                )
            )
            succeeded += 1
        return self._commit(len(records), succeeded, errors)

    # ---------------- performance ----------------

    def push_performance_review(
        self, records: list[PerformanceReviewDTO]
    ) -> SyncResult:
        succeeded, errors = 0, []
        for r in records:
            emp = self.db.execute(
                select(Employee).where(Employee.employee_no == r.employee_no)
            ).scalars().first()
            if not emp:
                errors.append(f"未找到员工：{r.employee_no}")
                continue
            existed = self.db.execute(
                select(PerformanceReview).where(
                    PerformanceReview.employee_id == emp.id,
                    PerformanceReview.period == r.period,
                )
            ).scalars().first()
            if existed:
                existed.manager_score = r.manager_score
                existed.rating_label = r.rating_label
                existed.self_score = r.self_score
            else:
                self.db.add(
                    PerformanceReview(
                        employee_id=emp.id,
                        period=r.period,
                        manager_score=r.manager_score,
                        rating_label=r.rating_label,
                        self_score=r.self_score,
                        review_date=r.period and __import__("datetime").date.today(),
                    )
                )
            succeeded += 1
        return self._commit(len(records), succeeded, errors)

    # ---------------- employee_relations ----------------

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
        return self._commit(len(records), succeeded, errors)

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
        return self._commit(1, 1, [])

    # ---------------- learning ----------------

    def push_training_record(self, records: list[TrainingRecordDTO]) -> SyncResult:
        succeeded, errors = 0, []
        for r in records:
            emp = self.db.execute(
                select(Employee).where(Employee.employee_no == r.employee_no)
            ).scalars().first()
            if not emp:
                errors.append(f"未找到员工：{r.employee_no}")
                continue
            course = self.db.execute(
                select(TrainingCourse).where(TrainingCourse.code == r.course_code)
            ).scalars().first()
            if not course:
                errors.append(f"未找到课程编号：{r.course_code}")
                continue
            if r.completed:
                existed = self.db.execute(
                    select(TrainingEnrollment).where(
                        TrainingEnrollment.employee_id == emp.id,
                        TrainingEnrollment.course_id == course.id,
                    )
                ).scalars().first()
                if existed:
                    existed.status = "completed"
                    existed.score = r.score
                    existed.hours_spent = r.hours
                else:
                    self.db.add(
                        TrainingEnrollment(
                            employee_id=emp.id,
                            course_id=course.id,
                            enrolled_at=__import__("datetime").date.today(),
                            completed_at=__import__("datetime").date.today(),
                            status="completed",
                            score=r.score,
                            hours_spent=r.hours,
                        )
                    )
            succeeded += 1
        return self._commit(len(records), succeeded, errors)

    # ---------------- workforce ----------------

    def pull_headcount(self, department: str | None = None) -> SyncResult:
        stmt = select(HeadcountPlan)
        if department:
            stmt = stmt.where(HeadcountPlan.department == department)
        plans = list(self.db.execute(stmt).scalars().all())
        data = [
            {
                "department": p.department,
                "planned_headcount": p.planned_headcount,
                "actual_headcount": p.actual_headcount,
                "open_reqs": p.open_reqs,
            }
            for p in plans
        ]
        return SyncResult(
            adapter=self.name, ok=True, total=len(data), succeeded=len(data),
            extra={"headcounts": data},
        )

    # ---------------- 内部辅助 ----------------

    def _commit(self, total: int, succeeded: int, errors: list[str]) -> SyncResult:
        try:
            self.db.commit()
            return SyncResult(
                adapter=self.name,
                ok=not errors,
                total=total,
                succeeded=succeeded,
                failed=len(errors),
                errors=errors,
            )
        except Exception as exc:
            self.db.rollback()
            return SyncResult(
                adapter=self.name, ok=False, total=total, failed=total,
                errors=[str(exc)],
            )


__all__ = ["LocalHRISAdapter"]