"""
RetentionEngine — M8-01.

Deletes individual-level records from cycles older than retention_months.
Triggered after a cycle closes (M8-02).

Records deleted in order (respects FK constraints):
  - AssessmentResponse  — per-cycle individual responses
  - RiskScore           — per-cycle individual risk scores
  - Withdrawal          — consent-withdrawn employees (cascade on employee delete)
  - Employee            — employee record itself (cascade removes related records)

Does NOT delete:
  - Organisation, Team, AssessmentCycle, AuditEntry, DeploymentParameter
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from src.model.entities._db import get_session_factory
from src.model.services.deployment_parameter import DeploymentParameterService

log = structlog.get_logger(__name__)


class RetentionEngine:
    """
    PII/data retention enforcer.

    Scans for cycles closed more than `retention_months` ago and purges
    individual-level records belonging to employees who have no scores in
    any non-expired cycle.
    """

    def __init__(self, session_factory=None):
        self._factory = session_factory or get_session_factory

    def run(self, organisation_id: int) -> dict[str, Any]:
        """
        Execute retention purge for one organisation.

        Returns a summary dict with counts of each record type deleted.
        """
        session = self._factory()
        try:
            return self._run(session, organisation_id)
        finally:
            session.close()

    def _run(self, session, organisation_id: int) -> dict[str, Any]:
        dp_svc = DeploymentParameterService(session)
        retention_months: int = dp_svc.get_typed(organisation_id, "retention_months") or 12
        cutoff = datetime.now(UTC) - timedelta(days=int(retention_months) * 30)

        log.info(
            "retention.run",
            organisation_id=organisation_id,
            retention_months=retention_months,
            cutoff=cutoff.isoformat(),
        )

        from src.model.entities import (
            AssessmentCycle,
            AssessmentResponse,
            CycleStatus,
            Employee,
            RiskScore,
        )

        # Cycles closed before cutoff
        old_cycles = (
            session.query(AssessmentCycle.id)
            .filter(
                AssessmentCycle.organisation_id == organisation_id,
                AssessmentCycle.status == CycleStatus.CLOSED,
                AssessmentCycle.closed_at.isnot(None),
                AssessmentCycle.closed_at < cutoff,
            )
            .all()
        )
        old_cycle_ids = [c.id for c in old_cycles]

        if not old_cycle_ids:
            log.info("retention.no_old_cycles", organisation_id=organisation_id)
            return {"cycles_scanned": 0, "records": {}}

        # Employees who have NO scores in any non-expired cycle
        # (cycles not in old_cycle_ids)
        recent_cycle_ids = [
            c.id
            for c in session.query(AssessmentCycle.id)
            .filter(
                AssessmentCycle.organisation_id == organisation_id,
                AssessmentCycle.status == CycleStatus.CLOSED,
                AssessmentCycle.closed_at >= cutoff,
            )
            .all()
        ]

        if recent_cycle_ids:
            # Employees with at least one score in a recent cycle — keep them
            retained_emp_ids = set(
                r[0]
                for r in session.query(RiskScore.employee_id)
                .filter(
                    RiskScore.cycle_id.in_(recent_cycle_ids),
                    RiskScore.employee_id.in_(
                        session.query(Employee.id).filter(
                            Employee.organisation_id == organisation_id
                        )
                    ),
                )
                .distinct()
                .all()
            )
            emp_ids_to_delete = (
                session.query(Employee.id)
                .filter(
                    Employee.organisation_id == organisation_id,
                    Employee.id.notin_(retained_emp_ids),
                )
                .all()
            )
        else:
            # No recent cycles — delete all employees in this org
            emp_ids_to_delete = (
                session.query(Employee.id)
                .filter(Employee.organisation_id == organisation_id)
                .all()
            )

        emp_ids = [e.id for e in emp_ids_to_delete]
        deleted: dict[str, int] = {}

        if emp_ids:
            # 1. AssessmentResponse for affected employees in old cycles
            ar_count = (
                session.query(AssessmentResponse)
                .filter(
                    AssessmentResponse.employee_id.in_(emp_ids),
                    AssessmentResponse.cycle_id.in_(old_cycle_ids),
                )
                .delete(synchronize_session=False)
            )
            deleted["assessment_responses"] = ar_count

            # 2. RiskScore for affected employees in old cycles
            rs_count = (
                session.query(RiskScore)
                .filter(
                    RiskScore.employee_id.in_(emp_ids),
                    RiskScore.cycle_id.in_(old_cycle_ids),
                )
                .delete(synchronize_session=False)
            )
            deleted["risk_scores"] = rs_count

            # 3. Employees (cascade deletes withdrawals, scores not in old cycles)
            emp_count = (
                session.query(Employee)
                .filter(Employee.id.in_(emp_ids))
                .delete(synchronize_session=False)
            )
            deleted["employees"] = emp_count

        session.commit()

        log.info(
            "retention.complete",
            organisation_id=organisation_id,
            old_cycles=len(old_cycle_ids),
            employees_deleted=deleted.get("employees", 0),
            records=deleted,
        )

        return {
            "old_cycles_scanned": len(old_cycle_ids),
            "cycle_ids": old_cycle_ids,
            "records": deleted,
        }

    @classmethod
    def for_organisation(cls, organisation_id: int) -> dict[str, Any]:
        """Convenience: run retention for one org."""
        return cls().run(organisation_id)

    @classmethod
    def run_all_orgs(cls) -> dict[int, dict[str, Any]]:
        """Run retention across all organisations."""
        from src.model.entities import Organisation

        factory = get_session_factory()
        session = factory()
        try:
            orgs = session.query(Organisation.id).all()
            results: dict[int, dict[str, Any]] = {}
            for (org_id,) in orgs:
                try:
                    results[org_id] = cls().run(org_id)
                except Exception as exc:
                    log.error("retention.org_failed", organisation_id=org_id, error=str(exc))
                    results[org_id] = {"error": str(exc)}
            return results
        finally:
            session.close()
