"""
Train the Sprint 1 Random Forest burnout risk model.

Pipeline:
  1. Load data from config.CLEAN_DATA_PATH (or data/raw/train.csv for full run)
  2. Drop unlabelled rows (Burn Rate null)
  3. Feature engineering: tenure_days, seniority_tier, missing indicators
  4. Median imputation for Resource Allocation and Mental Fatigue Score
  5. Binarise label at config.BINARISATION_THRESHOLD
  6. Stratified 80/20 split
  7. Train RandomForestClassifier with config.MODEL_PARAMS
  8. Evaluate: AUC, PR-AUC, Brier
  9. SHAP TreeExplainer — MFS below 40% check (D16 gate)
  10. Serialize to config.MODEL_ARTIFACT_PATH

Decisions locked: D16 (XGBoost disqualified), D17 (RF confirmed),
  D18 (floor checks), D20 (tier boundaries).
"""

from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split

from src.config import (
    BINARISATION_THRESHOLD,
    CLEAN_DATA_PATH,
    FEATURES,
    MODEL_ARTIFACT_PATH,
    MODEL_PARAMS,
    SENIORITY_DESIGNATION_CUTOFF,
    UNLABELLED_POOL_PATH,
)

REFERENCE_DATE = datetime(2026, 1, 1)


def load_data(path: str = CLEAN_DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    before = len(df)
    unlabelled = df[df["Burn Rate"].isnull()]
    df = df.dropna(subset=["Burn Rate"])
    dropped = before - len(df)
    if dropped > 0:
        print(f"Saved {dropped} unlabelled rows to {UNLABELLED_POOL_PATH}")
        Path(UNLABELLED_POOL_PATH).parent.mkdir(parents=True, exist_ok=True)
        unlabelled.to_csv(UNLABELLED_POOL_PATH, index=False)
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Missing indicators before imputation
    df["missing_ra"] = df["Resource Allocation"].isnull().astype(int)
    df["missing_mfs"] = df["Mental Fatigue Score"].isnull().astype(int)

    # Median imputation + rename to snake_case
    ra_median = df["Resource Allocation"].median()
    mfs_median = df["Mental Fatigue Score"].median()
    df["Resource Allocation"] = df["Resource Allocation"].fillna(ra_median)
    df["Mental Fatigue Score"] = df["Mental Fatigue Score"].fillna(mfs_median)
    df = df.rename(columns={
        "Resource Allocation": "resource_allocation",
        "Mental Fatigue Score": "mental_fatigue_score",
    })

    # tenure_days from Date of Joining
    df["Date of Joining"] = pd.to_datetime(df["Date of Joining"])
    df["tenure_days"] = (REFERENCE_DATE - df["Date of Joining"]).dt.days

    # seniority_tier from Designation — handle both string and numeric formats.
    # Raw Kaggle data uses numeric (0-5), clean data uses string labels.
    designation_order = {
        "Analyst": 1, "Associate": 2, "Senior Analyst": 3,
        "Lead": 4, "Manager": 5,
    }
    if pd.api.types.is_numeric_dtype(df["Designation"]):
        df["_designation_level"] = df["Designation"].fillna(0)
    else:
        df["_designation_level"] = df["Designation"].map(designation_order).fillna(0)
    df["seniority_tier"] = (df["_designation_level"] >= SENIORITY_DESIGNATION_CUTOFF).astype(int)
    df = df.drop(columns=["_designation_level"])

    # Interaction terms (D24 RE-DO Round 1) — dilute MFS SHAP dominance
    df["tenure_fatigue"] = df["tenure_days"] * df["mental_fatigue_score"]
    df["tenure_workload"] = df["tenure_days"] * df["resource_allocation"]

    # Binary encoding
    df["company_type"] = (df["Company Type"] == "Product").astype(int)
    df["wfh_setup"] = (df["WFH Setup Available"] == "Yes").astype(int)

    return df


def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    X = df[FEATURES].copy()
    y = (df["Burn Rate"] >= BINARISATION_THRESHOLD).astype(int)
    return X, y


def train(X_train: np.ndarray, y_train: np.ndarray) -> RandomForestClassifier:
    model = RandomForestClassifier(**MODEL_PARAMS)
    model.fit(X_train, y_train)
    return model


def evaluate(model: RandomForestClassifier, X_test: np.ndarray, y_test: np.ndarray) -> dict:
    y_prob = model.predict_proba(X_test)[:, 1]
    return {
        "auc": roc_auc_score(y_test, y_prob),
        "pr_auc": average_precision_score(y_test, y_prob),
        "brier": brier_score_loss(y_test, y_prob),
    }


def shap_audit(model: RandomForestClassifier, X: pd.DataFrame) -> dict:
    """SHAP importance check — MFS must be below 40% (D16 gate)."""
    import shap

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    # shap API varies: list of 2D arrays, or 3D (samples, features, classes)
    if isinstance(shap_values, list):
        sv = shap_values[1]  # class 1 for binary
    elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
        sv = shap_values[:, :, 1]  # (samples, features) for class 1
    else:
        sv = shap_values
    mean_abs = np.abs(sv).mean(axis=0)
    total = mean_abs.sum()
    if total == 0:
        return {"mfs_shap_pct": 0.0, "shap_profile": {}, "mfs_gate": True}
    pct = {feat: float(v / total * 100) for feat, v in zip(X.columns, mean_abs)}
    mfs_pct = pct.get("mental_fatigue_score", 0.0)
    return {
        "mfs_shap_pct": round(mfs_pct, 1),
        "shap_profile": {k: round(v, 1) for k, v in sorted(pct.items(), key=lambda x: -x[1])},
        "mfs_gate": mfs_pct < 40.0,
    }


def save_model(model: RandomForestClassifier, metrics: dict, shap_result: dict, path: str = MODEL_ARTIFACT_PATH) -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "model": model,
        "features": FEATURES,
        "metrics": metrics,
        "shap": shap_result,
        "model_version": "sprint-1-rf",
    }
    joblib.dump(artifact, path)
    return path


def run(data_path: str = CLEAN_DATA_PATH) -> dict:
    """Full training pipeline. Returns metrics dict."""
    df = load_data(data_path)
    df = engineer_features(df)
    X, y = prepare_features(df)

    print(f"Dataset: {len(df)} rows, {X.shape[1]} features")
    print(f"Label distribution: {y.value_counts().to_dict()}")
    print(f"Class balance: {y.mean():.1%} elevated")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=MODEL_PARAMS["random_state"],
    )

    model = train(X_train, y_train)
    metrics = evaluate(model, X_test, y_test)

    print(f"AUC:    {metrics['auc']:.3f}")
    print(f"PR-AUC: {metrics['pr_auc']:.3f}")
    print(f"Brier:  {metrics['brier']:.4f}")

    shap_result = shap_audit(model, X_test)
    print(f"MFS SHAP: {shap_result['mfs_shap_pct']}% — {'PASS' if shap_result['mfs_gate'] else 'FAIL (>=40%)'}")
    for feat, pct in list(shap_result["shap_profile"].items())[:5]:
        print(f"  {feat}: {pct}%")

    if not shap_result["mfs_gate"]:
        raise RuntimeError(
            f"MFS SHAP dominance: {shap_result['mfs_shap_pct']}%. "
            f"Exceeds 40% threshold. Model not serialised. "
            f"Expand feature set before retraining. See D16."
        )

    path = save_model(model, metrics, shap_result, MODEL_ARTIFACT_PATH)
    print(f"Model saved to {path}")

    return {**metrics, "shap": shap_result, "dataset_size": len(df), "artifact_path": path}


if __name__ == "__main__":
    run()
