"""
Exclusion record entity — tracks each individual exclusion determination.

One Exclusion record per employee per exclusion category event.
Driven by ExclusionEngine (M1-09); used to compute scoreable_population.
"""

from datetime import datetime

from sqlalchemy import ForeignKey, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from enum import Enum as PyEnum

from sqlalchemy import ForeignKey, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .employee import ExclusionCategory


class ExclusionSource(PyEnum):
    HRIS = "hris"
    MANUAL = "manual"


class Exclusion(Base, TimestampMixin):
    __tablename__ = "exclusions"
    __table_args__ = (
        Index("ix_exclusions_employee_category", "employee_id", "category"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    category: Mapped[ExclusionCategory] = mapped_column(Enum(ExclusionCategory), nullable=False)
    source: Mapped[ExclusionSource] = mapped_column(
        Enum(ExclusionSource),
        default=ExclusionSource.MANUAL,
        nullable=False,
    )
    effective_from: Mapped[datetime] = mapped_column(nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relations
    employee = relationship("Employee", back_populates="exclusions")
