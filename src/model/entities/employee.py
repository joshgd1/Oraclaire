"""
Employee entity — a scored individual within an Organisation.

Fields:
- consent_status: tracks opt-in state for Tier 1 scoring
- seniority_tier: junior(0) or senior(1); drives which threshold applies
- exclusion_status / exclusion_category: driven by ExclusionEngine
- team_id: FK to Team; nullable for employees not yet assigned
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, ForeignKey, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, OrganisationMixin


class Role(PyEnum):
    EMPLOYEE = "employee"
    MANAGER = "manager"
    HR_ADMIN = "hr_admin"
    SYSTEM_ADMIN = "system_admin"
    PRODUCT_OWNER = "product_owner"


class ConsentStatus(PyEnum):
    PENDING = "pending"
    CONSENTED = "consented"
    WITHDRAWN = "withdrawn"


class ExclusionCategory(PyEnum):
    PIP = "pip"
    ADA = "ada"
    FMLA = "fmla"
    WORKERS_COMP = "workers_comp"
    DISCIPLINARY = "disciplinary"
    GRIEVANCE_COOLDOWN = "grievance_cooldown"
    MEDICAL_LEAVE = "medical_leave"
    ACTIVE_INTERVENTION = "active_intervention"
    CONTRACTOR = "contractor"
    TEST_ACCOUNT = "test_account"


class SenioritySource(PyEnum):
    HRIS_DERIVED = "hris_derived"
    SELF_REPORTED = "self_reported"
    REJECTED = "rejected"  # null because employee declined to self-report


class Employee(Base, TimestampMixin, OrganisationMixin):
    __tablename__ = "employees"
    __table_args__ = (
        Index("ix_employees_organisation_consent", "organisation_id", "consent_status"),
        Index("ix_employees_team", "team_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)

    consent_status: Mapped[ConsentStatus] = mapped_column(
        Enum(ConsentStatus),
        default=ConsentStatus.PENDING,
        nullable=False,
    )
    consent_timestamp: Mapped[datetime | None] = mapped_column(nullable=True)

    role: Mapped[Role] = mapped_column(
        Enum(Role),
        default=Role.EMPLOYEE,
        nullable=False,
    )

    seniority_tier: Mapped[int | None] = mapped_column(nullable=True)
    seniority_source: Mapped[SenioritySource | None] = mapped_column(
        Enum(SenioritySource),
        nullable=True,
    )

    exclusion_status: Mapped[bool] = mapped_column(default=False, nullable=False)
    exclusion_category: Mapped[ExclusionCategory | None] = mapped_column(
        Enum(ExclusionCategory),
        nullable=True,
    )

    # Relations
    organisation = relationship("Organisation", back_populates="employees")
    team = relationship("Team", back_populates="employees")
    department = relationship("Department", back_populates="employees")
    responses = relationship("AssessmentResponse", back_populates="employee")
    risk_scores = relationship("RiskScore", back_populates="employee")
    exclusions = relationship("Exclusion", back_populates="employee")
    withdrawals = relationship("Withdrawal", back_populates="employee")
