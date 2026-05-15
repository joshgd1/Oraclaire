"""
Withdrawal entity — tracks an employee's opt-out from individual scoring.

Withdrawal takes effect after a 48-hour cooling-off period (D15-3).
"""

from datetime import datetime

from sqlalchemy import ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Withdrawal(Base, TimestampMixin):
    __tablename__ = "withdrawals"
    __table_args__ = (Index("ix_withdrawals_employee", "employee_id", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(nullable=False)
    effective_at: Mapped[datetime] = mapped_column(nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relations
    employee = relationship("Employee", back_populates="withdrawals")
