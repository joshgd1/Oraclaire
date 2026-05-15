"""
Feature extraction for the scoring pipeline.

Converts CBI/pulse AssessmentResponse rows + Employee records into the
10 model input features defined in config.FEATURES.

Feature mapping (from train.py engineer_features):

  company_type        — from Organisation.company_type ("Product"=1, "Service"=0)
  wfh_setup          — from Employee.wfh_setup_available ("Yes"=1, "No"=0)
  resource_allocation — CBI Work-Related Burnout subscale (items 7-12), 0-100 → 0-6
  mental_fatigue_score — CBI Personal Burnout subscale (items 1-6,18,19), 0-100 → 0-6
  missing_ra         — 1 if resource_allocation derived from insufficient CBI items
  missing_mfs        — 1 if mental_fatigue derived from insufficient CBI items
  seniority_tier      — from Employee.seniority_tier
  tenure_days        — days from Employee.date_of_joining to today
  tenure_fatigue     — tenure_days × mental_fatigue_score (scaled)
  tenure_workload    — tenure_days × resource_allocation (scaled)

Reference: product-identity.md §3, cost-model.md §1-2,
config.FEATURES, train.py engineer_features.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from src.config import FEATURES, SENIORITY_DESIGNATION_CUTOFF

# CBI item index constants (0-based)
_CBI_PB_ITEMS = {0, 1, 2, 3, 4, 5, 17, 18}   # Personal Burnout items
_CBI_WB_ITEMS = {6, 7, 8, 9, 10, 11}           # Work-Related Burnout items


@dataclass
class ExtractedFeatures:
    company_type: float
    wfh_setup: float
    resource_allocation: float
    mental_fatigue_score: float
    missing_ra: float
    missing_mfs: float
    seniority_tier: float
    tenure_days: float
    tenure_fatigue: float
    tenure_workload: float

    def to_list(self) -> list[float]:
        return [
            self.company_type,
            self.wfh_setup,
            self.resource_allocation,
            self.mental_fatigue_score,
            self.missing_ra,
            self.missing_mfs,
            self.seniority_tier,
            self.tenure_days,
            self.tenure_fatigue,
            self.tenure_workload,
        ]

    def to_dict(self) -> dict[str, float]:
        return {
            "company_type": self.company_type,
            "wfh_setup": self.wfh_setup,
            "resource_allocation": self.resource_allocation,
            "mental_fatigue_score": self.mental_fatigue_score,
            "missing_ra": self.missing_ra,
            "missing_mfs": self.missing_mfs,
            "seniority_tier": self.seniority_tier,
            "tenure_days": self.tenure_days,
            "tenure_fatigue": self.tenure_fatigue,
            "tenure_workload": self.tenure_workload,
        }


def _cb_to_model_scale(cb_score: float) -> float:
    """Convert CBI 0-100 subscale score to model 0-6 scale."""
    return cb_score / 100.0 * 6.0


def _compute_tenure(joining_date: date, reference_date: date | None = None) -> float:
    """Days from joining_date to reference_date (default: today)."""
    if reference_date is None:
        reference_date = date.today()
    delta = reference_date - joining_date
    return max(0.0, float(delta.days))


def _compute_missing_ra(responses: list[float | None]) -> float:
    """1 if fewer than 4 WB items (7-12) have responses."""
    wb_answered = sum(1 for i in _CBI_WB_ITEMS if responses[i] is not None)
    return 1.0 if wb_answered < 4 else 0.0


def _compute_missing_mfs(responses: list[float | None]) -> float:
    """1 if fewer than 5 PB items (0-5, 17, 18) have responses."""
    pb_answered = sum(1 for i in _CBI_PB_ITEMS if responses[i] is not None)
    return 1.0 if pb_answered < 5 else 0.0


def _mean_subscale(
    responses: list[float | None],
    item_indices: set[int],
    missing_indicator: float,
) -> tuple[float, float]:
    """
    Compute subscale mean (0-100) and whether it should be flagged as missing.

    Returns (subscale_mean, missing_flag).
    """
    valid = [responses[i] for i in item_indices if responses[i] is not None]
    if not valid:
        return 0.0, 1.0
    return sum(valid) / len(valid) * (100.0 / 6.0), missing_indicator


def extract_from_cbi(
    responses: list[float | None],
    seniority_tier: int,
    joining_date: date | None,
    company_type: Literal["Product", "Service"] | None = None,
    wfh_setup: bool | None = None,
    reference_date: date | None = None,
) -> ExtractedFeatures:
    """
    Extract all 10 model features from a 19-item CBI response list.

    Parameters
    ----------
    responses:
        List of 19 numeric responses (0–6) in CBI item order.
        None for missing/unanswered items.
    seniority_tier:
        0 = junior (Threshold A), 1 = senior (Threshold B).
    joining_date:
        Employee's start date, used to compute tenure.
    company_type:
        "Product"=1, "Service"=0. Defaults to 0 (safe/fail-closed).
    wfh_setup:
        True = "Yes"=1, False = "No"=0. Defaults to 0.
    reference_date:
        Override for tenure calculation (useful for testing with fixed date).

    Returns
    -------
    ExtractedFeatures
        All 10 model input features, on the same scale as train.py.

    Raises
    ------
    ValueError
        If seniority_tier is not 0 or 1.
    """
    if seniority_tier not in (0, 1):
        raise ValueError(f"seniority_tier must be 0 or 1, got {seniority_tier}")

    if len(responses) != 19:
        raise ValueError(f"expected 19 CBI responses, got {len(responses)}")

    # Missing indicators
    missing_ra = _compute_missing_ra(responses)
    missing_mfs = _compute_missing_mfs(responses)

    # Subscale means (0-100)
    resource_raw, _ = _mean_subscale(responses, _CBI_WB_ITEMS, missing_ra)
    fatigue_raw, _ = _mean_subscale(responses, _CBI_PB_ITEMS, missing_mfs)

    # Impute with median if missing (same as train.py engineer_features)
    RA_MEDIAN_CBI = 3.5 * (100.0 / 6.0)   # Kaggle train median ≈ 3.5/6
    MFS_MEDIAN_CBI = 3.5 * (100.0 / 6.0)

    if missing_ra:
        resource_raw = RA_MEDIAN_CBI
    if missing_mfs:
        fatigue_raw = MFS_MEDIAN_CBI

    # Model-scale (0-6)
    resource_allocation = _cb_to_model_scale(resource_raw)
    mental_fatigue_score = _cb_to_model_scale(fatigue_raw)

    # Tenure — if joining_date is None, default to 0 (safe fail-closed)
    if joining_date is None:
        tenure_days = 0.0
    else:
        tenure_days = _compute_tenure(joining_date, reference_date)

    # Interaction terms (same scale as train.py)
    tenure_fatigue = tenure_days * mental_fatigue_score
    tenure_workload = tenure_days * resource_allocation

    # Categorical encodings (same as train.py engineer_features)
    company_type_enc = 1.0 if company_type == "Product" else 0.0
    wfh_setup_enc = 1.0 if wfh_setup else 0.0

    return ExtractedFeatures(
        company_type=company_type_enc,
        wfh_setup=wfh_setup_enc,
        resource_allocation=resource_allocation,
        mental_fatigue_score=mental_fatigue_score,
        missing_ra=missing_ra,
        missing_mfs=missing_mfs,
        seniority_tier=float(seniority_tier),
        tenure_days=tenure_days,
        tenure_fatigue=tenure_fatigue,
        tenure_workload=tenure_workload,
    )


def extract_from_pulse(
    pulse_response: float,
    seniority_tier: int,
    joining_date: date | None,
    company_type: Literal["Product", "Service"] | None = None,
    wfh_setup: bool | None = None,
    reference_date: date | None = None,
) -> ExtractedFeatures:
    """
    Extract model features from a single pulse response.

    Pulse is one CBI item (item index 0, personal burnout).
    Both resource_allocation and mental_fatigue_score are set to the pulse
    response scaled as a CBI subscale score. Missing indicators are set
    to 0 (pulse is not considered a missing signal for either subscale).

    Parameters
    ----------
    pulse_response:
        Single CBI item response (0–6).
    seniority_tier:
        0 = junior (Threshold A), 1 = senior (Threshold B).
    joining_date:
        Employee's start date.
    company_type:
        "Product"=1, "Service"=0.
    wfh_setup:
        True = "Yes"=1, False = "No"=0.
    reference_date:
        Override for tenure calculation.

    Returns
    -------
    ExtractedFeatures
    """
    if not (0.0 <= pulse_response <= 6.0):
        raise ValueError(f"pulse_response must be in [0, 6], got {pulse_response}")

    # Pulse is one item — use it as both subscales
    fatigue_raw = pulse_response * (100.0 / 6.0)
    resource_raw = fatigue_raw

    mental_fatigue_score = pulse_response
    resource_allocation = pulse_response

    if joining_date is None:
        tenure_days = 0.0
    else:
        tenure_days = _compute_tenure(joining_date, reference_date)
    tenure_fatigue = tenure_days * mental_fatigue_score
    tenure_workload = tenure_days * resource_allocation

    company_type_enc = 1.0 if company_type == "Product" else 0.0
    wfh_setup_enc = 1.0 if wfh_setup else 0.0

    return ExtractedFeatures(
        company_type=company_type_enc,
        wfh_setup=wfh_setup_enc,
        resource_allocation=resource_allocation,
        mental_fatigue_score=mental_fatigue_score,
        missing_ra=0.0,
        missing_mfs=0.0,
        seniority_tier=float(seniority_tier),
        tenure_days=tenure_days,
        tenure_fatigue=tenure_fatigue,
        tenure_workload=tenure_workload,
    )
