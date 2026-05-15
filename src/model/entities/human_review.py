"""
HumanReview entity — the per-employee review gate for Critical-tier scores.

Stores:
- review_status: pending_review / approved / overridden
- reviewer_id: who took the action (null while pending)
- reviewed_at: when the action was taken (null while pending)
- override_reason: required when status=overridden
- override_new_tier: the tier HR changed to (null when status=approved)
"""

from datetime import datetime

from sqlalchemy import ForeignKey, String, Enum as SAEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class ReviewStatus(str):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    OVERRIDDEN = "overridden"


class HumanReview(Base, TimestampMixin):
    __tablename__ = "human_reviews"
    __table_args__ = (
        Index(
            "ix_human_reviews_employee_cycle",
            "employee_id",
            "cycle_id",
            unique=True,
        ),
        Index("ix_human_reviews_status", "review_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id"), nullable=False
    )
    cycle_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_cycles.id"), nullable=False
    )
    risk_score_id: Mapped[int] = mapped_column(
        ForeignKey("risk_scores.id"), nullable=False, unique=True
    )

    # Review state
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ReviewStatus.PENDING_REVIEW
    )

    # Who acted (null while pending_review)
    reviewer_id: Mapped[int | None] = mapped_column(nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Override fields (required when review_status=OVERRIDDEN)
    override_reason: Mapped[str | None] = mapped_column(nullable=True)
    override_new_tier: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )

    # Relations
    employee = relationship("Employee", back_populates="human_reviews")
    cycle = relationship("AssessmentCycle", back_populates="human_reviews")
    risk_score = relationship("RiskScore", back_populates="human_review")
