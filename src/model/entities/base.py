"""
Base class and custom types shared across all Oraclaire entities.
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class OrganisationMixin:
    """Add organisation_id FK to any entity scoped to one organisation."""

    organisation_id: Mapped[int] = mapped_column(
        ForeignKey("organisations.id"), primary_key=False
    )


class TimestampMixin:
    """Add created_at / updated_at to any entity."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
