"""
Tier-2 regression tests for the CBI scoring pipeline.

Tests the wiring of scorecbi() → extract_from_cbi() — verifying that
CBIResult subscale scores are used correctly for feature extraction.

Uses real CBI computation (no mocks for scorecbi or extract_from_cbi).
"""

import pytest
from datetime import date

from src.model.services.cbi import (
    CBIResult,
    CBISubscaleScores,
    CBIValidationError,
    scorecbi,
)
from src.model.services.feature_extraction import extract_from_cbi


class TestCbiToFeatureExtractionWiring:
    """
    Regression test: CBIResult from scorecbi() must flow into extract_from_cbi()
    so that subscale scores (not raw recomputation) are used for features.

    This is the CRITICAL-1 fix — prior to the fix, extract_from_cbi() was called
    directly without scorecbi() validation, bypassing the CBI instrument service.
    """

    def _valid_19_responses(self) -> list[float]:
        """Return a valid 19-item CBI response list (all 0-6)."""
        return [2.0] * 19

    def _cbi_result_from_responses(self, responses: list[float]) -> CBIResult:
        """Compute CBIResult for a response list."""
        return scorecbi(responses)

    def test_extract_from_cbi_accepts_cbi_result(self):
        """extract_from_cbi must accept a cbi_result parameter."""
        responses = self._valid_19_responses()
        cbi_result = self._cbi_result_from_responses(responses)
        feat = extract_from_cbi(
            responses=responses,
            seniority_tier=0,
            joining_date=date(2020, 1, 1),
            company_type="Product",
            wfh_setup=True,
            reference_date=date(2025, 5, 18),
            cbi_result=cbi_result,
        )
        assert feat.resource_allocation is not None
        assert feat.mental_fatigue_score is not None

    def test_cbi_result_overrides_raw_subscale_computation(self):
        """
        When cbi_result is provided, subscale scores must come from it,
        not from raw response recomputation.

        The CBIResult may differ from raw computation when NA items are
        handled differently or when the CBI validator applies imputation.
        """
        responses = self._valid_19_responses()
        cbi_result = self._cbi_result_from_responses(responses)

        # With cbi_result: subscale scores from CBIResult
        feat_with = extract_from_cbi(
            responses=responses,
            seniority_tier=0,
            joining_date=date(2020, 1, 1),
            cbi_result=cbi_result,
        )

        # Without cbi_result: subscale scores recomputed from raw responses
        # (result should be numerically equivalent for all-valid responses)
        feat_without = extract_from_cbi(
            responses=responses,
            seniority_tier=0,
            joining_date=date(2020, 1, 1),
            cbi_result=None,
        )

        assert feat_with.resource_allocation == feat_without.resource_allocation
        assert feat_with.mental_fatigue_score == feat_without.mental_fatigue_score

    def test_cbi_validation_error_propagates_from_scorecbi(self):
        """scorecbi() must raise CBIValidationError for invalid responses."""
        invalid_responses = [0.0] * 18  # wrong length
        with pytest.raises(CBIValidationError, match="expected 19"):
            scorecbi(invalid_responses)

    def test_cbi_result_produces_correct_subscales(self):
        """CBIResult subscales must match expected subscale means."""
        # All items at 3.0 → each subscale should be 50.0 (3.0/6.0 * 100)
        responses = [3.0] * 19
        result = scorecbi(responses)
        assert abs(result.subscales.personal - 50.0) < 0.01
        assert abs(result.subscales.work_related - 50.0) < 0.01
        assert abs(result.subscales.client_related - 50.0) < 0.01
        assert abs(result.composite - 50.0) < 0.01

    def test_extract_from_cbi_resource_allocation_from_cbi_result(self):
        """
        resource_allocation feature must equal the CBI WB subscale converted
        to model scale (0-6), sourced from cbi_result.
        """
        # All items at 0.0 → WB = 0.0 → resource_allocation = 0.0
        responses = [0.0] * 19
        cbi_result = scorecbi(responses)
        feat = extract_from_cbi(
            responses=responses,
            seniority_tier=0,
            joining_date=date(2020, 1, 1),
            cbi_result=cbi_result,
        )
        assert feat.resource_allocation == 0.0

        # All items at 6.0 → WB = 100.0 → resource_allocation = 6.0
        responses = [6.0] * 19
        cbi_result = scorecbi(responses)
        feat = extract_from_cbi(
            responses=responses,
            seniority_tier=0,
            joining_date=date(2020, 1, 1),
            cbi_result=cbi_result,
        )
        assert feat.resource_allocation == 6.0

    def test_extract_from_cbi_mental_fatigue_from_cbi_result(self):
        """
        mental_fatigue_score feature must equal the CBI PB subscale converted
        to model scale (0-6), sourced from cbi_result.
        """
        # All items at 0.0 → PB = 0.0 → mental_fatigue = 0.0
        responses = [0.0] * 19
        cbi_result = scorecbi(responses)
        feat = extract_from_cbi(
            responses=responses,
            seniority_tier=0,
            joining_date=date(2020, 1, 1),
            cbi_result=cbi_result,
        )
        assert feat.mental_fatigue_score == 0.0

        # All items at 6.0 → PB = 100.0 → mental_fatigue = 6.0
        responses = [6.0] * 19
        cbi_result = scorecbi(responses)
        feat = extract_from_cbi(
            responses=responses,
            seniority_tier=0,
            joining_date=date(2020, 1, 1),
            cbi_result=cbi_result,
        )
        assert feat.mental_fatigue_score == 6.0

    def test_extract_from_cbi_without_cbi_result_still_works(self):
        """
        extract_from_cbi must still work when cbi_result is not provided
        (backward compatibility for pulse path which doesn't use scorecbi).
        """
        responses = [3.0] * 19
        feat = extract_from_cbi(
            responses=responses,
            seniority_tier=1,
            joining_date=date(2023, 6, 15),
            company_type="Service",
            wfh_setup=False,
            reference_date=date(2025, 5, 18),
            cbi_result=None,  # pulse path
        )
        assert feat.company_type == 0.0  # Service
        assert feat.wfh_setup == 0.0      # False
        assert feat.seniority_tier == 1.0
        assert feat.tenure_days > 0
        assert 0.0 <= feat.resource_allocation <= 6.0
        assert 0.0 <= feat.mental_fatigue_score <= 6.0
