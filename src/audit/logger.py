"""
JSONL append-only writers for prediction and pulse audit trails.

Each writer appends one JSON line per event. No reads, no updates,
no deletes — the audit trail is immutable by design.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.audit.schema import PredictionRecord, PulseRecord
from src.config import (
    PREDICTIONS_LOG,
    PULSE_DRIFT_CONSECUTIVE_WEEKS,
    PULSE_DRIFT_THRESHOLD,
    PULSE_LOG,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append(path: str, data: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    # SPRINT 1: Single-user Streamlit — concurrent writes not expected.
    # SPRINT 2: Add file locking before multi-user deployment.
    # One-line fix when needed:
    #   import fcntl
    #   fcntl.flock(f, fcntl.LOCK_EX)
    #   after the file is opened,
    #   fcntl.flock(f, fcntl.LOCK_UN)
    #   before the context manager exits.
    # Without locking, concurrent writes to predictions.jsonl or pulse.jsonl
    # can produce corrupt JSONL lines that silently break the audit trail.
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def _read_prior_pulses(employee_id: str) -> list[dict]:
    path = Path(PULSE_LOG)
    if not path.exists():
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("employee_id") == employee_id:
                entries.append(record)
    entries.sort(key=lambda r: r["timestamp"], reverse=True)
    return entries


def log_prediction(
    employee_id: str,
    burnout_probability: float,
    risk_tier: str,
    threshold_used: str,
    seniority_tier: str,
    top_shap_feature: str,
    top_shap_value: float,
    shap_values: dict[str, float],
    model_version: str = "sprint-1-rf",
) -> str:
    """Write one prediction record. Returns the timestamp as correlation ID."""
    ts = _utc_now()
    record = PredictionRecord(
        timestamp=ts,
        employee_id=employee_id,
        burnout_probability=burnout_probability,
        risk_tier=risk_tier,
        threshold_used=threshold_used,
        seniority_tier=seniority_tier,
        top_shap_feature=top_shap_feature,
        top_shap_value=top_shap_value,
        shap_values=shap_values,
        model_version=model_version,
    )
    _append(PREDICTIONS_LOG, record.model_dump(mode="json"))
    return ts


def log_pulse(
    employee_id: str,
    pulse_score: float,
    drift_points: Optional[float] = None,
    drift_alert: bool = False,
) -> str:
    """Write one pulse record. Returns the timestamp as correlation ID.

    Drift detection (D13 Mechanism A) is computed here from prior pulse
    history — not passed in by the caller. If the caller computed it,
    the burnout detection logic would live in the view layer.
    """
    prior = _read_prior_pulses(employee_id)

    # Count consecutive qualifying drops ending at current score.
    # All scores newest-first: [current, most_recent_prior, ..., oldest]
    all_scores = [pulse_score] + [p["pulse_score"] for p in prior]
    consecutive = 0
    for i in range(len(all_scores) - 1):
        drop = all_scores[i + 1] - all_scores[i]  # older - newer = positive when dropping
        if drop >= PULSE_DRIFT_THRESHOLD:
            consecutive += 1
        else:
            break

    reassessment_triggered = consecutive >= PULSE_DRIFT_CONSECUTIVE_WEEKS

    ts = _utc_now()
    record = PulseRecord(
        timestamp=ts,
        employee_id=employee_id,
        pulse_score=pulse_score,
        previous_score=prior[0]["pulse_score"] if prior else None,
        drift_points=drift_points,
        drift_alert=drift_alert,
        consecutive_drift_weeks=consecutive,
        reassessment_triggered=reassessment_triggered,
    )
    _append(PULSE_LOG, record.model_dump(mode="json"))
    return ts
