"""
AuditLogService — immutable append-only audit log for Oraclaire.

Required for GDPR Article 30, EU AI Act transparency, and conformity assessment.

Every API endpoint that reads or modifies employee/score data must write an
AuditLog entry via this service. Entries must never be modified or deleted.

Access is intentionally read-only for downstream consumers — the service provides
no update or delete methods.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.model.entities import AuditLog
from src.model.entities._db import get_session_factory


class AuditLogService:
    """Append-only audit log service."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def log(
        self,
        action: str,
        target_entity_type: str,
        target_entity_id: str,
        *,
        actor_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> AuditLog:
        """Append an immutable audit log entry.

        Parameters
        ----------
        action:
            The action performed. Convention: "verb_entity" e.g.
            "create_employee", "read_score", "update_consent", "delete_withdrawal".
        target_entity_type:
            The type of entity acted on. Convention: singular snake_case
            e.g. "employee", "risk_score", "assessment_cycle".
        target_entity_id:
            The ID of the entity acted on.
        actor_id:
            The user or system performing the action. For employee-initiated
            actions this is the employee_id. For system-initiated actions
            (e.g. scoring job) this is "system".
        metadata:
            Arbitrary context. Do NOT include PII or secrets.
        timestamp:
            Defaults to now UTC. Explicit values are used when replaying
            or backfilling entries.
        """
        entry = AuditLog(
            actor_id=actor_id,
            action=action,
            target_entity_type=target_entity_type,
            target_entity_id=str(target_entity_id),
            timestamp=timestamp or datetime.now(timezone.utc),
            metadata_json=metadata,
        )
        self._session.add(entry)
        self._session.flush()
        return entry

    # Convenience methods for common audit events

    def log_consent(
        self,
        employee_id: int,
        action: str,
        actor_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Audit a consent-related action (opt-in, withdrawal, etc.)."""
        return self.log(
            action=action,
            target_entity_type="employee",
            target_entity_id=str(employee_id),
            actor_id=actor_id,
            metadata=metadata,
        )

    def log_score_read(
        self,
        employee_id: int,
        viewer_id: str,
        viewer_role: str,
    ) -> AuditLog:
        """Audit when a score is accessed."""
        return self.log(
            action="read_risk_score",
            target_entity_type="risk_score",
            target_entity_id=str(employee_id),
            actor_id=viewer_id,
            metadata={"viewer_role": viewer_role},
        )

    def log_cycle_close(
        self,
        cycle_id: int,
        system_id: str = "system",
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Audit when an assessment cycle closes and triggers scoring."""
        return self.log(
            action="close_assessment_cycle",
            target_entity_type="assessment_cycle",
            target_entity_id=str(cycle_id),
            actor_id=system_id,
            metadata=metadata,
        )

    def log_exclusion_change(
        self,
        employee_id: int,
        excluded: bool,
        category: str | None,
        actor_id: str,
    ) -> AuditLog:
        """Audit an exclusion status change."""
        return self.log(
            action=("exclude_employee" if excluded else "unexclude_employee"),
            target_entity_type="employee",
            target_entity_id=str(employee_id),
            actor_id=actor_id,
            metadata={"exclusion_category": category} if category else None,
        )

    # ── read ────────────────────────────────────────────────────────────────

    def query(
        self,
        *,
        actor_id: str | None = None,
        target_entity_type: str | None = None,
        target_entity_id: str | None = None,
        action: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Query audit log entries with optional filters."""
        q = self._session.query(AuditLog)

        if actor_id is not None:
            q = q.filter(AuditLog.actor_id == actor_id)
        if target_entity_type is not None:
            q = q.filter(AuditLog.target_entity_type == target_entity_type)
        if target_entity_id is not None:
            q = q.filter(AuditLog.target_entity_id == str(target_entity_id))
        if action is not None:
            q = q.filter(AuditLog.action == action)
        if since is not None:
            q = q.filter(AuditLog.timestamp >= since)
        if until is not None:
            q = q.filter(AuditLog.timestamp <= until)

        return q.order_by(AuditLog.timestamp.desc()).limit(limit).all()

    # ── context manager ────────────────────────────────────────────────────

    @classmethod
    def using(cls) -> "AuditLogService":
        """Create a service backed by a session from the factory."""
        factory = get_session_factory()
        session = factory()
        return cls(session)

    def close(self) -> None:
        self._session.close()
