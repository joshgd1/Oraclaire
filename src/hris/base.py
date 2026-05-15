"""
Abstract HRIS adapter — defines the interface for all HRIS integrations.

Implementors: WorkdayAdapter, BambooHRAdapter, ManualAdapter.

The adapter is the source of truth for employee employment status used by the
ExclusionEngine.  It fetches raw HRIS data and translates it into Exclusion
records in the database.

Exclusion categories mapped from HRIS data:
  PIP                → ExclusionCategory.PIP
  ADA                → ExclusionCategory.ADA
  FMLA              → ExclusionCategory.FMLA
  WorkersComp        → ExclusionCategory.WORKERS_COMP
  Disciplinary       → ExclusionCategory.DISCIPLINARY
  GrievanceCooldown  → ExclusionCategory.GRIEVANCE_COOLDOWN
  MedicalLeave       → ExclusionCategory.MEDICAL_LEAVE
  ActiveIntervention → ExclusionCategory.ACTIVE_INTERVENTION
  Contractor         → ExclusionCategory.CONTRACTOR
  TestAccount        → ExclusionCategory.TEST_ACCOUNT
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from src.model.entities import Exclusion, ExclusionCategory, ExclusionSource
from src.model.entities._db import get_session_factory


@dataclass
class EmployeeRecord:
    """Canonical employee record fetched from an HRIS."""

    employee_id: int  # DB primary key (mapped via employee_mapping)
    external_id: str  # HRIS employee ID / employee number
    leave_status: list[str] = field(default_factory=list)
    contract_type: str | None = None  # "employee" | "contractor" | "test"
    disciplinary_active: bool = False
    grievance_active: bool = False
    active_intervention: bool = False


# Category mapping: HRIS leave type strings → ExclusionCategory enum values
LEAVE_CATEGORY_MAP: dict[str, ExclusionCategory] = {
    "pip": ExclusionCategory.PIP,
    "ada": ExclusionCategory.ADA,
    "fmla": ExclusionCategory.FMLA,
    "workers_comp": ExclusionCategory.WORKERS_COMP,
    "workers_compensation": ExclusionCategory.WORKERS_COMP,
    "disciplinary": ExclusionCategory.DISCIPLINARY,
    "grievance_cooldown": ExclusionCategory.GRIEVANCE_COOLDOWN,
    "medical_leave": ExclusionCategory.MEDICAL_LEAVE,
    "active_intervention": ExclusionCategory.ACTIVE_INTERVENTION,
}


class HRISAdapter(ABC):
    """
    Abstract HRIS adapter.

    Subclasses implement provider-specific fetch logic.  The adapter is used
    by ExclusionEngine via sync_exclusions() to reconcile Exclusion records
    with the current HRIS state.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name, e.g. 'Workday', 'BambooHR'."""

    @abstractmethod
    def is_available(self) -> bool:
        """
        Return True if the HRIS endpoint is reachable and credentials are
        configured.  Used by ExclusionEngine to decide whether to trust
        HRIS-sourced exclusions.
        """

    @abstractmethod
    def fetch_employees(self, organisation_id: int) -> list[EmployeeRecord]:
        """
        Fetch all employees for the given organisation from the HRIS.

        Returns a list of EmployeeRecord objects.  The caller maps these to DB
        employee IDs using the employee_mapping.
        """

    @abstractmethod
    def fetch_leave_status(
        self, employee_external_ids: list[str]
    ) -> dict[str, list[str]]:
        """
        Fetch active leave types for the given employee external IDs.

        Returns dict mapping external_id -> list of leave type strings
        (e.g. ["fmla", "ada"]).  Unknown employees return empty lists.
        """

    def employee_mapping(
        self, organisation_id: int, external_ids: list[str]
    ) -> dict[str, int]:
        """
        Map HRIS external IDs to DB employee IDs.

        Returns dict mapping external_id (str) -> employee_id (int).
        Employees not found in the DB are omitted.
        """
        factory = get_session_factory()
        session = factory()
        try:
            from src.model.entities import Employee

            rows = (
                session.query(Employee.id, Employee.id)
                .filter(Employee.organisation_id == organisation_id)
                .all()
            )
            # Simple implementation: external_id stored in a lookup field
            # Subclasses may override with provider-specific logic
            return {str(eid): eid for eid, in rows if str(eid) in external_ids}
        finally:
            session.close()

    def sync_exclusions(self, organisation_id: int) -> dict[str, int]:
        """
        Fetch current HRIS state and reconcile Exclusion records.

        Calls fetch_employees() and fetch_leave_status(), maps to DB employee
        IDs, then upserts Exclusion records with source=HRIS.

        Returns dict with keys:
          "processed": number of employees evaluated
          "exclusions_added": number of new Exclusion records created
          "exclusions_removed": number of HRIS-sourced records deactivated
        """
        if not self.is_available():
            return {"processed": 0, "exclusions_added": 0, "exclusions_removed": 0}

        employees = self.fetch_employees(organisation_id)
        external_ids = [e.external_id for e in employees]

        leave_map = self.fetch_leave_status(external_ids)
        db_id_map = self.employee_mapping(organisation_id, external_ids)

        now = datetime.now(timezone.utc)
        added = 0
        removed = 0

        factory = get_session_factory()
        session = factory()
        try:
            # Deactivate any existing HRIS-sourced exclusions for these employees
            # (they will be re-created if still applicable)
            active_hris = (
                session.query(Exclusion)
                .filter(
                    Exclusion.source == ExclusionSource.HRIS,
                    Exclusion.effective_to.is_(None),
                )
                .join(Exclusion.employee)
                .filter_by(organisation_id=organisation_id)
                .all()
            )

            still_excluded: set[int] = set()

            for emp in employees:
                db_id = db_id_map.get(emp.external_id)
                if db_id is None:
                    continue

                # Determine exclusion categories from HRIS data
                categories: list[ExclusionCategory] = []

                # Leave types
                for lt in leave_map.get(emp.external_id, []):
                    cat = LEAVE_CATEGORY_MAP.get(lt.lower())
                    if cat and cat not in categories:
                        categories.append(cat)

                # Contract type
                if emp.contract_type == "contractor":
                    if ExclusionCategory.CONTRACTOR not in categories:
                        categories.append(ExclusionCategory.CONTRACTOR)
                elif emp.contract_type == "test":
                    if ExclusionCategory.TEST_ACCOUNT not in categories:
                        categories.append(ExclusionCategory.TEST_ACCOUNT)

                # Disciplinary
                if emp.disciplinary_active and ExclusionCategory.DISCIPLINARY not in categories:
                    categories.append(ExclusionCategory.DISCIPLINARY)

                # Grievance cooldown
                if emp.grievance_active and ExclusionCategory.GRIEVANCE_COOLDOWN not in categories:
                    categories.append(ExclusionCategory.GRIEVANCE_COOLDOWN)

                # Active intervention
                if emp.active_intervention and ExclusionCategory.ACTIVE_INTERVENTION not in categories:
                    categories.append(ExclusionCategory.ACTIVE_INTERVENTION)

                if not categories:
                    continue

                still_excluded.add(db_id)

                # Upsert one Exclusion per category
                for cat in categories:
                    existing = (
                        session.query(Exclusion)
                        .filter(
                            Exclusion.employee_id == db_id,
                            Exclusion.category == cat,
                            Exclusion.source == ExclusionSource.HRIS,
                            Exclusion.effective_to.is_(None),
                        )
                        .first()
                    )
                    if existing is None:
                        session.add(
                            Exclusion(
                                employee_id=db_id,
                                category=cat,
                                source=ExclusionSource.HRIS,
                                effective_from=now,
                                effective_to=None,
                            )
                        )
                        added += 1

            # Deactivate HRIS exclusions for employees no longer excluded
            for exc in active_hris:
                if exc.employee_id not in still_excluded:
                    exc.effective_to = now
                    removed += 1

            session.commit()
            return {
                "processed": len(employees),
                "exclusions_added": added,
                "exclusions_removed": removed,
            }
        finally:
            session.close()
