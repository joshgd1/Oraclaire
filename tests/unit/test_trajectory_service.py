"""
Tier-1 unit tests for src.model.services.trajectory.

Tests the TrajectoryClassificationService.classify() boundary conditions
and _get_threshold() fallback logic using mocked RiskScore queries.

Uses mocking (allowed at Tier 1) to isolate the classification logic.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.model.services.trajectory import (
    DEFAULT_TRAJECTORY_THRESHOLD,
    TrajectoryClassificationService,
    TrajectoryResult,
    _get_threshold,
)


class TestGetThreshold:
    """_get_threshold falls back to DEFAULT_TRAJECTORY_THRESHOLD on error."""

    def test_returns_default_when_no_session(self):
        result = _get_threshold(None, organisation_id=999)
        assert result == DEFAULT_TRAJECTORY_THRESHOLD

    def test_returns_default_when_deployment_parameter_not_set(self):
        mock_session = MagicMock()
        with patch("src.model.services.trajectory.DeploymentParameterService") as MockDP:
            MockDP.return_value.get_typed.return_value = None
            result = _get_threshold(mock_session, organisation_id=999)
        assert result == DEFAULT_TRAJECTORY_THRESHOLD

    def test_returns_casted_float_when_set(self):
        mock_session = MagicMock()
        with patch("src.model.services.trajectory.DeploymentParameterService") as MockDP:
            MockDP.return_value.get_typed.return_value = "0.15"
            result = _get_threshold(mock_session, organisation_id=999)
        assert result == 0.15  # float("0.15")


class TestTrajectoryClassification:
    """TrajectoryClassificationService.classify() boundary conditions."""

    def _mock_score(self, numeric_score: float):
        m = MagicMock()
        m.numeric_score = numeric_score
        return m

    def _mock_query(self, scores):
        m = MagicMock()
        m.filter.return_value.order_by.return_value.all.return_value = scores
        return m

    def test_no_trajectory_when_single_score(self):
        """One score → no_trajectory."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            self._mock_score(0.3)
        ]
        svc = TrajectoryClassificationService(session=mock_session)
        result = svc.classify(employee_id=1, organisation_id=1)
        assert result.trajectory == "no_trajectory"
        assert result.cycles_compared is None
        assert result.current_score == 0.3

    def test_no_trajectory_when_no_scores(self):
        """Zero scores → no_trajectory with None current."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        svc = TrajectoryClassificationService(session=mock_session)
        result = svc.classify(employee_id=1, organisation_id=1)
        assert result.trajectory == "no_trajectory"
        assert result.current_score is None
        assert result.cycles_compared is None

    def test_improved_when_delta_below_negative_threshold(self):
        """delta < -threshold → improved."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            self._mock_score(0.5),
            self._mock_score(0.3),
        ]
        with patch("src.model.services.trajectory._get_threshold", return_value=0.10):
            svc = TrajectoryClassificationService(session=mock_session)
            result = svc.classify(employee_id=1, organisation_id=1)
        assert result.trajectory == "improved"
        assert result.delta == -0.2
        assert result.current_score == 0.3
        assert result.previous_score == 0.5

    def test_worsened_when_delta_above_positive_threshold(self):
        """delta > +threshold → worsened."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            self._mock_score(0.2),
            self._mock_score(0.5),
        ]
        with patch("src.model.services.trajectory._get_threshold", return_value=0.10):
            svc = TrajectoryClassificationService(session=mock_session)
            result = svc.classify(employee_id=1, organisation_id=1)
        assert result.trajectory == "worsened"
        assert result.delta == 0.3

    def test_held_when_delta_within_threshold_band(self):
        """|delta| <= threshold → held."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            self._mock_score(0.5),
            self._mock_score(0.52),
        ]
        with patch("src.model.services.trajectory._get_threshold", return_value=0.10):
            svc = TrajectoryClassificationService(session=mock_session)
            result = svc.classify(employee_id=1, organisation_id=1)
        assert result.trajectory == "held"
        assert result.delta == pytest.approx(0.02)

    def test_improved_exactly_at_negative_threshold(self):
        """delta exactly = -threshold → held (not improved)."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            self._mock_score(0.5),
            self._mock_score(0.4),
        ]
        with patch("src.model.services.trajectory._get_threshold", return_value=0.10):
            svc = TrajectoryClassificationService(session=mock_session)
            result = svc.classify(employee_id=1, organisation_id=1)
        assert result.trajectory == "held"  # exactly at boundary → held

    def test_worsened_exactly_at_positive_threshold(self):
        """delta exactly = +threshold → held (not worsened)."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            self._mock_score(0.4),
            self._mock_score(0.5),
        ]
        with patch("src.model.services.trajectory._get_threshold", return_value=0.10):
            svc = TrajectoryClassificationService(session=mock_session)
            result = svc.classify(employee_id=1, organisation_id=1)
        assert result.trajectory == "held"  # exactly at boundary → held

    def test_uses_most_recent_two_scores(self):
        """Most recent two scores (by scored_at asc) are used."""
        mock_session = MagicMock()
        # Scores ordered oldest → newest: 0.1, 0.2, 0.8, 0.9
        # Should compare 0.8 → 0.9 (worsened by 0.1, threshold 0.10 → held)
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            self._mock_score(0.1),
            self._mock_score(0.2),
            self._mock_score(0.8),
            self._mock_score(0.9),
        ]
        with patch("src.model.services.trajectory._get_threshold", return_value=0.10):
            svc = TrajectoryClassificationService(session=mock_session)
            result = svc.classify(employee_id=1, organisation_id=1)
        assert result.previous_score == 0.8
        assert result.current_score == 0.9
        assert result.cycles_compared == 2

    def test_for_employee_convenience_classmethod(self):
        """for_employee() is a convenience wrapper that opens/closes its own session."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        mock_session.close = MagicMock()

        # Patch at the module where get_session_factory is bound
        with patch("src.model.services.trajectory.get_session_factory", return_value=mock_session):
            result = TrajectoryClassificationService.for_employee(employee_id=1, organisation_id=1)
        assert result.trajectory == "no_trajectory"

    def test_result_dataclass_fields(self):
        """TrajectoryResult has all required fields."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            self._mock_score(0.3),
            self._mock_score(0.1),
        ]
        with patch("src.model.services.trajectory._get_threshold", return_value=0.10):
            svc = TrajectoryClassificationService(session=mock_session)
            result = svc.classify(employee_id=42, organisation_id=7)
        assert isinstance(result, TrajectoryResult)
        assert result.employee_id == 42
        assert result.trajectory == "improved"
        assert result.threshold_used == 0.10
        assert result.cycles_compared == 2
