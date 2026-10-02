"""HRIS / ATS 适配器。

把"业务逻辑"与"具体系统"解耦。Agent 通过适配器与真实 HRIS 通讯；默认情况下使用
LocalHRISAdapter 直接读写本地数据库演示整套业务。生产可切换为 SAPSuccessFactorsAdapter。

新增外部系统支持只需新增一个 Adapter 子类并实现 ping / upsert / pull / push 方法。
"""

from app.integrations.hris_adapter import (
    HRISAdapter,
    HRISCapability,
    HRISEmployee,
    SyncResult,
)
from app.integrations.local_adapter import LocalHRISAdapter
from app.integrations.sap_successfactors_adapter import (
    SAPSuccessFactorsAdapter,
    build_sf_adapter_from_env,
)

__all__ = [
    "HRISAdapter",
    "HRISCapability",
    "HRISEmployee",
    "LocalHRISAdapter",
    "SAPSuccessFactorsAdapter",
    "SyncResult",
    "build_sf_adapter_from_env",
]