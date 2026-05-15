"""
C3a model health check — critical-tier ceiling and participation floor.

Called by scoring.py after scoring commits.  Fires a C3a alert when
the fraction of CRITICAL-tier employees exceeds CRITICAL_HEALTH_CEILING.
M4-08: fires a PARTICIPATION_DROP alert when participation falls below
20%% for two consecutive cycles.
"""

from __future__ import annotations

from src.config import (
    CRITICAL_HEALTH_CEILING,
    MIN_TEAM_SIZE,
    ORT_CEILING,
    ORT_PULSE_CONSECUTIVE_WEEKS,
    ORT_TRIGGER_QUARTERLY,
    TIER_BOUNDARIES,
)
from src.model.entities import AssessmentCycle, Employee, RiskScore, CycleType, CycleStatus, Team
from src.model.entities._db import get_session_factory
from src.audit.alerts import write_alert
from src.model.services.participation import get_participation_for_cycle
from src.model.services.deployment_parameter import DeploymentParameterService


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


def check_organisational_risk_threshold(
    cycle_id: int,
    organisation_id: int,
) -> dict[int, dict]:
    """
    M6-04: Check Organisational Risk Threshold per team.

    Computes High+Critical combined rate for each team.  Triggers an ORT
    alert when the rate exceeds ORT_CEILING for ORT_TRIGGER_WEEKS (weekly
    pulse) or ORT_TRIGGER_QUARTERLY (quarterly CBI) consecutive cycles.

    Weekly pulse (pulse cycle):  ORT_TRIGGER_WEEKS = 2 consecutive weeks.
    Quarterly CBI:                 ORT_TRIGGER_QUARTERLY = 1 (single cycle).

    Returns a dict keyed by team_id:
      {team_id: {"alert_id": <str>, "hc_pct": float, "weeks": int}}

    An empty dict means no ORT alerts fired.  The caller (scoring pipeline)
    uses the returned dict to suppress individual team alerts for teams
    that triggered ORT.

    Rules:
    - Teams below MIN_TEAM_SIZE are excluded from ORT evaluation.
    - Consecutive-week counters are persisted per team via DeploymentParameter
      with keys ``ort_consecutive_<team_id>``.
    """
    factory = get_session_factory()
    session = factory()
    try:
        # ── resolve cycle type ─────────────────────────────────────────────
        cycle = session.query(AssessmentCycle).filter(
            AssessmentCycle.id == cycle_id,
        ).first()
        if cycle is None:
            return {}
        is_pulse = cycle.cycle_type == CycleType.PULSE
        trigger_weeks = ORT_PULSE_CONSECUTIVE_WEEKS if is_pulse else ORT_TRIGGER_QUARTERLY

        # ── fetch org's teams ──────────────────────────────────────────────
        teams = session.query(Team).filter(
            Team.organisation_id == organisation_id,
        ).all()

        dp_svc = DeploymentParameterService(session)
        ort_results: dict[int, dict] = {}

        for team in teams:
            if team.member_count < MIN_TEAM_SIZE:
                continue

            # ── High+Critical rate for this team / cycle ───────────────────
            total = session.query(Employee).filter(
                Employee.team_id == team.id,
                Employee.organisation_id == organisation_id,
                Employee.consent_status != "withdrawn",
                Employee.exclusion_status == False,  # noqa: E712
            ).count()

            if total == 0:
                continue

            hc_count = session.query(RiskScore).join(
                Employee, RiskScore.employee_id == Employee.id
            ).filter(
                RiskScore.cycle_id == cycle_id,
                RiskScore.risk_tier.in_(("high", "critical")),
                Employee.team_id == team.id,
                Employee.organisation_id == organisation_id,
                Employee.consent_status != "withdrawn",
                Employee.exclusion_status == False,  # noqa: E712
            ).count()

            hc_pct = hc_count / total

            # ── consecutive-weeks counter ───────────────────────────────────
            counter_key = f"ort_consecutive_{team.id}"
            consecutive = dp_svc.get_typed(organisation_id, counter_key) or 0

            if hc_pct > ORT_CEILING:
                consecutive += 1
                dp_svc.set(organisation_id, counter_key, consecutive)
            else:
                # Reset on improvement
                if consecutive > 0:
                    dp_svc.set(organisation_id, counter_key, 0)
                consecutive = 0

            # ── fire ORT alert? ──────────────────────────────────────────
            if hc_pct > ORT_CEILING and consecutive >= trigger_weeks:
                alert_id = write_alert(
                    cycle_id=cycle_id,
                    organisation_id=organisation_id,
                    critical_fraction=hc_pct,
                    affected_count=hc_count,
                    total_count=total,
                    ceiling=ORT_CEILING,
                    alert_type="ORT_THRESHOLD_EXCEEDED",
                    team_id=team.id,
                    team_name=team.name,
                )
                ort_results[team.id] = {
                    "alert_id": alert_id,
                    "hc_pct": hc_pct,
                    "weeks": consecutive,
                    "team_name": team.name,
                }

        return ort_results
    finally:
        session.close()
