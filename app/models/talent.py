"""关键岗位与继任计划。"""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class KeyPosition(Base, TimestampMixin):
    """关键岗位。criticality 越高，空缺风险越大。"""

    __tablename__ = "key_position"

    title: Mapped[str] = mapped_column(String(64))
    department: Mapped[str] = mapped_column(String(64))
    job_level: Mapped[str] = mapped_column(String(8))
    incumbent_id: Mapped[int | None] = mapped_column(
        ForeignKey("employee.id"), nullable=True
    )
    criticality: Mapped[str] = mapped_column(String(8))  # 高 / 中 / 低

    successors: Mapped[list["SuccessionPlan"]] = relationship(
        back_populates="key_position", cascade="all, delete-orphan"
    )


class SuccessionPlan(Base, TimestampMixin):
    """继任计划：某个关键岗位的候选人及其准备度。

    readiness:
        ready_now  立即就绪
        ready_1y   1 年内就绪
        ready_2y   2 年内就绪
        not_ready  尚未就绪
    """

    __tablename__ = "succession_plan"

    key_position_id: Mapped[int] = mapped_column(ForeignKey("key_position.id"))
    successor_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    readiness: Mapped[str] = mapped_column(String(16))
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    key_position: Mapped["KeyPosition"] = relationship(back_populates="successors")
    successor: Mapped["Employee"] = relationship()


__all__ = ["KeyPosition", "SuccessionPlan"]
