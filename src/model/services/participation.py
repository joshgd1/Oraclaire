"""
Participation tracking service — M4-07.

Computes participation metrics per cycle:
  - scoreable_population: employees consented and not excluded
  - responded_count: employees with submitted responses
  - participation_rate: responded / scoreable

Targets tracked per D7, D13:
  - Sprint 1 gate: >= 20% participation
  - Architecture target: >= 40% participation
"""

from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.model.entities import AssessmentCycle, AssessmentResponse, Employee, ConsentStatus, CycleStatus
from src.model.entities._db import get_session_factory


@dataclass(frozen=True)
class ParticipationMetrics:
    cycle_id: int
    scoreable_population: int
    responded_count: int
    participation_rate: float  # 0.0 - 1.0

    @property
    def rate_percent(self) -> float:
        return self.participation_rate * 100.0

    def meets_sprint1_target(self) -> bool:
        """D7: Sprint 1 gate is 20% participation."""
        return self.participation_rate >= 0.20

    def meets_architecture_target(self) -> bool:
        """D13: Architecture target is 40% participation."""
        return self.participation_rate >= 0.40


def get_participation_for_cycle(cycle_id: int) -> ParticipationMetrics:
    """
    Compute participation metrics for a single cycle.

    Scoreable population = employees who are consented + not excluded,
    in the same organisation as the cycle.
    """
    factory = get_session_factory()
    session = factory()
    try:
        cycle = session.query(AssessmentCycle).filter(
            AssessmentCycle.id == cycle_id
        ).first()
        if not cycle:
            raise ValueError(f"cycle {cycle_id} not found")

        org_id = cycle.organisation_id

        # Scoreable: consented + not excluded in the same org
        scoreable = session.query(func.count(Employee.id)).filter(
            Employee.organisation_id == org_id,
            Employee.consent_status == ConsentStatus.CONSENTED,
            Employee.exclusion_status == False,  # noqa: E712
        ).scalar() or 0

        # Responded: employees with at least one submitted response for this cycle
        responded = session.query(
            func.count(func.distinct(AssessmentResponse.employee_id))
        ).join(
            Employee, AssessmentResponse.employee_id == Employee.id
        ).filter(
            AssessmentResponse.cycle_id == cycle_id,
            AssessmentResponse.submitted_at.isnot(None),
            Employee.organisation_id == org_id,
        ).scalar() or 0

        rate = (responded / scoreable) if scoreable > 0 else 0.0

        return ParticipationMetrics(
            cycle_id=cycle_id,
            scoreable_population=scoreable,
            responded_count=responded,
            participation_rate=rate,
        )
    finally:
        session.close()


def update_participation_for_cycle(cycle_id: int, organisation_id: int) -> ParticipationMetrics:
    """
    M4-07 wire: triggered on every response submission and on cycle close.

    Returns the current participation metrics. Alerts on participation drop
    below 20% (D7) are handled by M4-08.
    """
    return get_participation_for_cycle(cycle_id)
