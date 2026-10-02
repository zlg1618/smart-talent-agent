"""HRIS 六大模块的 REST 路由包。

    recruitment         招聘管理
    compensation        薪酬与福利
    performance         绩效管理
    employee_relations  员工关系管理
    learning            培训与开发
    workforce           人力资源规划
"""

from app.api.hr import (
    compensation,
    employee_relations,
    learning,
    performance,
    recruitment,
    workforce,
)

__all__ = [
    "compensation",
    "employee_relations",
    "learning",
    "performance",
    "recruitment",
    "workforce",
]
