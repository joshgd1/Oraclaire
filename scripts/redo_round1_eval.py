"""
D24 RE-DO Round 1 evaluation — interaction terms.

Reports the four metrics D24 requires:
1. MFS SHAP percentage
2. RF probability for the BR=0.84 employee specifically
3. FP rate at threshold 0.30
4. FN rate at threshold 0.30
"""

import sys
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split

from src.config import (
    BINARISATION_THRESHOLD,
    BRIER_FLOOR,
    FEATURES,
    MODEL_PARAMS,
    THRESHOLD_A,
)
from src.model.train import engineer_features, load_data, prepare_features, train, shap_audit


def main():
    raw_path = "data/raw/train.csv"
    df = load_data(raw_path)
    df = engineer_features(df)
    X, y = prepare_features(df)

    print(f"Dataset: {len(df)} rows, {X.shape[1]} features")
    print(f"Features: {FEATURES}")
    print(f"Label balance: {y.mean():.1%} elevated")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=MODEL_PARAMS["random_state"],
    )

    model = train(X_train, y_train)
    y_prob = model.predict_proba(X_test)[:, 1]

    # Reset indices
    X_test_r = X_test.reset_index(drop=True)
    y_test_r = y_test.reset_index(drop=True)

    # ── Metric 1: MFS SHAP ──────────────────────────────────────────────
    shap_result = shap_audit(model, X_test_r)
    print(f"\n{'='*60}")
    print(f"METRIC 1 — MFS SHAP: {shap_result['mfs_shap_pct']}% (gate: 40%)")
    print(f"  {'PASS' if shap_result['mfs_gate'] else 'FAIL'}")
    print(f"  SHAP profile:")
    for feat, pct in shap_result["shap_profile"].items():
        print(f"    {feat}: {pct}%")

    # ── Metric 2: BR=0.84 employee probability ──────────────────────────
    # Find the original test indices
    test_indices = X_test.index
    test_df = df.loc[test_indices]

    # Find employees with Burn Rate near 0.84
    high_br_mask = test_df["Burn Rate"] >= 0.80
    high_br_indices = test_df.index[high_br_mask]

    print(f"\n{'='*60}")
    print(f"METRIC 2 — High Burn Rate employees (BR >= 0.80):")
    print(f"  Total in test set: {high_br_mask.sum()}")

    # Get probabilities for all high-BR employees
    high_br_probs = y_prob[high_br_mask.values]
    print(f"  RF probability range: [{high_br_probs.min():.4f}, {high_br_probs.max():.4f}]")
    print(f"  RF probability mean: {high_br_probs.mean():.4f}")

    # Specifically the BR=0.84 employee
    br_084_mask = (test_df["Burn Rate"] >= 0.83) & (test_df["Burn Rate"] <= 0.85)
    if br_084_mask.sum() > 0:
        br_084_probs = y_prob[br_084_mask.values]
        print(f"\n  Employees with BR ~0.84 (0.83-0.85 range):")
        for i, (idx, row) in enumerate(test_df[br_084_mask].iterrows()):
            prob = br_084_probs[i]
            prob_idx = list(high_br_mask[high_br_mask].index).index(idx) if idx in high_br_mask[high_br_mask].index else -1
            print(f"    Index {idx}: Burn Rate={row['Burn Rate']:.4f}, RF prob={prob:.4f}")

    # How many high-BR employees are below threshold 0.30?
    below_threshold = (high_br_probs < THRESHOLD_A).sum()
    print(f"\n  High-BR employees below threshold {THRESHOLD_A}: {below_threshold}/{high_br_mask.sum()}")

    # ── Metric 3 & 4: FP and FN at threshold 0.30 ──────────────────────
    gen_mask = (X_test_r["seniority_tier"] == 0).values
    y_pred = (y_prob >= THRESHOLD_A).astype(int)

    # General population
    y_gen = y_test_r[gen_mask]
    p_gen = y_prob[gen_mask]
    pred_gen = y_pred[gen_mask]
    tn, fp, fn, tp = confusion_matrix(y_gen, pred_gen, labels=[0, 1]).ravel()
    fp_rate = fp / (fp + tn) if (fp + tn) > 0 else 0
    fn_rate = fn / (fn + tp) if (fn + tp) > 0 else 0

    print(f"\n{'='*60}")
    print(f"METRIC 3 — FP rate at {THRESHOLD_A} (general pop): {fp_rate:.4f} ({fp}/{fp+tn})")
    print(f"  {'PASS' if fp_rate <= 0.15 else 'FAIL'} (ceiling 15%)")

    print(f"\nMETRIC 4 — FN rate at {THRESHOLD_A} (general pop): {fn_rate:.4f} ({fn}/{fn+tp})")
    print(f"  {'PASS' if fn_rate <= 0.15 else 'FAIL'} (target 15%)")

    # Overall metrics
    brier = brier_score_loss(y_test_r, y_prob)
    auc = roc_auc_score(y_test_r, y_prob)
    print(f"\n{'='*60}")
    print(f"Brier: {brier:.4f} (ceiling {BRIER_FLOOR}) {'PASS' if brier <= BRIER_FLOOR else 'FAIL'}")
    print(f"AUC:   {auc:.3f}")

    # Threshold sensitivity
    print(f"\nThreshold sensitivity (general, {gen_mask.sum()} employees):")
    for t in [0.30, 0.35, 0.40, 0.45]:
        pred_t = (p_gen >= t).astype(int)
        tn_t, fp_t, fn_t, tp_t = confusion_matrix(y_gen, pred_t, labels=[0, 1]).ravel()
        fp_r = fp_t / (fp_t + tn_t) if (fp_t + tn_t) > 0 else 0
        fn_r = fn_t / (fn_t + tp_t) if (fn_t + tp_t) > 0 else 0
        print(f"  {t:.2f}: FP={fp_r:.3f}, FN={fn_r:.3f}")

    return 0 if shap_result["mfs_gate"] else 1


if __name__ == "__main__":
    sys.exit(main())
