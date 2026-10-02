"""HRIS 适配器。

把"业务逻辑"与"具体人事系统"解耦。
业务层通过 HRISAdapter 接口访问六大模块的数据，默认使用 LocalHRISAdapter
直接读写本地库；配置好环境变量后可切换为 SAPSuccessFactorsAdapter。

六大模块：
    recruitment        招聘管理
    compensation       薪酬与福利
    performance        绩效管理
    employee_relations 员工关系管理
    learning           培训与开发
    workforce          人力资源规划

新增外部系统支持只需新增 Adapter 子类，按能力声明 capabilities 并实现对应方法。
"""

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
from app.integrations.local_adapter import LocalHRISAdapter
from app.integrations.sap_successfactors_adapter import (
    SF_ENTITY_MAP,
    SAPSuccessFactorsAdapter,
    build_sf_adapter_from_env,
)

__all__ = [
    "AttendanceRecordDTO",
    "CompensationDTO",
    "HeadcountDTO",
    "HRISAdapter",
    "HRISCapability",
    "HRISEmployee",
    "LeaveRequestDTO",
    "LocalHRISAdapter",
    "PerformanceReviewDTO",
    "SAPSuccessFactorsAdapter",
    "SF_ENTITY_MAP",
    "SyncResult",
    "TrainingRecordDTO",
    "build_sf_adapter_from_env",
]
