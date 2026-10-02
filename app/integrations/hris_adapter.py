"""HRIS 适配器抽象接口。

所有第三方 HRIS（SuccessFactors、Workday、北森、SAP HR 等）都通过本接口暴露能力。
实现类需要提供：
  - ping                  健康检查
  - get_employee          拉取员工主数据
  - upsert_employee       推送员工主数据
  - push_attendance       推送考勤记录
  - push_leave_request    推送请假申请
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable


@dataclass
class HRISEmployee:
    """统一员工数据契约（与具体 HRIS 字段解耦）。"""

    employee_no: str
    name: str
    department: str
    position_title: str
    job_level: str
    hire_date: date
    city: str = "-"
    status: str = "在职"
    email: str = ""
    manager_id: str | None = None
    extras: dict = field(default_factory=dict)


@dataclass
class AttendanceRecordDTO:
    employee_no: str
    date: date
    check_in: str = ""
    check_out: str = ""
    is_late: bool = False
    is_absent: bool = False
    hours: float = 0.0


@dataclass
class LeaveRequestDTO:
    employee_no: str
    leave_type: str
    start_date: date
    end_date: date
    days: float
    reason: str = ""


@dataclass
class SyncResult:
    """同步操作的统一返回。"""

    adapter: str
    ok: bool
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)


class HRISCapability:
    EMPLOYEE = "employee"
    ATTENDANCE = "attendance"
    LEAVE = "leave"


class HRISAdapter(ABC):
    """所有 HRIS 适配器的基类。"""

    name: str = "base"
    capabilities: Iterable[str] = ()

    @abstractmethod
    def ping(self) -> dict:
        """连通性自检，返回 {"reachable": bool, ...}。"""

    @abstractmethod
    def get_employee(self, employee_no: str) -> HRISEmployee | None:
        """按工号拉取员工主数据。"""

    @abstractmethod
    def upsert_employee(self, employee: HRISEmployee) -> SyncResult:
        """创建或更新员工主数据。"""

    @abstractmethod
    def push_attendance(self, records: list[AttendanceRecordDTO]) -> SyncResult:
        """推送考勤记录。"""

    @abstractmethod
    def push_leave_request(self, leave_request: LeaveRequestDTO) -> SyncResult:
        """推送请假申请。"""

    def describe(self) -> dict:
        return {
            "name": self.name,
            "capabilities": list(self.capabilities),
        }