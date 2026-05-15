"""
Team entity — group of Employees within an Organisation and Department.
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, ForeignKey, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, OrganisationMixin


class Team(Base, TimestampMixin, OrganisationMixin):
    __tablename__ = "teams"
    __table_args__ = (Index("ix_teams_department", "department_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Denormalised counts updated on each cycle close
    member_count: Mapped[int] = mapped_column(default=0, nullable=False)
    aggregate_score: Mapped[float | None] = mapped_column(nullable=True)
    participation_rate: Mapped[float | None] = mapped_column(nullable=True)
    last_assessment_date: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relations
    organisation = relationship("Organisation", back_populates="teams")
    department = relationship("Department", back_populates="teams")
    employees = relationship("Employee", back_populates="team")
