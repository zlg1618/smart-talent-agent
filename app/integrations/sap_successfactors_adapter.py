"""SAP SuccessFactors Employee Central OData v2 适配器骨架。

⚠️ 本实现为接入骨架代码，未在真实租户上做端到端验证。
生产部署前请在目标 SF 沙箱跑一遍回归后再切换。

接入前准备：
    1. 在 SuccessFactors 租户上启用 OData API 与 OAuth2 SAML Bearer / Basic Auth。
    2. 申请 API 访问账号（具备 Employee Central 读写权限）。
    3. 配置以下环境变量：
           SAP_SF_BASE_URL=https://{tenant}.api.successfactors.com
           SAP_SF_COMPANY_ID=...
           SAP_SF_AUTH_MODE=oauth   # 或 basic
       OAuth 模式：
           SAP_SF_CLIENT_ID=...
           SAP_SF_CLIENT_SECRET=...
           SAP_SF_TOKEN_URL=https://{tenant}.auth.successfactors.com/oauth/token
       Basic 模式：
           SAP_SF_USER=...
           SAP_SF_PASSWORD=...
    4. 在企业网络打通到 https://{tenant}.api.successfactors.com 的访问。

核心双域与六模块对应的常见 OData v2 实体：
    组织发展        Position / PositionMatrixRelationship / Department / FOPosition
    人才发展        TalentPool / Succession / DevelopmentGoal / CareerDevelopment
    招聘管理        JobRequisition / JobApplication / CandidateProfile / JobOffer
    薪酬与福利      EmpCompensation / CompensationInfo / EmployeeBenefits
    绩效管理        PerformanceReview / Goal / CalibrationSession
    员工关系管理    EmpEmployment / Timesheet / EmployeeTimeSheet / LeaveRequest
    培训与开发      LearningEvents（LMS 侧通常走 OData v2 Learning API）
    人力资源规划    Position / PositionMatrixRelationship / EmpJob（编制与任职）

文档：
    https://api.sap.com/api/RCM_PF_V2/overview
    https://help.sap.com/docs/SAP_SUCCESSFACTORS_PLATFORM
"""

from __future__ import annotations

import base64
import os
from datetime import date
from typing import Any

import httpx

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

# 六大模块 → SAP SuccessFactors OData v2 实体映射表。
# 字段命名是各模块的常见默认集合，实际租户可能因版本与配置不同而有出入，
# 接入沙箱时建议先用下面的 entity 名跑一次 $metadata 校验。
SF_ENTITY_MAP: dict[str, str] = {
    "organization_development": "Position",
    "talent_development": "TalentPool",
    "recruitment": "JobApplication",
    "compensation": "EmpCompensation",
    "performance": "PerformanceReview",
    "employee_relations": "EmpEmployment",
    "learning": "LearningEvent",
    "workforce": "Position",
}


class SAPSuccessFactorsAdapter(HRISAdapter):
    name = "sap_successfactors"

    # Employee Central 主数据与时间管理是最容易开通的两块；
    # 其余模块依赖对应 SF 模块是否已启用，故默认不全开。
    capabilities = (
        # 核心双域：Employee Central 提供组织架构与编制，
        # Succession & Development 提供任职资格与人才池
        HRISCapability.ORG_DEV,
        HRISCapability.TALENT_DEV,
        HRISCapability.RECRUITMENT,
        HRISCapability.COMPENSATION,
        HRISCapability.PERFORMANCE,
        HRISCapability.EMPLOYEE_RELATIONS,
        HRISCapability.LEARNING,
        HRISCapability.WORKFORCE,
    )

    def __init__(
        self,
        base_url: str,
        company_id: str,
        auth_mode: str = "basic",
        user: str = "",
        password: str = "",
        client_id: str = "",
        client_secret: str = "",
        token_url: str = "",
        token: str = "",
    ):
        if not base_url:
            raise ValueError("base_url 必填，例 https://{tenant}.api.successfactors.com")
        self.base_url = base_url.rstrip("/")
        self.company_id = company_id
        self.auth_mode = auth_mode.lower()
        self.user = user
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self._token = token
        self._client = httpx.Client(timeout=30.0)

    # ---------------- 鉴权 ----------------

    def _basic_auth_header(self) -> dict[str, str]:
        token = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
        return {
            "Authorization": f"Basic {token}",
            "Accept": "application/json",
        }

    def _fetch_oauth_token(self) -> str:
        resp = self._client.post(
            self.token_url,
            data={"grant_type": "client_credentials"},
            auth=(self.client_id, self.client_secret),
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _headers(self) -> dict[str, str]:
        if self.auth_mode == "oauth":
            if not self._token:
                self._token = self._fetch_oauth_token()
            return {
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/json",
            }
        return self._basic_auth_header()

    def _params(self) -> dict[str, str]:
        return {"companyID": self.company_id, "$format": "JSON"}

    # ---------------- 实现 ----------------

    def ping(self) -> dict:
        try:
            resp = self._client.get(
                f"{self.base_url}/odata/v2/$metadata",
                headers=self._headers(),
                params={"companyID": self.company_id},
            )
            return {
                "reachable": resp.status_code == 200,
                "status": resp.status_code,
                "url": f"{self.base_url}/odata/v2/$metadata",
            }
        except Exception as exc:
            return {"reachable": False, "error": str(exc)}

    def get_employee(self, employee_no: str) -> HRISEmployee | None:
        try:
            resp = self._client.get(
                f"{self.base_url}/odata/v2/User('{employee_no}')",
                headers=self._headers(),
                params=self._params(),
            )
        except httpx.HTTPError as exc:
            return None
        if resp.status_code != 200:
            return None
        data: dict[str, Any] = resp.json()
        return HRISEmployee(
            employee_no=data.get("userId") or employee_no,
            name=data.get("displayName") or "",
            department=data.get("department") or "",
            position_title=data.get("title") or "",
            job_level=data.get("custom01") or "",
            hire_date=_parse_date(data.get("hireDate")),
            status="在职" if data.get("active") else "离职",
            extras={"raw": data},
        )

    def upsert_employee(self, employee: HRISEmployee) -> SyncResult:
        payload = {
            "userId": employee.employee_no,
            "displayName": employee.name,
            "department": employee.department,
            "title": employee.position_title,
            "custom01": employee.job_level,
            "hireDate": employee.hire_date.isoformat() if employee.hire_date else None,
            "status": "A" if employee.status == "在职" else "T",
        }
        return self._post_entity("User", payload, label=employee.employee_no)

    # ---------------- recruitment ----------------

    def pull_applications(self, req_no: str | None = None) -> SyncResult:
        params = dict(self._params())
        if req_no:
            params["$filter"] = f"requisitionId eq '{req_no}'"
        try:
            resp = self._client.get(
                self._entity_url(SF_ENTITY_MAP["recruitment"]),
                headers=self._headers(),
                params=params,
            )
            if resp.status_code != 200:
                return SyncResult(
                    adapter=self.name, ok=False, total=0,
                    errors=[f"HTTP {resp.status_code}: {resp.text[:200]}"],
                )
            rows = resp.json().get("d", {}).get("results", [])
            data = [
                {
                    "application_id": r.get("applicationId"),
                    "req_no": r.get("requisitionId") or "",
                    "job_title": r.get("jobTitle") or "",
                    "candidate": r.get("candidateName") or r.get("lastName") or "",
                    "status": r.get("applicationStatus") or "",
                    "overall_score": r.get("overallRating") or 0,
                }
                for r in rows
            ]
            return SyncResult(
                adapter=self.name, ok=True, total=len(data), succeeded=len(data),
                extra={"applications": data},
            )
        except httpx.HTTPError as exc:
            return SyncResult(adapter=self.name, ok=False, total=0, errors=[str(exc)])

    # ---------------- compensation ----------------

    def pull_compensation(self, employee_nos: list[str] | None = None) -> SyncResult:
        params = dict(self._params())
        if employee_nos:
            quoted = ",".join(f"'{n}'" for n in employee_nos)
            params["$filter"] = f"userId in ({quoted})"
        try:
            resp = self._client.get(
                self._entity_url(SF_ENTITY_MAP["compensation"]),
                headers=self._headers(),
                params=params,
            )
            if resp.status_code != 200:
                return SyncResult(
                    adapter=self.name, ok=False, total=0,
                    errors=[f"HTTP {resp.status_code}: {resp.text[:200]}"],
                )
            rows = resp.json().get("d", {}).get("results", [])
            data = [
                {
                    "employee_no": r.get("userId") or "",
                    "name": r.get("displayName") or "",
                    "effective_date": (r.get("startDate") or "")[:10],
                    "base_salary": r.get("payGroupAmount") or r.get("annualSalary") or 0,
                    "target_bonus_pct": r.get("targetBonusPercent") or 0,
                    "equity_value": r.get("stockAmount") or 0,
                }
                for r in rows
            ]
            return SyncResult(
                adapter=self.name, ok=True, total=len(data), succeeded=len(data),
                extra={"compensations": data},
            )
        except httpx.HTTPError as exc:
            return SyncResult(adapter=self.name, ok=False, total=0, errors=[str(exc)])

    def push_compensation(self, records: list[CompensationDTO]) -> SyncResult:
        errors: list[str] = []
        succeeded = 0
        for r in records:
            payload = {
                "userId": r.employee_no,
                "startDate": r.effective_date.isoformat(),
                "annualSalary": r.base_salary,
                "targetBonusPercent": r.target_bonus_pct,
                "stockAmount": r.equity_value,
                "currency": r.currency,
            }
            result = self._post_entity(
                SF_ENTITY_MAP["compensation"], payload, label=r.employee_no
            )
            if result.ok:
                succeeded += 1
            else:
                errors.extend(result.errors)
        return SyncResult(
            adapter=self.name, ok=not errors, total=len(records),
            succeeded=succeeded, failed=len(errors), errors=errors,
        )

    # ---------------- performance ----------------

    def push_performance_review(
        self, records: list[PerformanceReviewDTO]
    ) -> SyncResult:
        errors: list[str] = []
        succeeded = 0
        for r in records:
            payload = {
                "userId": r.employee_no,
                "period": r.period,
                "managerScore": r.manager_score,
                "selfScore": r.self_score,
                "ratingLabel": r.rating_label,
            }
            result = self._post_entity(
                SF_ENTITY_MAP["performance"], payload, label=r.employee_no
            )
            if result.ok:
                succeeded += 1
            else:
                errors.extend(result.errors)
        return SyncResult(
            adapter=self.name, ok=not errors, total=len(records),
            succeeded=succeeded, failed=len(errors), errors=errors,
        )

    # ---------------- employee_relations ----------------

    def push_attendance(self, records: list[AttendanceRecordDTO]) -> SyncResult:
        errors: list[str] = []
        succeeded = 0
        for r in records:
            payload = {
                "userId": r.employee_no,
                "date": r.date.isoformat(),
                "hours": r.hours,
                "startTime": r.check_in or None,
                "endTime": r.check_out or None,
                "status": "ABSENT" if r.is_absent else ("LATE" if r.is_late else "OK"),
            }
            result = self._post_entity("Timesheet", payload, label=r.employee_no)
            if result.ok:
                succeeded += 1
            else:
                errors.extend(result.errors)
        return SyncResult(
            adapter=self.name, ok=not errors, total=len(records),
            succeeded=succeeded, failed=len(errors), errors=errors,
        )

    def push_leave_request(self, leave_request: LeaveRequestDTO) -> SyncResult:
        payload = {
            "userId": leave_request.employee_no,
            "leaveType": leave_request.leave_type,
            "startDate": leave_request.start_date.isoformat(),
            "endDate": leave_request.end_date.isoformat(),
            "deductionQuantity": leave_request.days,
            "comments": leave_request.reason,
        }
        return self._post_entity("LeaveRequest", payload, label=leave_request.employee_no)

    # ---------------- learning ----------------

    def push_training_record(self, records: list[TrainingRecordDTO]) -> SyncResult:
        errors: list[str] = []
        succeeded = 0
        for r in records:
            payload = {
                "userId": r.employee_no,
                "itemId": r.course_code,
                "itemTitle": r.course_name,
                "completionStatus": "COMPLETED" if r.completed else "IN_PROGRESS",
                "creditHours": r.hours,
                "score": r.score,
            }
            result = self._post_entity(
                SF_ENTITY_MAP["learning"], payload, label=r.employee_no
            )
            if result.ok:
                succeeded += 1
            else:
                errors.extend(result.errors)
        return SyncResult(
            adapter=self.name, ok=not errors, total=len(records),
            succeeded=succeeded, failed=len(errors), errors=errors,
        )

    # ---------------- workforce ----------------

    def pull_headcount(self, department: str | None = None) -> SyncResult:
        params = dict(self._params())
        if department:
            params["$filter"] = f"department eq '{department}'"
        try:
            resp = self._client.get(
                self._entity_url(SF_ENTITY_MAP["workforce"]),
                headers=self._headers(),
                params=params,
            )
            if resp.status_code != 200:
                return SyncResult(
                    adapter=self.name, ok=False, total=0,
                    errors=[f"HTTP {resp.status_code}: {resp.text[:200]}"],
                )
            rows = resp.json().get("d", {}).get("results", [])
            data = [
                {
                    "department": r.get("department") or "",
                    "planned_headcount": int(r.get("plannedHeadcount") or 0),
                    "actual_headcount": int(r.get("actualHeadcount") or 0),
                    "open_reqs": int(r.get("openRequisitions") or 0),
                }
                for r in rows
            ]
            return SyncResult(
                adapter=self.name, ok=True, total=len(data), succeeded=len(data),
                extra={"headcounts": data},
            )
        except httpx.HTTPError as exc:
            return SyncResult(adapter=self.name, ok=False, total=0, errors=[str(exc)])

    # ---------------- 内部辅助 ----------------

    def _entity_url(self, entity: str) -> str:
        return f"{self.base_url}/odata/v2/{entity}"

    def _post_entity(
        self, entity: str, payload: dict, label: str = ""
    ) -> SyncResult:
        try:
            resp = self._client.post(
                self._entity_url(entity),
                headers={**self._headers(), "Content-Type": "application/json"},
                params=self._params(),
                json=payload,
            )
            ok = resp.status_code in (200, 201, 204)
            return SyncResult(
                adapter=self.name,
                ok=ok,
                total=1,
                succeeded=1 if ok else 0,
                failed=0 if ok else 1,
                errors=[]
                if ok
                else [f"{label} HTTP {resp.status_code}: {resp.text[:200]}"],
                extra={"status": resp.status_code, "entity": entity},
            )
        except httpx.HTTPError as exc:
            return SyncResult(
                adapter=self.name, ok=False, total=1, failed=1,
                errors=[f"{label}: {exc}"],
            )


def _parse_date(value: Any) -> date:
    if not value:
        return date.today()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return date.today()


def build_sf_adapter_from_env() -> SAPSuccessFactorsAdapter | None:
    """根据环境变量构造适配器；任意必填项缺失时返回 None。"""
    base_url = os.getenv("SAP_SF_BASE_URL")
    company_id = os.getenv("SAP_SF_COMPANY_ID")
    auth_mode = os.getenv("SAP_SF_AUTH_MODE", "basic")
    if not base_url or not company_id:
        return None
    return SAPSuccessFactorsAdapter(
        base_url=base_url,
        company_id=company_id,
        auth_mode=auth_mode,
        user=os.getenv("SAP_SF_USER", ""),
        password=os.getenv("SAP_SF_PASSWORD", ""),
        client_id=os.getenv("SAP_SF_CLIENT_ID", ""),
        client_secret=os.getenv("SAP_SF_CLIENT_SECRET", ""),
        token_url=os.getenv("SAP_SF_TOKEN_URL", ""),
    )