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

常见 OData 端点：
    GET    /odata/v2/User('userName')
    POST   /odata/v2/User
    PATCH  /odata/v2/User('userName')
    GET    /odata/v2/EmpEmployment
    GET    /odata/v2/Timesheet

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
    HRISAdapter,
    HRISCapability,
    HRISEmployee,
    LeaveRequestDTO,
    SyncResult,
)


class SAPSuccessFactorsAdapter(HRISAdapter):
    name = "sap_successfactors"
    capabilities = (
        HRISCapability.EMPLOYEE,
        HRISCapability.ATTENDANCE,
        HRISCapability.LEAVE,
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
            "active": employee.status == "在职",
        }
        try:
            resp = self._client.post(
                f"{self.base_url}/odata/v2/User",
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
                errors=[] if ok else [f"HTTP {resp.status_code}: {resp.text[:200]}"],
                extra={"status": resp.status_code},
            )
        except httpx.HTTPError as exc:
            return SyncResult(
                adapter=self.name,
                ok=False,
                total=1,
                failed=1,
                errors=[str(exc)],
            )

    def push_attendance(self, records: list[AttendanceRecordDTO]) -> SyncResult:
        # SuccessFactors 默认通过 Timesheet OData 实体提交
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
            try:
                resp = self._client.post(
                    f"{self.base_url}/odata/v2/Timesheet",
                    headers={**self._headers(), "Content-Type": "application/json"},
                    params=self._params(),
                    json=payload,
                )
                if resp.status_code in (200, 201, 204):
                    succeeded += 1
                else:
                    errors.append(f"{r.employee_no} HTTP {resp.status_code}")
            except httpx.HTTPError as exc:
                errors.append(f"{r.employee_no}: {exc}")
        return SyncResult(
            adapter=self.name,
            ok=not errors,
            total=len(records),
            succeeded=succeeded,
            failed=len(errors),
            errors=errors,
        )

    def push_leave_request(self, leave_request: LeaveRequestDTO) -> SyncResult:
        payload = {
            "userId": leave_request.employee_no,
            "leaveType": leave_request.leave_type,
            "startDate": leave_request.start_date.isoformat(),
            "endDate": leave_request.end_date.isoformat(),
            "days": leave_request.days,
            "reason": leave_request.reason,
        }
        try:
            resp = self._client.post(
                f"{self.base_url}/odata/v2/LeaveRequest",
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
                errors=[] if ok else [f"HTTP {resp.status_code}: {resp.text[:200]}"],
            )
        except httpx.HTTPError as exc:
            return SyncResult(
                adapter=self.name,
                ok=False,
                total=1,
                failed=1,
                errors=[str(exc)],
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