"""
Organisation entity — the top-level tenant in Oraclaire.

Each Oraclaire customer deployment is one Organisation record.
All other entities (Employee, Team, AssessmentCycle, ...) carry an organisation_id FK.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Organisation(Base, TimestampMixin):
    __tablename__ = "organisations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(10), nullable=False)
    works_council_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # EU jurisdictions requiring works council approval: DE, FR, NL
    # Set via deployment parameter; defaults False (safest starting point)

    # Relations — one org has many employees, teams, cycles, parameters
    employees = relationship("Employee", back_populates="organisation")
    teams = relationship("Team", foreign_keys="Team.organisation_id", viewonly=True)
    departments = relationship("Department", foreign_keys="Department.organisation_id", viewonly=True)
    cycles = relationship("AssessmentCycle", foreign_keys="AssessmentCycle.organisation_id", viewonly=True)
    parameters = relationship(
        "DeploymentParameter",
        foreign_keys="DeploymentParameter.organisation_id",
        viewonly=True,
    )
