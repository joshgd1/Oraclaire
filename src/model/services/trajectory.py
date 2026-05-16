"""
TrajectoryClassificationService — M5-07.

Compares an employee's risk scores across cycles to classify their trajectory:
  - improved  — numeric_score decreased by more than threshold
  - worsened  — numeric_score increased by more than threshold
  - held     — change within threshold band
  - no_trajectory — fewer than 2 scores (first cycle only)

Threshold is configurable via deployment parameter `trajectory_threshold`
(default 0.10 = 10 percentage points).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

from src.model.entities import Employee, RiskScore
from src.model.entities._db import get_session_factory
from src.model.services.deployment_parameter import DeploymentParameterService

log = structlog.get_logger(__name__)

# Default threshold: 10 percentage points of burnout risk score
DEFAULT_TRAJECTORY_THRESHOLD = 0.10


@dataclass
class TrajectoryResult:
    """Result of trajectory classification for one employee."""

    employee_id: int
    trajectory: str  # "improved" | "worsened" | "held" | "no_trajectory"
    current_score: float | None
    previous_score: float | None
    delta: float | None  # current - previous (negative = improved)
    cycles_compared: int | None  # None when no_trajectory
    threshold_used: float


def _get_threshold(session, organisation_id: int) -> float:
    try:
        dp_svc = DeploymentParameterService(session)
        threshold = dp_svc.get_typed(organisation_id, "trajectory_threshold")
        if threshold is not None:
            return float(threshold)
    except Exception:
        pass
    return DEFAULT_TRAJECTORY_THRESHOLD


class TrajectoryClassificationService:
    """
    Classifies employee burnout risk trajectory across scoring cycles.

    Requires minimum 2 RiskScore records for the employee.
    Classification:
      - improved:  current_score < previous_score - threshold
      - worsened:  current_score > previous_score + threshold
      - held:     within threshold band
      - no_trajectory: fewer than 2 scores
    """

    def __init__(self, session=None):
        self._session = session

    def classify(self, employee_id: int, organisation_id: int) -> TrajectoryResult:
        """
        Classify trajectory for one employee.

        Args:
            employee_id: PK of the employee
            organisation_id: PK of the organisation (for deployment parameter lookup)

        Returns:
            TrajectoryResult with classification + score details
        """
        factory = get_session_factory
        if self._session is None:
            session = factory()
            try:
                return self._classify(session, employee_id, organisation_id)
            finally:
                session.close()
        else:
            return self._classify(self._session, employee_id, organisation_id)

    def _classify(
        self, session, employee_id: int, organisation_id: int
    ) -> TrajectoryResult:
        threshold = _get_threshold(session, organisation_id)

        # Fetch all scores ordered oldest → newest
        scores = (
            session.query(RiskScore)
            .filter(RiskScore.employee_id == employee_id)
            .order_by(RiskScore.scored_at.asc())
            .all()
        )

        log.debug(
            "trajectory.classify",
            employee_id=employee_id,
            scores_found=len(scores),
        )

        if len(scores) < 2:
            return TrajectoryResult(
                employee_id=employee_id,
                trajectory="no_trajectory",
                current_score=scores[-1].numeric_score if scores else None,
                previous_score=None,
                delta=None,
                cycles_compared=None,
                threshold_used=threshold,
            )

        previous_score = scores[-2].numeric_score
        current_score = scores[-1].numeric_score
        delta = current_score - previous_score

        if delta < -threshold:
            trajectory = "improved"
        elif delta > threshold:
            trajectory = "worsened"
        else:
            trajectory = "held"

        log.info(
            "trajectory.result",
            employee_id=employee_id,
            trajectory=trajectory,
            current_score=current_score,
            previous_score=previous_score,
            delta=delta,
            threshold=threshold,
        )

        return TrajectoryResult(
            employee_id=employee_id,
            trajectory=trajectory,
            current_score=current_score,
            previous_score=previous_score,
            delta=delta,
            cycles_compared=2,
            threshold_used=threshold,
        )

    @classmethod
    def for_employee(cls, employee_id: int, organisation_id: int) -> TrajectoryResult:
        """Convenience: classify trajectory for one employee."""
        return cls().classify(employee_id, organisation_id)
