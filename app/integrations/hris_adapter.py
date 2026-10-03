"""HRIS 适配器抽象接口。

所有第三方 HRIS（SAP SuccessFactors、Workday、北森、SAP HR 等）都通过本接口
暴露能力，业务层不直接依赖任何具体厂商的字段。

能力按核心双域 + HRIS 六大支撑模块组织：
    organization_development  组织发展
    talent_development        人才发展
    recruitment        招聘管理
    compensation       薪酬与福利
    performance        绩效管理
    employee_relations 员工关系管理
    learning           培训与开发
    workforce          人力资源规划

每个模块默认可选实现：适配器通过 capabilities 声明自己支持哪些模块，
上层据此决定可路由的范围，避免调用到厂商不支持的接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable


# ---------------------------- 数据契约 ----------------------------


@dataclass
class HRISEmployee:
    """统一员工主数据契约（与具体 HRIS 字段解耦）。"""

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
class CompensationDTO:
    """统一薪酬数据契约（年度金额，单位：元）。"""

    employee_no: str
    effective_date: date
    base_salary: int
    target_bonus_pct: float = 0.0
    equity_value: int = 0
    currency: str = "CNY"


@dataclass
class PerformanceReviewDTO:
    """统一绩效评估契约。"""

    employee_no: str
    period: str
    manager_score: float
    rating_label: str = ""
    self_score: float = 0.0


@dataclass
class TrainingRecordDTO:
    """统一培训记录契约。"""

    employee_no: str
    course_code: str
    course_name: str
    completed: bool
    hours: float = 0.0
    score: float = 0.0


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
class HeadcountDTO:
    """编制与在编数据契约。"""

    department: str
    planned_headcount: int
    actual_headcount: int
    open_reqs: int = 0


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
    """能力域常量：核心双域 + 六大 HRIS 支撑模块，命名与业务模块 key 保持一致。"""

    # 核心双域
    ORG_DEV = "organization_development"
    TALENT_DEV = "talent_development"

    # 六大 HRIS 支撑模块
    RECRUITMENT = "recruitment"
    COMPENSATION = "compensation"
    PERFORMANCE = "performance"
    EMPLOYEE_RELATIONS = "employee_relations"
    LEARNING = "learning"
    WORKFORCE = "workforce"

    CORE: tuple[str, ...] = (ORG_DEV, TALENT_DEV)

    ALL: tuple[str, ...] = (
        ORG_DEV,
        TALENT_DEV,
        RECRUITMENT,
        COMPENSATION,
        PERFORMANCE,
        EMPLOYEE_RELATIONS,
        LEARNING,
        WORKFORCE,
    )

    LABELS: dict[str, str] = {
        ORG_DEV: "组织发展",
        TALENT_DEV: "人才发展",
        RECRUITMENT: "招聘管理",
        COMPENSATION: "薪酬与福利",
        PERFORMANCE: "绩效管理",
        EMPLOYEE_RELATIONS: "员工关系管理",
        LEARNING: "培训与开发",
        WORKFORCE: "人力资源规划",
    }


class HRISAdapter(ABC):
    """所有 HRIS 适配器的基类。

    必选：ping / get_employee / upsert_employee（主数据是任何集成的前提）。
    可选：其余方法默认抛 NotImplementedError，由 supports() 在调用前判定。
    """

    name: str = "base"
    capabilities: Iterable[str] = ()

    # ---------------- 通用 ----------------

    @abstractmethod
    def ping(self) -> dict:
        """连通性自检，返回 {"reachable": bool, ...}。"""

    @abstractmethod
    def get_employee(self, employee_no: str) -> HRISEmployee | None:
        """按工号拉取员工主数据。"""

    @abstractmethod
    def upsert_employee(self, employee: HRISEmployee) -> SyncResult:
        """创建或更新员工主数据。"""

    def supports(self, capability: str) -> bool:
        return capability in set(self.capabilities)

    def describe(self) -> dict:
        return {
            "name": self.name,
            "capabilities": list(self.capabilities),
            "capability_labels": {
                c: HRISCapability.LABELS.get(c, c) for c in self.capabilities
            },
        }

    # ---------------- recruitment 招聘管理 ----------------

    def pull_applications(self, req_no: str | None = None) -> SyncResult:
        """拉取投递申请。子类按需实现。"""
        raise NotImplementedError(f"{self.name} 未实现 pull_applications")

    # ---------------- compensation 薪酬与福利 ----------------

    def pull_compensation(self, employee_nos: list[str] | None = None) -> SyncResult:
        """拉取员工薪酬包。"""
        raise NotImplementedError(f"{self.name} 未实现 pull_compensation")

    def push_compensation(self, records: list[CompensationDTO]) -> SyncResult:
        """推送薪酬调整结果。"""
        raise NotImplementedError(f"{self.name} 未实现 push_compensation")

    # ---------------- performance 绩效管理 ----------------

    def push_performance_review(
        self, records: list[PerformanceReviewDTO]
    ) -> SyncResult:
        """推送绩效评估结果到外部 HRIS。"""
        raise NotImplementedError(f"{self.name} 未实现 push_performance_review")

    # ---------------- employee_relations 员工关系 ----------------

    def push_attendance(self, records: list[AttendanceRecordDTO]) -> SyncResult:
        """推送考勤记录。"""
        raise NotImplementedError(f"{self.name} 未实现 push_attendance")

    def push_leave_request(self, leave_request: LeaveRequestDTO) -> SyncResult:
        """推送请假申请。"""
        raise NotImplementedError(f"{self.name} 未实现 push_leave_request")

    # ---------------- learning 培训与开发 ----------------

    def push_training_record(self, records: list[TrainingRecordDTO]) -> SyncResult:
        """推送培训完成记录。"""
        raise NotImplementedError(f"{self.name} 未实现 push_training_record")

    # ---------------- workforce 人力资源规划 ----------------

    def pull_headcount(self, department: str | None = None) -> SyncResult:
        """拉取编制与在编数据。"""
        raise NotImplementedError(f"{self.name} 未实现 pull_headcount")
