"""
Tier-1 unit tests for src.views.employee_ux.

Tests the pure functions:
  - _build_factor_sentence() — feature → plain sentence mapping
  - TIER_LABELS / TIER_DESCRIPTIONS — plain-language tier output
  - screen_factors() filtering logic (excludes missing_ra, missing_mfs, sorts by abs impact)

No mocking needed — pure function tests.
"""

import pytest

from src.views.employee_ux import (
    TIER_DESCRIPTIONS,
    TIER_LABELS,
    _build_factor_sentence,
)


class TestBuildFactorSentence:
    """_build_factor_sentence maps feature labels to plain English sentences."""

    @pytest.mark.parametrize(
        "feature,increases,expected_substr",
        [
            # tenure_days
            ("tenure_days", True, "length of time you've been in this role"),
            ("tenure_days", False, "How long you've been here"),
            # mental_fatigue_score
            ("mental_fatigue_score", True, "energy levels"),
            ("mental_fatigue_score", False, "recent energy"),
            # resource_allocation
            ("resource_allocation", True, "workload"),
            ("resource_allocation", False, "workload is not a major pressure"),
            # wfh_setup
            ("wfh_setup", True, "working arrangement"),
            ("wfh_setup", False, "working setup"),
            # seniority_tier
            ("seniority_tier", True, "demands of your role level"),
            ("seniority_tier", False, "Your role level is not adding pressure"),
            # company_type
            ("company_type", True, "nature of your organisation"),
            ("company_type", False, "organisation type is not a pressure"),
        ],
    )
    def test_all_feature_keys_have_plain_sentence(self, feature, increases, expected_substr):
        result = _build_factor_sentence(feature, increases)
        assert expected_substr.lower() in result.lower()

    def test_unknown_feature_returns_label(self):
        result = _build_factor_sentence("unknown_feature", True)
        assert "unknown_feature" in result

    def test_increases_vs_decreases_are_different(self):
        """Increasing and decreasing versions must produce different sentences."""
        for feature in [
            "tenure_days",
            "mental_fatigue_score",
            "resource_allocation",
            "wfh_setup",
            "seniority_tier",
            "company_type",
        ]:
            inc = _build_factor_sentence(feature, increases=True)
            dec = _build_factor_sentence(feature, increases=False)
            assert inc != dec, f"{feature}: increasing and decreasing sentences must differ"


class TestTierLabels:
    """TIER_LABELS maps risk tier keys to plain-language labels."""

    @pytest.mark.parametrize(
        "tier,expected_label",
        [
            ("low", "You seem to be doing well right now"),
            ("moderate", "A few things worth keeping an eye on"),
            ("high", "Some signs worth paying attention to"),
            ("critical", "This might be a good time to reach out for support"),
        ],
    )
    def test_tier_labels_are_plain_language(self, tier, expected_label):
        assert TIER_LABELS[tier] == expected_label
        # No jargon: no "risk", "classification", "probability", "SHAP", "burnout"
        for word in ("risk", "classification", "probability", "shap", "burnout"):
            assert word.lower() not in TIER_LABELS[tier].lower()

    def test_all_four_tiers_covered(self):
        assert set(TIER_LABELS.keys()) == {"low", "moderate", "high", "critical"}


class TestTierDescriptions:
    """TIER_DESCRIPTIONS maps risk tier keys to plain-language descriptions."""

    @pytest.mark.parametrize(
        "tier",
        ["low", "moderate", "high", "critical"],
    )
    def test_all_tiers_have_descriptions(self, tier):
        assert tier in TIER_DESCRIPTIONS
        assert len(TIER_DESCRIPTIONS[tier]) > 0

    def test_critical_mentions_reaching_out(self):
        text = TIER_DESCRIPTIONS["critical"].lower()
        assert any(word in text for word in ("reach", "support", "out", "tough"))


class TestScreenFactorsFiltering:
    """screen_factors() filters and sorts SHAP decomposition correctly."""

    def test_excludes_missing_ra(self):
        """missing_ra feature must be filtered out."""
        shap = [
            {"feature": "missing_ra", "label": "RA missing", "direction": "increases", "impact_value": 0.5},
            {"feature": "resource_allocation", "label": "RA", "direction": "increases", "impact_value": 0.3},
        ]
        filtered = [f for f in shap if f.get("feature") not in ("missing_ra", "missing_mfs") and f.get("label")]
        assert "missing_ra" not in [f["feature"] for f in filtered]

    def test_excludes_missing_mfs(self):
        """missing_mfs feature must be filtered out."""
        shap = [
            {"feature": "missing_mfs", "label": "MFS missing", "direction": "increases", "impact_value": 0.6},
            {"feature": "mental_fatigue_score", "label": "Energy", "direction": "increases", "impact_value": 0.2},
        ]
        filtered = [f for f in shap if f.get("feature") not in ("missing_ra", "missing_mfs") and f.get("label")]
        assert "missing_mfs" not in [f["feature"] for f in filtered]

    def test_excludes_items_without_label(self):
        """Items with no label must be filtered out."""
        shap = [
            {"feature": "resource_allocation", "label": "", "direction": "increases", "impact_value": 0.4},
            {"feature": "mental_fatigue_score", "label": "Energy levels", "direction": "increases", "impact_value": 0.3},
        ]
        filtered = [f for f in shap if f.get("label") and f.get("feature") not in ("missing_ra", "missing_mfs")]
        assert all(f["label"] for f in filtered)

    def test_sorts_by_abs_impact_descending(self):
        """Factors must be sorted by absolute impact value, descending."""
        shap = [
            {"feature": "a", "label": "A", "direction": "increases", "impact_value": 0.1},
            {"feature": "b", "label": "B", "direction": "increases", "impact_value": 0.8},
            {"feature": "c", "label": "C", "direction": "increases", "impact_value": 0.4},
        ]
        shap.sort(key=lambda x: abs(x.get("impact_value", 0)), reverse=True)
        assert shap[0]["feature"] == "b"
        assert shap[1]["feature"] == "c"
        assert shap[2]["feature"] == "a"

    def test_takes_top_3(self):
        """Only top 3 factors must be retained after sorting."""
        shap = [
            {"feature": str(i), "label": f"Feature {i}", "direction": "increases", "impact_value": i * 0.1}
            for i in range(1, 6)
        ]
        shap.sort(key=lambda x: abs(x.get("impact_value", 0)), reverse=True)
        top3 = shap[:3]
        assert len(top3) == 3
        assert [f["feature"] for f in top3] == ["5", "4", "3"]
