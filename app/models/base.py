"""模型公共基类与混入字段。"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class TimestampMixin:
    """通用主键与创建时间。"""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=True
    )


__all__ = ["Base", "TimestampMixin"]
