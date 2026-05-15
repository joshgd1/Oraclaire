"""
Tier-1 unit tests for CBI instrument service.

Tests scoring logic against known CBI response patterns.
No real infra; no mocking needed.
"""

import pytest
from src.model.services.cbi import (
    scorecbi,
    composite_burnout_score,
    CBIValidationError,
    CBISubscaleScores,
)


class TestCBIValidation:
    """Input validation."""

    def test_rejects_wrong_length(self):
        with pytest.raises(CBIValidationError, match="expected 19"):
            scorecbi([0.0] * 18)

    def test_rejects_negative_value(self):
        responses = [0.0] * 19
        responses[0] = -0.1
        with pytest.raises(CBIValidationError, match="item 1"):
            scorecbi(responses)

    def test_rejects_value_above_max(self):
        responses = [0.0] * 19
        responses[0] = 6.1
        with pytest.raises(CBIValidationError, match="item 1"):
            scorecbi(responses)

    def test_rejects_none_on_non_cb_item(self):
        responses = [2.0] * 19
        responses[0] = None
        with pytest.raises(CBIValidationError, match="item 1.*PB"):
            scorecbi(responses)

    def test_accepts_none_on_cb_item_when_na_acceptable(self):
        responses = [2.0] * 19
        responses[12] = None  # item 13 (CB subscale)
        result = scorecbi(responses, na_acceptable=True)
        assert isinstance(result.subscales, CBISubscaleScores)
        assert result.valid_items == 18

    def test_rejects_none_on_cb_item_when_na_not_acceptable(self):
        responses = [2.0] * 19
        responses[12] = None
        with pytest.raises(CBIValidationError, match="item 13"):
            scorecbi(responses, na_acceptable=False)


class TestCBIScoring:
    """Subscale and composite score computation."""

    def _all(self, value: float) -> list[float]:
        """Return 19-item list with every item set to value."""
        return [float(value)] * 19

    def test_all_zero_returns_zero(self):
        result = scorecbi(self._all(0.0))
        assert result.subscales.personal == 0.0
        assert result.subscales.work_related == 0.0
        assert result.subscales.client_related == 0.0
        assert result.composite == 0.0

    def test_all_six_returns_100(self):
        result = scorecbi(self._all(6.0))
        assert result.subscales.personal == 100.0
        assert result.subscales.work_related == 100.0
        assert result.subscales.client_related == 100.0
        assert result.composite == 100.0

    def test_mixed_values(self):
        # Item 1 PB: 3.0 → 50.0; items 18 PB: 0.0; all others 0.0
        # Item 13 CB: None (na_acceptable)
        # PB: 8 items → [50.0, 0, 0, 0, 0, 0, 0, 0] → mean = 50/8 = 6.25
        responses = [3.0] + [0.0] * 11 + [None] + [0.0] * 5 + [0.0]  # 19 items
        result = scorecbi(responses, na_acceptable=True)
        assert abs(result.subscales.personal - 50.0 / 8.0) < 0.01
        assert result.subscales.work_related == 0.0
        assert result.subscales.client_related == 0.0
        assert result.valid_items == 18

    def test_high_personal_threshold(self):
        # PB items at 5.0 (83.3), WB/CB at 0.0
        responses = [5.0] * 6 + [0.0] * 13
        result = scorecbi(responses)
        assert result.subscales.is_high_personal() is True
        assert result.subscales.is_high_work_related() is False
        assert result.subscales.is_high_client_related() is False
        assert result.subscales.high_subscales() == ["personal"]

    def test_composite_burnout_score_convenience(self):
        responses = [2.0] * 19
        assert abs(composite_burnout_score(responses) - (2.0 * 100.0 / 6.0)) < 0.01

    def test_raw_item_scores_0_to_100(self):
        # Item 1 at 0 → 0; item 6 (index 5) at 6 → 100
        responses = [0.0, 0.0, 0.0, 0.0, 0.0, 6.0] + [3.0] * 13
        result = scorecbi(responses)
        assert result.raw_item_scores[0] == 0.0
        assert result.raw_item_scores[5] == 100.0
        assert len(result.raw_item_scores) == 19
