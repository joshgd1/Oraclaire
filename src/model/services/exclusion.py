"""
ExclusionEngine — determines exclusion status for employees.

Drives M1-09 (exclusion engine) and feeds M1-10 (cycle-start wiring).
Computes exclusion_status + exclusion_category for a set of employees
by evaluating active Exclusion records (effective_from/effective_to).

HRIS wiring (M2-07):
- ExclusionEngine accepts an optional HrisAdapter
- On apply_to_employees(), syncs exclusion records from HRIS before checking DB
- Circuit breaker: after 5 consecutive failures, the adapter is skipped for
  subsequent calls until it recovers
- Exponential backoff: 1s, 2s, 4s, 8s, 16s per failure count
- Partial-failure: proceeds with fetched employees, flags remainder for manual review
- All adapter failures are logged
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Literal

from sqlalchemy.orm import Session

from src.model.entities import Exclusion, ExclusionCategory, ExclusionSource
from src.model.entities._db import get_session_factory

logger = logging.getLogger(__name__)

# How many consecutive failures trip the circuit breaker
_CIRCUIT_BREAKER_THRESHOLD = 5
# Starting delay in seconds for exponential backoff
_BACKOFF_BASE_SECS = 1.0


class ExclusionEngine:
    """
    Service that resolves exclusion status per employee.

    Parameters
    ----------
    session : Session
        SQLAlchemy session. Caller is responsible for commit/rollback/close.
    hris_available : bool, default True
        Set to False to force graceful-degradation mode, ignoring all
        HRIS-sourced Exclusion records and using only MANUAL ones.
    hris_adapter : HrisAdapter | None
        Optional HRIS adapter. When provided, exclusion records are synced from
        the HR system before checking the local DB. Circuit breaker protects
        against sustained HRIS failures.
    """

    def __init__(
        self,
        session: Session,
        *,
        hris_available: bool = True,
        hris_adapter: "HrisAdapter | None" = None,
    ) -> None:
        self._session = session
        self._hris_available = hris_available
        self._adapter = hris_adapter
        self._adapter_failures = 0
        self._circuit_open_since: float | None = None

    # ── public API ────────────────────────────────────────────────────────────

    def check_employees(
        self,
        employee_ids: list[int] | None = None,
        organisation_id: int | None = None,
    ) -> dict[int, dict[str, bool | str | None]]:
        """
        Return exclusion status for one or more employees.

        Exactly one of employee_ids or organisation_id must be supplied.

        Parameters
        ----------
        employee_ids
            Specific employee IDs to evaluate. Fetched in a single query.
        organisation_id
            If provided, all employees in the org are evaluated.
        hris_available (constructor kwarg)
            When False, HRIS-sourced exclusion records are ignored.

        Returns
        -------
        Dict mapping employee_id -> {
            "exclusion_status": bool,
            "exclusion_category": str | None,   # enum value name or None
            "exclusion_source": str | None,    # "hris" | "manual" | None
        }
        """
        if (employee_ids is None) == (organisation_id is None):
            raise ValueError("Provide employee_ids OR organisation_id, not both and not neither.")

        now = datetime.utcnow()

        query = self._session.query(Exclusion).filter(
            Exclusion.effective_from <= now,
            (Exclusion.effective_to.is_(None)) | (Exclusion.effective_to >= now),
        )

        if employee_ids is not None:
            query = query.filter(Exclusion.employee_id.in_(employee_ids))
        else:
            # organisation_id path: join through Employee
            from src.model.entities import Employee

            query = query.join(Employee).filter(
                Employee.organisation_id == organisation_id
            )

        if not self._hris_available:
            query = query.filter(Exclusion.source == ExclusionSource.MANUAL)

        rows = query.all()
        return self._build_result(rows, employee_ids)

    def check_all_in_org(
        self, organisation_id: int
    ) -> dict[int, dict[str, bool | str | None]]:
        """Convenience: check every employee in an organisation."""
        return self.check_employees(organisation_id=organisation_id)

    def check_by_ids(
        self, employee_ids: list[int]
    ) -> dict[int, dict[str, bool | str | None]]:
        """Convenience: check specific employees by ID."""
        return self.check_employees(employee_ids=employee_ids)

    def _sync_from_hris(self, employee_ids: list[int]) -> dict[str, int]:
        """
        Pull exclusion records from the HRIS adapter and upsert them into the
        local Exclusion table.

        This is called at the start of apply_to_employees() when an adapter
        is configured and the circuit breaker is closed.

        Returns a summary dict with keys:
          "fetched": employees whose HRIS exclusion status was fetched
          "flagged_for_manual_review": employees where HRIS returned null
          "adapter_failures": employees skipped due to adapter error
        """
        if not self._adapter or not self._hris_available:
            return {"fetched": 0, "flagged_for_manual_review": 0, "adapter_failures": 0}

        # Circuit breaker — if tripped, skip until some time has passed
        if self._circuit_open_since is not None:
            elapsed = time.time() - self._circuit_open_since
            backoff = _BACKOFF_BASE_SECS * (2 ** (self._adapter_failures - 1))
            if elapsed < backoff:
                logger.info(
                    "exclusion.circuit_open",
                    adapter=self._adapter.name,
                    failures=self._adapter_failures,
                    elapsed_s=round(elapsed, 1),
                )
                return {"fetched": 0, "flagged_for_manual_review": 0, "adapter_failures": len(employee_ids)}
            # Retry after backoff elapsed
            self._circuit_open_since = None

        from src.model.entities import Employee

        fetched = 0
        flagged = 0
        failures = 0

        for emp_id in employee_ids:
            emp = self._session.query(Employee).filter(Employee.id == emp_id).first()
            if emp is None:
                continue

            try:
                result = self._adapter.get_exclusion_status(emp_id)
            except Exception as exc:
                logger.warning(
                    "exclusion.hris.error",
                    adapter=self._adapter.name,
                    employee_id=emp_id,
                    error=str(exc),
                )
                failures += 1
                self._adapter_failures += 1
                if self._adapter_failures >= _CIRCUIT_BREAKER_THRESHOLD:
                    self._circuit_open_since = time.time()
                    logger.error(
                        "exclusion.circuit_open",
                        adapter=self._adapter.name,
                        threshold=_CIRCUIT_BREAKER_THRESHOLD,
                    )
                continue

            if result is None:
                flagged += 1
                continue

            if not result.excluded:
                fetched += 1
                continue

            # Upsert: find existing HRIS exclusion or create new one
            existing = self._session.query(Exclusion).filter(
                Exclusion.employee_id == emp_id,
                Exclusion.source == ExclusionSource.HRIS,
                Exclusion.category == ExclusionCategory(result.category or "pip"),
            ).first()

            if existing:
                existing.effective_from = datetime.utcnow()
                existing.effective_to = None
            else:
                self._session.add(Exclusion(
                    employee_id=emp_id,
                    category=ExclusionCategory(result.category or "pip"),
                    source=ExclusionSource.HRIS,
                    effective_from=datetime.utcnow(),
                    effective_to=None,
                ))
            fetched += 1

        # Reset failure count on success
        if failures == 0 and fetched > 0:
            self._adapter_failures = 0
            self._circuit_open_since = None

        try:
            self._session.commit()
        except Exception as exc:
            logger.exception("exclusion.hris.commit.error", error=str(exc))
            self._session.rollback()

        return {
            "fetched": fetched,
            "flagged_for_manual_review": flagged,
            "adapter_failures": failures,
        }

    def apply_to_employees(
        self,
        employee_ids: list[int] | None = None,
        organisation_id: int | None = None,
    ) -> dict[str, int]:
        """
        Evaluate exclusion status and write results back to Employee records.

        This is the M1-10 wiring point: after checking exclusions, the
        resulting exclusion_status and exclusion_category are written to each
        Employee row so the scoring pipeline can filter scorable employees
        with a simple query.

        Parameters
        ----------
        employee_ids or organisation_id
            Same as check_employees().

        Returns
        -------
        Dict with keys:
          "evaluated": employees whose records were updated
          "excluded": employees flagged as excluded
          "hris_fetched": employees whose HRIS record was synced
          "hris_flagged_for_manual_review": employees where HRIS returned null
          "hris_adapter_failures": employees skipped due to adapter error
        """
        # Sync from HRIS first
        hris_sync = {"fetched": 0, "flagged_for_manual_review": 0, "adapter_failures": 0}
        if employee_ids is not None and self._adapter and self._hris_available:
            hris_sync = self._sync_from_hris(employee_ids)

        statuses = self.check_employees(
            employee_ids=employee_ids, organisation_id=organisation_id
        )

        from src.model.entities import Employee

        evaluated = 0
        excluded = 0

        for emp_id, status in statuses.items():
            emp = self._session.query(Employee).filter(Employee.id == emp_id).first()
            if emp is None:
                continue
            evaluated += 1
            emp.exclusion_status = status["exclusion_status"]
            emp.exclusion_category = (
                ExclusionCategory(status["exclusion_category"])
                if status["exclusion_category"]
                else None
            )
            if status["exclusion_status"]:
                excluded += 1

        self._session.commit()
        return {
            "evaluated": evaluated,
            "excluded": excluded,
            "hris_fetched": hris_sync["fetched"],
            "hris_flagged_for_manual_review": hris_sync["flagged_for_manual_review"],
            "hris_adapter_failures": hris_sync["adapter_failures"],
        }

    # ── internal ─────────────────────────────────────────────────────────────

    def _build_result(
        self,
        rows: list[Exclusion],
        employee_ids: list[int] | None,
    ) -> dict[int, dict[str, bool | str | None]]:
        """
        Resolve a flat list of Exclusion rows into one result entry per employee.

        Priority when multiple active exclusions exist for the same employee:
        1. HRIS-sourced over MANUAL (when HRIS is available)
        2. Otherwise first-found (deterministic via query ordering)

        The caller may pass employee_ids to fill in explicit zero-exclusion
        entries for employees who have no Exclusion records at all.
        """
        result: dict[int, dict[str, bool | str | None]] = {}

        # Pre-fill with non-excluded so every requested employee is represented
        if employee_ids is not None:
            for eid in employee_ids:
                result[eid] = {
                    "exclusion_status": False,
                    "exclusion_category": None,
                    "exclusion_source": None,
                }

        for row in rows:
            # Don't override an existing HRIS result with MANUAL (HRIS wins)
            existing = result.get(row.employee_id)
            if existing is not None:
                if self._hris_available and existing["exclusion_source"] == "hris":
                    continue  # keep the HRIS result

            result[row.employee_id] = {
                "exclusion_status": True,
                "exclusion_category": row.category.value
                if row.category is not None
                else None,
                "exclusion_source": row.source.value if row.source is not None else None,
            }

        return result

    # ── context manager helpers ───────────────────────────────────────────────

    @classmethod
    def using(
        cls, *, hris_available: bool = True
    ) -> "ExclusionEngine":
        """Create a service backed by a session from the factory."""
        factory = get_session_factory()
        session = factory()
        return cls(session, hris_available=hris_available)

    def close(self) -> None:
        """Close the underlying session."""
        self._session.close()
