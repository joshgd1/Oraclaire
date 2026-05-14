"""
Full Kaggle dataset re-run — Sprint 1 floor-check validation.

Runs the training pipeline on the full 22,750-row Kaggle dataset
and validates all D18 floor checks plus D21 Critical tier validation.

Floor checks (D18):
  1. Brier score ≤ 0.15 (BRIER_FLOOR)
  2. MFS SHAP < 40% (D16 gate)
  3. Threshold A FP ceiling ≤ 15% (general population)
  4. Threshold A FN target ≤ 15% (general population)
  5. Threshold B FP ceiling ≤ 20% (senior tier)
  6. Threshold B FN target ≤ 10% (senior tier)

Additional checks:
  7. Threshold drift within (0.25, 0.35) — DRIFT_ACCEPTABLE_RANGE
  8. Critical tier produces real probabilities (D21)
  9. FP rate at threshold 0.30
"""

import sys
import numpy as np
from sklearn.metrics import confusion_matrix, brier_score_loss
from sklearn.model_selection import train_test_split

from src.config import (
    BINARISATION_THRESHOLD,
    BRIER_FLOOR,
    CLEAN_DATA_PATH,
    DRIFT_ACCEPTABLE_RANGE,
    FEATURES,
    MODEL_PARAMS,
    SENIORITY_DESIGNATION_CUTOFF,
    THRESHOLD_A,
    THRESHOLD_A_FP_CEILING,
    THRESHOLD_A_FN_TARGET,
    THRESHOLD_B,
    THRESHOLD_B_FP_CEILING,
    THRESHOLD_B_FN_TARGET,
    TIER_BOUNDARIES,
)
from src.model.train import engineer_features, load_data, prepare_features, train, shap_audit


def compute_fp_fn_rates(y_true, y_prob, threshold, seniority_mask=None):
    """Compute FP and FN rates at a given threshold, optionally for a subset."""
    if seniority_mask is not None:
        y_true = y_true[seniority_mask]
        y_prob = y_prob[seniority_mask]

    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    fp_rate = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fn_rate = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    return fp_rate, fn_rate, tn, fp, fn, tp


def classify_tier(prob):
    for tier_name in ["low", "moderate", "high", "critical"]:
        low, high = TIER_BOUNDARIES[tier_name]
        if low <= prob < high:
            return tier_name
    if prob >= TIER_BOUNDARIES["critical"][0]:
        return "critical"
    return "low"


def main():
    raw_path = "data/raw/train.csv"
    print(f"Loading full dataset from {raw_path}...")

    df = load_data(raw_path)
    df = engineer_features(df)
    X, y = prepare_features(df)

    print(f"\nDataset: {len(df)} labelled rows, {X.shape[1]} features")
    print(f"Label distribution: {y.value_counts().to_dict()}")
    print(f"Class balance: {y.mean():.1%} elevated (≥{BINARISATION_THRESHOLD})")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=MODEL_PARAMS["random_state"],
    )

    print(f"\nTrain: {len(X_train)}, Test: {len(X_test)}")

    model = train(X_train, y_train)
    y_prob = model.predict_proba(X_test)[:, 1]

    # Reset indices for seniority_mask alignment
    X_test_reset = X_test.reset_index(drop=True)
    y_test_reset = y_test.reset_index(drop=True)
    y_prob_series = pd.Series(y_prob)

    seniority_mask = (X_test_reset["seniority_tier"] == 1).values

    # ── Floor 1: Brier score ────────────────────────────────────────────────
    brier = brier_score_loss(y_test_reset, y_prob)
    brier_pass = brier <= BRIER_FLOOR
    print(f"\n{'='*60}")
    print(f"FLOOR 1 — Brier score: {brier:.4f} (ceiling {BRIER_FLOOR})")
    print(f"  {'PASS' if brier_pass else 'FAIL'}")

    # ── Floor 2: MFS SHAP ──────────────────────────────────────────────────
    shap_result = shap_audit(model, X_test_reset)
    mfs_pass = shap_result["mfs_gate"]
    print(f"\nFLOOR 2 — MFS SHAP: {shap_result['mfs_shap_pct']}% (ceiling 40%)")
    print(f"  {'PASS' if mfs_pass else 'FAIL'}")
    print(f"  Top 5 SHAP features:")
    for feat, pct in list(shap_result["shap_profile"].items())[:5]:
        print(f"    {feat}: {pct}%")

    # ── Floor 3-4: Threshold A (general) FP/FN ────────────────────────────
    gen_mask = ~seniority_mask
    fp_a, fn_a, tn_a, fp_a_count, fn_a_count, tp_a_count = compute_fp_fn_rates(
        y_test_reset.values, y_prob, THRESHOLD_A, gen_mask
    )
    fp_a_pass = fp_a <= THRESHOLD_A_FP_CEILING
    fn_a_pass = fn_a <= THRESHOLD_A_FN_TARGET
    gen_total = gen_mask.sum()
    print(f"\nFLOOR 3 — Threshold A FP rate: {fp_a:.4f} ({fp_a_count}/{tn_a + fp_a_count}) "
          f"[ceiling {THRESHOLD_A_FP_CEILING}] on {gen_total} general employees")
    print(f"  {'PASS' if fp_a_pass else 'FAIL'}")

    print(f"\nFLOOR 4 — Threshold A FN rate: {fn_a:.4f} ({fn_a_count}/{fn_a_count + tp_a_count}) "
          f"[target {THRESHOLD_A_FN_TARGET}] on {gen_total} general employees")
    print(f"  {'PASS' if fn_a_pass else 'FAIL'}")

    # ── Floor 5-6: Threshold B (senior) FP/FN ─────────────────────────────
    sen_total = seniority_mask.sum()
    if sen_total > 0:
        fp_b, fn_b, tn_b, fp_b_count, fn_b_count, tp_b_count = compute_fp_fn_rates(
            y_test_reset.values, y_prob, THRESHOLD_B, seniority_mask
        )
        fp_b_pass = fp_b <= THRESHOLD_B_FP_CEILING
        fn_b_pass = fn_b <= THRESHOLD_B_FN_TARGET
        print(f"\nFLOOR 5 — Threshold B FP rate: {fp_b:.4f} ({fp_b_count}/{tn_b + fp_b_count}) "
              f"[ceiling {THRESHOLD_B_FP_CEILING}] on {sen_total} senior employees")
        print(f"  {'PASS' if fp_b_pass else 'FAIL'}")

        print(f"\nFLOOR 6 — Threshold B FN rate: {fn_b:.4f} ({fn_b_count}/{fn_b_count + tp_b_count}) "
              f"[target {THRESHOLD_B_FN_TARGET}] on {sen_total} senior employees")
        print(f"  {'PASS' if fn_b_pass else 'FAIL'}")
    else:
        print(f"\nFLOORS 5-6 — No senior employees in test set ({sen_total})")

    # ── Floor 7: Threshold drift ────────────────────────────────────────────
    drift_low, drift_high = DRIFT_ACCEPTABLE_RANGE
    drift_a = drift_low <= THRESHOLD_A <= drift_high
    drift_b = drift_low <= THRESHOLD_B <= drift_high
    print(f"\nCHECK 7 — Threshold drift:")
    print(f"  Threshold A ({THRESHOLD_A}): {'PASS' if drift_a else 'FAIL'} [{drift_low}, {drift_high}]")
    print(f"  Threshold B ({THRESHOLD_B}): {'PASS' if drift_b else 'FAIL'} [{drift_low}, {drift_high}]")

    # ── Check 8: Critical tier validation (D21) ────────────────────────────
    tier_counts = {}
    critical_probs = []
    for p in y_prob:
        tier = classify_tier(float(p))
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        if tier == "critical":
            critical_probs.append(float(p))

    total_scored = len(y_prob)
    critical_pct = tier_counts.get("critical", 0) / total_scored * 100

    print(f"\nCHECK 8 — Critical tier validation (D21):")
    print(f"  Tier distribution on test set ({total_scored} employees):")
    for t in ["low", "moderate", "high", "critical"]:
        cnt = tier_counts.get(t, 0)
        pct = cnt / total_scored * 100
        print(f"    {t}: {cnt} ({pct:.1f}%)")

    if critical_probs:
        print(f"  Critical probabilities: min={min(critical_probs):.4f}, "
              f"max={max(critical_probs):.4f}, mean={np.mean(critical_probs):.4f}")
        print(f"  Critical ≤ 5% of scorable: {'PASS' if critical_pct <= 5.0 else 'FAIL'} "
              f"({critical_pct:.1f}%)")
    else:
        print(f"  No Critical-tier employees in test set")

    # ── Check 9: Overall FP rate at threshold 0.30 ─────────────────────────
    fp_all, fn_all, _, _, _, _ = compute_fp_fn_rates(
        y_test_reset.values, y_prob, THRESHOLD_A
    )
    print(f"\nCHECK 9 — Overall FP rate at {THRESHOLD_A}: {fp_all:.4f}")

    # ── Summary ─────────────────────────────────────────────────────────────
    all_floors = [brier_pass, mfs_pass, fp_a_pass, fn_a_pass]
    if sen_total > 0:
        all_floors.extend([fp_b_pass, fn_b_pass])

    print(f"\n{'='*60}")
    print(f"SUMMARY — {'ALL FLOORS PASS' if all(all_floors) else 'SOME FLOORS FAIL'}")
    print(f"  Brier:       {brier:.4f} {'PASS' if brier_pass else 'FAIL'}")
    print(f"  MFS SHAP:    {shap_result['mfs_shap_pct']}% {'PASS' if mfs_pass else 'FAIL'}")
    print(f"  FP-A:        {fp_a:.4f} {'PASS' if fp_a_pass else 'FAIL'}")
    print(f"  FN-A:        {fn_a:.4f} {'PASS' if fn_a_pass else 'FAIL'}")
    if sen_total > 0:
        print(f"  FP-B:        {fp_b:.4f} {'PASS' if fp_b_pass else 'FAIL'}")
        print(f"  FN-B:        {fn_b:.4f} {'PASS' if fn_b_pass else 'FAIL'}")

    return 0 if all(all_floors) else 1


if __name__ == "__main__":
    import pandas as pd  # noqa: E402 — needed for Series in main
    sys.exit(main())
