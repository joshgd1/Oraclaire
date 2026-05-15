"""
Integration test — Sprint 1 end-to-end pipeline.

Validates: train -> serve -> threshold -> audit trail
against the 12-row clean dataset.
"""

import json
from pathlib import Path

import joblib
import pytest

from src.config import (
    CLEAN_DATA_PATH,
    FEATURES,
    MODEL_ARTIFACT_PATH,
    PREDICTIONS_LOG,
    THRESHOLD_A,
    THRESHOLD_B,
    TIER_BOUNDARIES,
)


@pytest.fixture(autouse=True)
def _use_test_artifact(tmp_path, monkeypatch):
    """Redirect model and audit paths to temp directory."""
    artifact = tmp_path / "rf_model.joblib"
    monkeypatch.setattr("src.config.MODEL_ARTIFACT_PATH", str(artifact))
    monkeypatch.setattr("src.model.train.MODEL_ARTIFACT_PATH", str(artifact))
    monkeypatch.setattr("src.model.serve.MODEL_ARTIFACT_PATH", str(artifact))
    monkeypatch.setattr("src.model.thresholds.MODEL_ARTIFACT_PATH", str(artifact))

    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    predictions_log = audit_dir / "predictions.jsonl"
    monkeypatch.setattr("src.config.PREDICTIONS_LOG", str(predictions_log))
    monkeypatch.setattr("src.audit.logger.PREDICTIONS_LOG", str(predictions_log))

    data_dir = tmp_path / "processed"
    data_dir.mkdir()
    monkeypatch.setattr(
        "src.config.UNLABELLED_POOL_PATH",
        str(data_dir / "unlabelled_pool.csv"),
    )
    monkeypatch.setattr(
        "src.model.train.UNLABELLED_POOL_PATH",
        str(data_dir / "unlabelled_pool.csv"),
    )

    yield artifact


class TestTrainingPipeline:
    def test_train_produces_artifact(self, _use_test_artifact):
        from src.model.train import run

        result = run(data_path=CLEAN_DATA_PATH)

        assert _use_test_artifact.exists(), "Model artifact not created"
        assert "auc" in result
        assert "pr_auc" in result
        assert "brier" in result
        assert result["auc"] > 0.5, f"AUC too low: {result['auc']}"
        assert result["shap"]["mfs_gate"], "MFS SHAP dominance gate failed"

    def test_artifact_contains_required_fields(self, _use_test_artifact):
        from src.model.train import run

        run(data_path=CLEAN_DATA_PATH)
        artifact = joblib.load(str(_use_test_artifact))

        assert "model" in artifact
        assert "features" in artifact
        assert "metrics" in artifact
        assert "shap" in artifact
        assert "model_version" in artifact
        assert artifact["features"] == FEATURES


class TestScoringPipeline:
    @pytest.fixture(autouse=True)
    def _train_model(self, _use_test_artifact):
        from src.model.train import run

        run(data_path=CLEAN_DATA_PATH)

    def test_score_employee_junior(self, _use_test_artifact):
        from src.model.serve import score_employee

        features = {
            "company_type": 1,
            "wfh_setup": 0,
            "resource_allocation": 6.0,
            "mental_fatigue_score": 7.0,
            "missing_ra": 0,
            "missing_mfs": 0,
            "seniority_tier": 0,
            "tenure_days": 500,
            "tenure_fatigue": 3500.0,
            "tenure_workload": 3000.0,
        }

        result = score_employee("TEST_001", features, seniority_tier=0)

        assert result["employee_id"] == "TEST_001"
        assert 0.0 <= result["burnout_probability"] <= 1.0
        assert result["risk_tier"] in TIER_BOUNDARIES
        assert result["threshold_used"] == "A (general)"
        assert result["threshold_value"] == THRESHOLD_A
        assert isinstance(result["shap"], list)
        assert result["model_version"] == "sprint-1-rf"

    def test_score_employee_senior_uses_threshold_b(self, _use_test_artifact):
        from src.model.serve import score_employee

        features = {
            "company_type": 1,
            "wfh_setup": 1,
            "resource_allocation": 4.0,
            "mental_fatigue_score": 3.0,
            "missing_ra": 0,
            "missing_mfs": 0,
            "seniority_tier": 1,
            "tenure_days": 1500,
            "tenure_fatigue": 4500.0,
            "tenure_workload": 6000.0,
        }

        result = score_employee("TEST_002", features, seniority_tier=1)

        assert result["threshold_used"] == "B (senior)"
        assert result["threshold_value"] == THRESHOLD_B

    def test_audit_trail_written(self, _use_test_artifact, tmp_path):
        from src.model.serve import score_employee

        features = {
            "company_type": 0,
            "wfh_setup": 1,
            "resource_allocation": 5.0,
            "mental_fatigue_score": 4.0,
            "missing_ra": 0,
            "missing_mfs": 0,
            "seniority_tier": 0,
            "tenure_days": 300,
            "tenure_fatigue": 1200.0,
            "tenure_workload": 1500.0,
        }

        result = score_employee("TEST_003", features, seniority_tier=0)
        assert result["correlation_id"] is not None

        predictions_log = tmp_path / "audit" / "predictions.jsonl"
        assert predictions_log.exists(), "Audit log not created"

        lines = predictions_log.read_text().strip().split("\n")
        assert len(lines) >= 1

        entry = json.loads(lines[-1])
        assert entry["employee_id"] == "TEST_003"
        assert entry["risk_tier"] in TIER_BOUNDARIES
        assert "model_version" in entry


class TestThresholdRouting:
    def test_tier_boundaries(self):
        from src.model.thresholds import classify_tier

        assert classify_tier(0.0) == "low"
        assert classify_tier(0.10) == "low"
        assert classify_tier(0.19) == "low"
        assert classify_tier(0.20) == "moderate"
        assert classify_tier(0.25) == "moderate"
        assert classify_tier(0.29) == "moderate"
        assert classify_tier(0.30) == "high"
        assert classify_tier(0.50) == "high"
        assert classify_tier(0.89) == "high"
        assert classify_tier(0.90) == "critical"
        assert classify_tier(1.0) == "critical"

    def test_threshold_routing(self):
        from src.model.thresholds import get_threshold

        assert get_threshold(0) == THRESHOLD_A
        assert get_threshold(1) == THRESHOLD_B
