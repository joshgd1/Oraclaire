"""
Score an employee's burnout risk — the core inference pipeline.

Pipeline:
  1. Load model artifact from config.MODEL_ARTIFACT_PATH
  2. Accept employee assessment features as input
  3. Run model inference → raw probability
  4. Apply two-threshold routing via thresholds.py
  5. Generate SHAP decomposition (top-N features)
  6. Log prediction to audit trail via logger.log_prediction
  7. Return full result including tier, SHAP, and resources

Locked decisions: D17 (RF + SHAP), D20 (tier boundaries),
  D13 (24h employee-first gate), D8 (Critical human review).
"""

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import shap

from src.audit.logger import log_prediction
from src.config import (
    FEATURE_LABELS,
    FEATURES,
    MODEL_ARTIFACT_PATH,
    RESOURCES,
)
from src.model.thresholds import classify_tier, get_threshold, load_artifact


def load_model(path: str = MODEL_ARTIFACT_PATH) -> dict:
    if not Path(path).exists():
        raise FileNotFoundError(
            f"Model artifact not found at {path}. "
            f"Run src.model.train first."
        )
    return load_artifact(path)


def _validate_features(input_data: dict) -> pd.DataFrame:
    missing = [f for f in FEATURES if f not in input_data]
    if missing:
        raise ValueError(f"Missing required features: {missing}")
    row = {f: [input_data[f]] for f in FEATURES}
    return pd.DataFrame(row)


def _shap_explain(model, X: pd.DataFrame, n_top: int = 3) -> list[dict]:
    """Generate SHAP decomposition for one prediction.

    Returns list of {feature, impact_value, direction, label} sorted by
    absolute impact descending. Feature labels from config.FEATURE_LABELS.
    """
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    # shap API varies: list of 2D arrays, or 3D (samples, features, classes)
    if isinstance(shap_values, list):
        sv = shap_values[1]
    elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
        sv = shap_values[:, :, 1]
    else:
        sv = shap_values
    impacts = sv[0]

    ranked = sorted(
        zip(X.columns, impacts),
        key=lambda x: abs(x[1]),
        reverse=True,
    )

    result = []
    for feat, impact in ranked[:n_top]:
        label = FEATURE_LABELS.get(feat)
        if label is None:
            continue
        result.append({
            "feature": feat,
            "impact_value": round(float(impact), 4),
            "direction": "increases" if impact > 0 else "decreases",
            "label": label,
        })
    return result


def _get_resources(shap_features: list[dict]) -> list[str]:
    """Match curated resources to top SHAP feature."""
    if not shap_features:
        return []
    top_feature = shap_features[0]["feature"]
    return RESOURCES.get(top_feature, [])


def score_employee(
    employee_id: str,
    features: dict,
    seniority_tier: int,
    model_path: str = MODEL_ARTIFACT_PATH,
    log_to_audit: bool = True,
) -> dict:
    """Score one employee's burnout risk.

    Args:
        employee_id: Unique identifier for the employee.
        features: Dict with all 8 feature values (config.FEATURES).
        seniority_tier: 0 = junior (Threshold A), 1 = senior (Threshold B).
        model_path: Path to serialized model artifact.
        log_to_audit: Whether to write to predictions.jsonl audit trail.

    Returns:
        Dict with probability, risk_tier, threshold_used, shap decomposition,
        resources, and audit correlation ID.
    """
    artifact = load_model(model_path)
    model = artifact["model"]
    model_version = artifact.get("model_version", "sprint-1-rf")

    X = _validate_features(features)
    probability = float(model.predict_proba(X)[0, 1])

    threshold = get_threshold(seniority_tier)
    tier = classify_tier(probability)
    threshold_label = "B (senior)" if seniority_tier == 1 else "A (general)"

    shap_decomposition = _shap_explain(model, X)
    top_shap = shap_decomposition[0] if shap_decomposition else None
    resources = _get_resources(shap_decomposition)

    # Full SHAP values for audit trail (all features, not just top-N labeled)
    explainer = shap.TreeExplainer(model)
    all_shap_values = explainer.shap_values(X)
    if isinstance(all_shap_values, list):
        all_sv = all_shap_values[1]
    elif isinstance(all_shap_values, np.ndarray) and all_shap_values.ndim == 3:
        all_sv = all_shap_values[:, :, 1]
    else:
        all_sv = all_shap_values
    full_shap_dict = {feat: round(float(v), 4) for feat, v in zip(X.columns, all_sv[0])}

    correlation_id = None
    if log_to_audit:
        shap_values_dict = full_shap_dict
        correlation_id = log_prediction(
            employee_id=employee_id,
            burnout_probability=probability,
            risk_tier=tier,
            threshold_used=threshold_label,
            seniority_tier="senior" if seniority_tier == 1 else "junior",
            top_shap_feature=top_shap["feature"] if top_shap else "",
            top_shap_value=top_shap["impact_value"] if top_shap else 0.0,
            shap_values=shap_values_dict,
            model_version=model_version,
        )

    return {
        "employee_id": employee_id,
        "burnout_probability": round(probability, 4),
        "risk_tier": tier,
        "threshold_used": threshold_label,
        "threshold_value": threshold,
        "seniority_tier": seniority_tier,
        "elevated": probability >= threshold,
        "shap": shap_decomposition,
        "resources": resources,
        "model_version": model_version,
        "correlation_id": correlation_id,
    }
