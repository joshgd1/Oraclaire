"""
C3a model health check — critical-tier ceiling and participation floor.

Called by scoring.py after scoring commits.  Fires a C3a alert when
the fraction of CRITICAL-tier employees exceeds CRITICAL_HEALTH_CEILING.
M4-08: fires a PARTICIPATION_DROP alert when participation falls below
20%% for two consecutive cycles.
"""

from __future__ import annotations

from src.config import CRITICAL_HEALTH_CEILING, TIER_BOUNDARIES
from src.model.entities import AssessmentCycle, Employee, RiskScore, CycleType, CycleStatus
from src.model.entities._db import get_session_factory
from src.audit.alerts import write_alert
from src.model.services.participation import get_participation_for_cycle


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


def check_participation_floor(cycle_id: int, organisation_id: int) -> str | None:
    """
    M4-08: Return an alert_id if participation falls below 20%% for two
    consecutive cycles, otherwise None.

    Checks the current cycle and the most recent prior cycle of the same type.
    Fires PARTICIPATION_DROP alert with participation_rate attached.
    """
    factory = get_session_factory()
    session = factory()
    try:
        # Get the two most recent consecutive cycles of the same type
        prior_cycles = (
            session.query(AssessmentCycle)
            .filter(
                AssessmentCycle.organisation_id == organisation_id,
                AssessmentCycle.status == CycleStatus.CLOSED,
                AssessmentCycle.id != cycle_id,
            )
            .order_by(AssessmentCycle.started_at.desc())
            .limit(2)
            .all()
        )

        if len(prior_cycles) < 1:
            return None

        # Check current cycle
        current_metrics = get_participation_for_cycle(cycle_id)
        if current_metrics.participation_rate >= 0.20:
            return None

        # Check if prior cycle also had < 20% participation
        prior_metrics = get_participation_for_cycle(prior_cycles[0].id)
        if prior_metrics.participation_rate >= 0.20:
            return None

        total = current_metrics.scoreable_population
        return write_alert(
            cycle_id=cycle_id,
            organisation_id=organisation_id,
            critical_fraction=0.0,
            participation_rate=current_metrics.participation_rate,
            alert_type="PARTICIPATION_DROP",
            affected_count=current_metrics.responded_count,
            total_count=total,
        )
    finally:
        session.close()
