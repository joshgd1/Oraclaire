"""
Audit log entity — immutable append-only log of all actions on employee/score data.

Required for:
- GDPR Article 30 (record of processing activities)
- EU AI Act conformity assessment (audit trail)
- Internal compliance reporting

Every API endpoint that reads or modifies employee/score data must write an
AuditLog entry. Entries must never be modified or deleted.
"""

from datetime import datetime

from sqlalchemy import String, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_actor", "actor_id"),
        Index("ix_audit_logs_target", "target_entity_type", "target_entity_id"),
        Index("ix_audit_logs_timestamp", "timestamp"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
