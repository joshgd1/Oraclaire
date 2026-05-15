"""
Manual HRIS adapter — direct HR admin input for demo/dev environments.

Allows HR admins to upsert Exclusion records directly without an external HRIS.
This is the fallback when no HRIS is configured, and is also used for
one-off manual overrides that take precedence over HRIS-sourced records.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import structlog

from src.hris.base import EmployeeRecord, HRISAdapter
from src.model.entities import Exclusion, ExclusionCategory, ExclusionSource
from src.model.entities._db import get_session_factory

logger = structlog.get_logger(__name__)


@dataclass
class ManualExclusionEntry:
    """A single manual exclusion specification."""

    employee_id: int  # DB primary key
    category: ExclusionCategory
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    reason: str = ""


class ManualAdapter(HRISAdapter):
    """
    Manual exclusion management adapter.

    This adapter does not fetch from an external HRIS.  Instead it exposes
    methods to upsert and remove MANUAL-sourced Exclusion records directly,
    giving HR admins a UI to manage exclusions without SSO/HRIS integration.

    The adapter is always available.
    """

    @property
    def provider_name(self) -> str:
        return "Manual"

    def is_available(self) -> bool:
        """Manual adapter is always available as the fallback."""
        return True

    def fetch_employees(self, organisation_id: int) -> list[EmployeeRecord]:
        """
        Returns an empty list — manual adapter does not sync from an HRIS.
        """
        return []

    def fetch_leave_status(
        self, employee_external_ids: list[str]
    ) -> dict[str, list[str]]:
        """Returns empty dict — manual adapter does not fetch leave status."""
        return {eid: [] for eid in employee_external_ids}

    def upsert_exclusion(
        self,
        employee_id: int,
        category: ExclusionCategory,
        effective_from: datetime | None = None,
        effective_to: datetime | None = None,
        reason: str = "",
    ) -> Exclusion:
        """
        Create or update a MANUAL-sourced Exclusion record.

        If an active MANUAL exclusion for the same employee+category already
        exists, it is updated in-place (effective_to extended or reason updated).
        """
        factory = get_session_factory()
        session = factory()
        try:
            now = effective_from or datetime.now(timezone.utc)

            existing = (
                session.query(Exclusion)
                .filter(
                    Exclusion.employee_id == employee_id,
                    Exclusion.category == category,
                    Exclusion.source == ExclusionSource.MANUAL,
                    Exclusion.effective_to.is_(None),
                )
                .first()
            )

            if existing is not None:
                existing.effective_to = effective_to
                session.commit()
                session.refresh(existing)
                logger.info(
                    "manual.exclusion.updated",
                    employee_id=employee_id,
                    category=category.value,
                )
                return existing

            exc = Exclusion(
                employee_id=employee_id,
                category=category,
                source=ExclusionSource.MANUAL,
                effective_from=now,
                effective_to=effective_to,
            )
            session.add(exc)
            session.commit()
            session.refresh(exc)
            logger.info(
                "manual.exclusion.created",
                employee_id=employee_id,
                category=category.value,
            )
            return exc
        finally:
            session.close()

    def remove_exclusion(
        self,
        employee_id: int,
        category: ExclusionCategory,
    ) -> bool:
        """
        Deactivate a MANUAL exclusion by setting effective_to = now.

        Returns True if a record was deactivated, False if no active record existed.
        """
        factory = get_session_factory()
        session = factory()
        try:
            existing = (
                session.query(Exclusion)
                .filter(
                    Exclusion.employee_id == employee_id,
                    Exclusion.category == category,
                    Exclusion.source == ExclusionSource.MANUAL,
                    Exclusion.effective_to.is_(None),
                )
                .first()
            )
            if existing is None:
                return False
            existing.effective_to = datetime.now(timezone.utc)
            session.commit()
            logger.info(
                "manual.exclusion.removed",
                employee_id=employee_id,
                category=category.value,
            )
            return True
        finally:
            session.close()

    def list_active(self, organisation_id: int) -> list[dict]:
        """
        Return all active MANUAL exclusions for the given organisation.
        """
        factory = get_session_factory()
        session = factory()
        try:
            from src.model.entities import Employee

            rows = (
                session.query(Exclusion)
                .join(Exclusion.employee)
                .filter(
                    Employee.organisation_id == organisation_id,
                    Exclusion.source == ExclusionSource.MANUAL,
                    Exclusion.effective_to.is_(None),
                )
                .all()
            )
            return [
                {
                    "id": r.id,
                    "employee_id": r.employee_id,
                    "category": r.category.value,
                    "effective_from": (
                        r.effective_from.isoformat() if r.effective_from else None
                    ),
                }
                for r in rows
            ]
        finally:
            session.close()
