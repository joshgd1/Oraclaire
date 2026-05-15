"""
Risk score entity — the output of the scoring pipeline for one Employee in one Cycle.

Stores:
- numeric_score: raw burnout probability
- risk_tier: low / moderate / high / critical
- shap_values: JSON array of {feature, impact_value, direction}
- model_version: which model version produced this score
- seniority_tier_at_score: preserves the tier used at scoring time
"""

from datetime import datetime

from sqlalchemy import ForeignKey, String, Float, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class RiskScore(Base, TimestampMixin):
    __tablename__ = "risk_scores"
    __table_args__ = (
        Index("ix_risk_scores_employee_cycle", "employee_id", "cycle_id", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("assessment_cycles.id"), nullable=False)

    risk_tier: Mapped[str] = mapped_column(String(20), nullable=False)
    numeric_score: Mapped[float] = mapped_column(Float, nullable=False)
    shap_values: Mapped[list] = mapped_column(JSON, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    scored_at: Mapped[datetime] = mapped_column(nullable=False)
    seniority_tier_at_score: Mapped[int | None] = mapped_column(nullable=True)

    # Relations
    employee = relationship("Employee", back_populates="risk_scores")
    cycle = relationship("AssessmentCycle", back_populates="risk_scores")
