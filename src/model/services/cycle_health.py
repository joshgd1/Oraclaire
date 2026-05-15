"""
C3a model health check — critical-tier ceiling.

Called by scoring.py after scoring commits.  Fires a C3a alert when
the fraction of CRITICAL-tier employees exceeds CRITICAL_HEALTH_CEILING.
"""

from __future__ import annotations

from src.config import CRITICAL_HEALTH_CEILING, TIER_BOUNDARIES
from src.model.entities import Employee, RiskScore
from src.model.entities._db import get_session_factory
from src.audit.alerts import write_alert


def check_critical_ceiling(cycle_id: int, organisation_id: int) -> str | None:
    """
    Return an alert_id if CRITICAL-tier employees exceed the ceiling fraction,
    otherwise None.

    Uses a FK-column join (RiskScore.employee_id == Employee.id) to count
    scorable employees only (consent not withdrawn, not excluded).
    """
    factory = get_session_factory()
    session = factory()
    try:
        total = session.query(Employee).filter(
            Employee.organisation_id == organisation_id,
            Employee.consent_status != "withdrawn",
            Employee.exclusion_status == False,  # noqa: E712
        ).count()

        if total == 0:
            return None

        critical = session.query(RiskScore).join(
            Employee, RiskScore.employee_id == Employee.id
        ).filter(
            RiskScore.cycle_id == cycle_id,
            RiskScore.risk_tier == "critical",
            Employee.organisation_id == organisation_id,
            Employee.consent_status != "withdrawn",
            Employee.exclusion_status == False,  # noqa: E712
        ).count()

        fraction = critical / total

        if fraction > CRITICAL_HEALTH_CEILING:
            return write_alert(
                cycle_id=cycle_id,
                organisation_id=organisation_id,
                critical_fraction=fraction,
                affected_count=critical,
                total_count=total,
                ceiling=CRITICAL_HEALTH_CEILING,
            )

        return None
    finally:
        session.close()
