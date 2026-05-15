"""
Assessment cycle entity — a scoring window (pulse or CBI) within an Organisation.
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, OrganisationMixin


class CycleType(PyEnum):
    PULSE = "pulse"
    CBI = "cbi"


class CycleStatus(PyEnum):
    OPEN = "open"
    CLOSED = "closed"


class AssessmentCycle(Base, TimestampMixin, OrganisationMixin):
    __tablename__ = "assessment_cycles"

    id: Mapped[int] = mapped_column(primary_key=True)
    cycle_type: Mapped[CycleType] = mapped_column(Enum(CycleType), nullable=False)
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[CycleStatus] = mapped_column(
        Enum(CycleStatus),
        default=CycleStatus.OPEN,
        nullable=False,
    )

    # Relations
    organisation = relationship("Organisation", back_populates="cycles")
    responses = relationship("AssessmentResponse", back_populates="cycle")
    risk_scores = relationship("RiskScore", back_populates="cycle")
