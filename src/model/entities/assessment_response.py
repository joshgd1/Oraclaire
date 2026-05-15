"""
Assessment response entity — a single employee's response to one CBI item.

One AssessmentCycle contains many responses (19 CBI items × N employees).
Each response is one row with item_index + response_value.
"""

from datetime import datetime

from sqlalchemy import ForeignKey, Index, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class AssessmentResponse(Base, TimestampMixin):
    __tablename__ = "assessment_responses"
    __table_args__ = (
        Index(
            "ix_responses_cycle_employee",
            "cycle_id",
            "employee_id",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("assessment_cycles.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    item_index: Mapped[int] = mapped_column(nullable=False)
    response_value: Mapped[float] = mapped_column(Float, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relations
    cycle = relationship("AssessmentCycle", back_populates="responses")
    employee = relationship("Employee", back_populates="responses")
