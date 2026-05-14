"""
Prediction and pulse log schemas.

Every field that must appear in the JSONL audit trail is defined here.
Adding a field? Add it here first, then update the logger.
"""

from typing import Optional

from pydantic import BaseModel, Field


class PredictionRecord(BaseModel):
    """One row written per assessment to predictions.jsonl."""

    timestamp: str = Field(..., description="ISO 8601 UTC")
    employee_id: str
    burnout_probability: float = Field(..., ge=0.0, le=1.0)
    risk_tier: str = Field(..., description="low / moderate / high / critical")
    threshold_used: str = Field(..., description="A (general) or B (senior)")
    seniority_tier: str
    top_shap_feature: str
    top_shap_value: float
    shap_values: dict[str, float] = Field(default_factory=dict)
    model_version: str = "sprint-1-rf"
    reviewer_id: Optional[str] = None
    review_status: str = "pending"
    review_timestamp: Optional[str] = None
    review_notes: Optional[str] = None


class PulseRecord(BaseModel):
    """One row written per weekly pulse check to pulse.jsonl."""

    timestamp: str = Field(..., description="ISO 8601 UTC")
    employee_id: str
    pulse_score: float = Field(..., ge=0.0, le=10.0)
    previous_score: Optional[float] = None
    drift_points: Optional[float] = None
    drift_alert: bool = False
    consecutive_drift_weeks: int = 0
    reassessment_triggered: bool = False
