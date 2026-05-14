"""
Two-threshold calibration and risk-tier classification.

Architecture (D11 Nuance 3, D17 confirmed):
  - Threshold A: general population (FN target 15%, FP ceiling 15%)
  - Threshold B: senior tier (FN target 10%, FP ceiling 20%)
  - Both read from config.py — update there, not here.
  - Risk tier boundaries from config.TIER_BOUNDARIES (D20 locked).

Calibration check:
  - Brier floor at config.BRIER_FLOOR (0.15).
  - If exceeded, Platt scaling applied before threshold selection.
  - Threshold drift tolerance: config.DRIFT_ACCEPTABLE_RANGE.

Seniority routing:
  - seniority_tier == 1 → Threshold B
  - seniority_tier == 0 → Threshold A
"""

import numpy as np
from sklearn.calibration import CalibratedClassifierCV

from src.config import (
    BRIER_FLOOR,
    DRIFT_ACCEPTABLE_RANGE,
    MODEL_ARTIFACT_PATH,
    THRESHOLD_A,
    THRESHOLD_B,
    TIER_BOUNDARIES,
    TIER_ORDER,
)

import joblib


def load_artifact(path: str = MODEL_ARTIFACT_PATH) -> dict:
    return joblib.load(path)


def check_calibration(brier_score: float) -> bool:
    """Return True if calibration passes (Brier below floor)."""
    return brier_score <= BRIER_FLOOR


def apply_platt_scaling(model, X_train: np.ndarray, y_train: np.ndarray):
    """Re-calibrate model probabilities using Platt scaling."""
    calibrated = CalibratedClassifierCV(model, cv="prefit", method="sigmoid")
    calibrated.fit(X_train, y_train)
    return calibrated


def get_threshold(seniority_tier: int) -> float:
    """Route to Threshold A (general) or Threshold B (senior)."""
    return THRESHOLD_B if seniority_tier == 1 else THRESHOLD_A


def classify_tier(probability: float) -> str:
    """Map probability to risk tier using config.TIER_BOUNDARIES."""
    for tier in TIER_ORDER:
        low, high = TIER_BOUNDARIES[tier]
        if low <= probability < high:
            return tier
    # Edge case: probability == 1.0 falls into critical
    if probability >= TIER_BOUNDARIES["critical"][0]:
        return "critical"
    return "low"


def score(
    probability: float,
    seniority_tier: int,
) -> dict:
    """Apply two-threshold architecture and classify into risk tier.

    Returns dict with probability, threshold_used, risk_tier, and seniority_tier.
    """
    threshold = get_threshold(seniority_tier)
    tier = classify_tier(probability)
    return {
        "probability": probability,
        "threshold_used": "B (senior)" if seniority_tier == 1 else "A (general)",
        "risk_tier": tier,
        "seniority_tier": seniority_tier,
        "threshold_value": threshold,
        "elevated": probability >= threshold,
    }


def batch_score(probabilities: np.ndarray, seniority_tiers: np.ndarray) -> list[dict]:
    """Score a batch of predictions."""
    return [score(float(p), int(s)) for p, s in zip(probabilities, seniority_tiers)]


def validate_threshold_drift(threshold: float, label: str) -> dict:
    """Check if a threshold is within the acceptable drift range."""
    low, high = DRIFT_ACCEPTABLE_RANGE
    in_range = low <= threshold <= high
    return {
        "threshold": threshold,
        "label": label,
        "acceptable_range": DRIFT_ACCEPTABLE_RANGE,
        "in_range": in_range,
        "action": "none" if in_range else "record cost rationale in decision log",
    }
