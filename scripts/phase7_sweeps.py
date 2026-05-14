"""
Phase 7 Red-Team — All four sweeps on the corrected 10-feature model.

Runs on data/processed/train_clean.csv (12 rows).
Sweep 1: Model stability across 3 random seeds (LOOCV)
Sweep 2: Feature ablation (top 3 features from Phase 4)
Sweep 3: Proxy leakage (Gender addition, Designation removal)
Sweep 4: Calibration per risk tier (LOOCV Brier by tier)
"""

import json
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.model_selection import LeaveOneOut

from src.config import (
    BINARISATION_THRESHOLD,
    BRIER_FLOOR,
    CLEAN_DATA_PATH,
    FEATURES,
    MODEL_PARAMS,
    THRESHOLD_A,
    THRESHOLD_B,
    TIER_BOUNDARIES,
    TIER_ORDER,
)
from src.model.train import engineer_features, load_data, prepare_features

# Current feature set: 10 features (post-D24 RE-DO with interaction terms)
# Phase 6 pre-registration referenced 8 features; RE-DO added tenure_fatigue + tenure_workload


def classify_tier(prob):
    for tier_name in TIER_ORDER:
        low, high = TIER_BOUNDARIES[tier_name]
        if low <= prob < high:
            return tier_name
    if prob >= TIER_BOUNDARIES["critical"][0]:
        return "critical"
    return "low"


def loocv(df, features, seed, extra_features=None):
    """Run LOOCV on the 12-row dataset. Returns per-employee predictions."""
    all_features = list(features)
    if extra_features:
        all_features.extend(extra_features)

    X = df[all_features].copy()
    y = (df["Burn Rate"] >= BINARISATION_THRESHOLD).astype(int)
    employee_ids = df["Employee ID"].values

    loo = LeaveOneOut()
    probs = np.zeros(len(df))

    for train_idx, test_idx in loo.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train = y.iloc[train_idx]

        model = RandomForestClassifier(
            n_estimators=MODEL_PARAMS["n_estimators"],
            max_depth=MODEL_PARAMS["max_depth"],
            random_state=seed,
        )
        model.fit(X_train, y_train)
        probs[test_idx[0]] = model.predict_proba(X_test)[0, 1]

    return employee_ids, probs, y.values


def shap_on_full(df, features, seed, extra_features=None):
    """Compute SHAP on model trained on all 12 rows."""
    import shap

    all_features = list(features)
    if extra_features:
        all_features.extend(extra_features)

    X = df[all_features].copy()
    y = (df["Burn Rate"] >= BINARISATION_THRESHOLD).astype(int)

    model = RandomForestClassifier(
        n_estimators=MODEL_PARAMS["n_estimators"],
        max_depth=MODEL_PARAMS["max_depth"],
        random_state=seed,
    )
    model.fit(X, y)

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    if isinstance(shap_values, list):
        sv = shap_values[1]
    elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
        sv = shap_values[:, :, 1]
    else:
        sv = shap_values

    mean_abs = np.abs(sv).mean(axis=0)
    total = mean_abs.sum()
    if total == 0:
        return {}
    pct = {feat: float(v / total * 100) for feat, v in zip(X.columns, mean_abs)}
    return {k: round(v, 1) for k, v in sorted(pct.items(), key=lambda x: -x[1])}


# ── Load data ───────────────────────────────────────────────────────────
df = load_data(CLEAN_DATA_PATH)
df = engineer_features(df)
print(f"Dataset: {len(df)} rows, features available: {df.columns.tolist()}")
print(f"Feature set: {FEATURES} ({len(FEATURES)} features)")
print(f"Binarisation threshold: {BINARISATION_THRESHOLD}")
print()

# ═══════════════════════════════════════════════════════════════════════
# SWEEP 1 — MODEL STABILITY (RE-SEED)
# ═══════════════════════════════════════════════════════════════════════
print("=" * 70)
print("SWEEP 1 — MODEL STABILITY (RE-SEED)")
print("=" * 70)

seeds = [42, 123, 456]
all_results = {}
all_tiers = {}

for seed in seeds:
    eids, probs, y_true = loocv(df, FEATURES, seed)
    auc = roc_auc_score(y_true, probs)
    brier = brier_score_loss(y_true, probs)
    shap_profile = shap_on_full(df, FEATURES, seed)

    mfs_pct = shap_profile.get("mental_fatigue_score", 0.0)
    tiers = [classify_tier(p) for p in probs]

    all_results[seed] = {
        "auc": round(auc, 4),
        "brier": round(brier, 4),
        "mfs_shap": mfs_pct,
    }
    all_tiers[seed] = {eid: tier for eid, tier in zip(eids, tiers)}

    print(f"\nSeed {seed}:")
    print(f"  AUC:   {auc:.4f}")
    print(f"  Brier: {brier:.4f}")
    print(f"  MFS SHAP: {mfs_pct}%")
    print(f"  SHAP profile: {list(shap_profile.items())[:5]}")
    print(f"  Tier distribution: {pd.Series(tiers).value_counts().to_dict()}")

# Per-employee tier stability
print(f"\n{'='*70}")
print("PER-EMPLOYEE TIER STABILITY:")
employee_ids = list(all_tiers[42].keys())
stable_count = 0
unstable_employees = []
for eid in employee_ids:
    tiers_across_seeds = [all_tiers[s][eid] for s in seeds]
    unique_tiers = set(tiers_across_seeds)
    is_stable = len(unique_tiers) == 1
    if is_stable:
        stable_count += 1
    else:
        unstable_employees.append({
            "employee_id": eid,
            "tiers": tiers_across_seeds,
            "burn_rate": float(df[df["Employee ID"] == eid]["Burn Rate"].values[0]),
        })
        print(f"  UNSTABLE: {eid} — tiers across seeds: {tiers_across_seeds} (Burn Rate: {unstable_employees[-1]['burn_rate']:.2f})")

print(f"\n  Stable: {stable_count}/12 employees ({stable_count/12*100:.0f}%)")
print(f"  Unstable: {len(unstable_employees)}/12 employees ({len(unstable_employees)/12*100:.0f}%)")

# Check for FN-costly instability (burned-out employee moves to lower tier)
print(f"\n  FN-risk instability (elevated employee moving to lower tier):")
fn_risk_count = 0
for ue in unstable_employees:
    br = ue["burn_rate"]
    if br >= BINARISATION_THRESHOLD:
        # Check if any seed gives a lower tier than another
        tier_order_map = {t: i for i, t in enumerate(["low", "moderate", "high", "critical"])}
        min_tier_idx = min(tier_order_map[t] for t in ue["tiers"])
        max_tier_idx = max(tier_order_map[t] for t in ue["tiers"])
        if max_tier_idx > min_tier_idx:
            fn_risk_count += 1
            print(f"    {ue['employee_id']}: Burn Rate={br:.2f}, tiers={ue['tiers']} — "
                  f"seed-driven tier change for elevated employee")

print(f"  Total FN-risk instabilities: {fn_risk_count}")


# ═══════════════════════════════════════════════════════════════════════
# SWEEP 2 — FEATURE ABLATION
# ═══════════════════════════════════════════════════════════════════════
print(f"\n{'='*70}")
print("SWEEP 2 — FEATURE ABLATION")
print("=" * 70)

# Baseline (full 10 features, seed 42)
_, baseline_probs, baseline_y = loocv(df, FEATURES, 42)
baseline_auc = roc_auc_score(baseline_y, baseline_probs)
baseline_shap = shap_on_full(df, FEATURES, 42)
baseline_tiers = {eid: classify_tier(p) for eid, p in
                  zip(df["Employee ID"].values, baseline_probs)}

print(f"\nBaseline (10 features, seed 42):")
print(f"  AUC: {baseline_auc:.4f}")
print(f"  SHAP: {list(baseline_shap.items())[:5]}")

# Phase 4 top 3 features to ablate
# Phase 4 SHAP: tenure_days 28.5%, mental_fatigue_score 25.3%, resource_allocation 24.5%
# Ablation must also remove dependent interaction terms
ablations = [
    {
        "name": "tenure_days",
        "remove": ["tenure_days", "tenure_fatigue", "tenure_workload"],
        "reason": "tenure_days feeds both interaction terms",
    },
    {
        "name": "mental_fatigue_score",
        "remove": ["mental_fatigue_score", "tenure_fatigue"],
        "reason": "MFS feeds tenure_fatigue interaction",
    },
    {
        "name": "resource_allocation",
        "remove": ["resource_allocation", "tenure_workload"],
        "reason": "RA feeds tenure_workload interaction",
    },
]

for abl in ablations:
    ablated_features = [f for f in FEATURES if f not in abl["remove"]]
    print(f"\n--- Ablation: remove {abl['name']} (+ dependencies: {abl['remove']}) ---")
    print(f"  Remaining features ({len(ablated_features)}): {ablated_features}")

    _, abl_probs, abl_y = loocv(df, ablated_features, 42)
    abl_auc = roc_auc_score(abl_y, abl_probs)
    abl_shap = shap_on_full(df, ablated_features, 42)
    abl_tiers = {eid: classify_tier(p) for eid, p in
                 zip(df["Employee ID"].values, abl_probs)}

    auc_drop = (baseline_auc - abl_auc) * 100  # in points
    mfs_pct = abl_shap.get("mental_fatigue_score", 0.0)

    print(f"  AUC: {abl_auc:.4f} (drop: {auc_drop:.1f} points)")
    print(f"  MFS SHAP: {mfs_pct}% {'FAIL >= 40%' if mfs_pct >= 40 else ''}")
    print(f"  SHAP profile: {list(abl_shap.items())[:5]}")

    # Tier changes
    tier_changes = 0
    for eid in df["Employee ID"].values:
        if baseline_tiers[eid] != abl_tiers[eid]:
            tier_changes += 1
            print(f"    Tier change: {eid}: {baseline_tiers[eid]} -> {abl_tiers[eid]}")
    print(f"  Tier changes: {tier_changes}/12")

    # Concentration risk flag
    if auc_drop > 3.0:
        print(f"  FLAG: AUC drop {auc_drop:.1f} points exceeds 3-point threshold — concentration risk")


# ═══════════════════════════════════════════════════════════════════════
# SWEEP 3 — PROXY LEAKAGE (DEMOGRAPHIC FEATURES)
# ═══════════════════════════════════════════════════════════════════════
print(f"\n{'='*70}")
print("SWEEP 3 — PROXY LEAKAGE")
print("=" * 70)

# Encode Gender as binary
df_proxy = df.copy()
df_proxy["gender_binary"] = (df_proxy["Gender"] == "Male").astype(int)

# Baseline tiers (already computed above with 10 features)
print(f"\nBaseline tier assignments (10 features, no Gender):")
for eid in df["Employee ID"].values:
    print(f"  {eid}: {baseline_tiers[eid]}")

# Test 3a: Add Gender temporarily
print(f"\n--- Test 3a: Add Gender as feature ---")
_, gender_probs, gender_y = loocv(df_proxy, FEATURES, 42, extra_features=["gender_binary"])
gender_tiers = {eid: classify_tier(p) for eid, p in
                zip(df["Employee ID"].values, gender_probs)}

gender_changes = 0
for eid in df["Employee ID"].values:
    if baseline_tiers[eid] != gender_tiers[eid]:
        gender_changes += 1
        print(f"  Tier change: {eid}: {baseline_tiers[eid]} -> {gender_tiers[eid]}")

gender_change_pct = gender_changes / 12 * 100
print(f"\n  Tier reassignment rate: {gender_changes}/12 ({gender_change_pct:.1f}%)")
print(f"  Threshold: 10% — {'FLAG' if gender_change_pct > 10 else 'PASS'}")

# Test 3b: Remove Designation (seniority_tier)
print(f"\n--- Test 3b: Remove Designation (seniority_tier) ---")
no_desig_features = [f for f in FEATURES if f != "seniority_tier"]
_, nodesig_probs, nodesig_y = loocv(df, no_desig_features, 42)
nodesig_tiers = {eid: classify_tier(p) for eid, p in
                 zip(df["Employee ID"].values, nodesig_probs)}

desig_changes = 0
for eid in df["Employee ID"].values:
    if baseline_tiers[eid] != nodesig_tiers[eid]:
        desig_changes += 1
        print(f"  Tier change: {eid}: {baseline_tiers[eid]} -> {nodesig_tiers[eid]}")

desig_change_pct = desig_changes / 12 * 100
print(f"\n  Tier reassignment rate: {desig_changes}/12 ({desig_change_pct:.1f}%)")


# ═══════════════════════════════════════════════════════════════════════
# SWEEP 4 — CALIBRATION PER RISK TIER
# ═══════════════════════════════════════════════════════════════════════
print(f"\n{'='*70}")
print("SWEEP 4 — CALIBRATION PER RISK TIER")
print("=" * 70)

# Use seed 42 LOOCV results
_, sweep4_probs, sweep4_y = loocv(df, FEATURES, 42)

# Per-tier Brier
overall_brier = brier_score_loss(sweep4_y, sweep4_probs)
print(f"\nOverall Brier (LOOCV, seed 42): {overall_brier:.4f} (floor: {BRIER_FLOOR})")

tier_briers = {}
for tier_name in TIER_ORDER:
    low, high = TIER_BOUNDARIES[tier_name]
    mask = np.array([(low <= p < high) for p in sweep4_probs])
    # Edge case for critical at 1.0
    if tier_name == "critical":
        mask = np.array([p >= low for p in sweep4_probs])

    count = mask.sum()
    if count > 0:
        tier_y = sweep4_y[mask]
        tier_probs = sweep4_probs[mask]
        tier_brier = brier_score_loss(tier_y, tier_probs)
        tier_briers[tier_name] = {
            "count": int(count),
            "brier": round(tier_brier, 4),
            "passes": tier_brier <= BRIER_FLOOR,
        }
        pass_fail = "PASS" if tier_brier <= BRIER_FLOOR else "FAIL"
        print(f"  {tier_name}: {count} employees, Brier={tier_brier:.4f} ({pass_fail})")
    else:
        tier_briers[tier_name] = {"count": 0, "brier": None, "passes": True}
        print(f"  {tier_name}: 0 employees")

# Identify worst-calibrated tier
worst_tier = None
worst_brier = 0
for t, v in tier_briers.items():
    if v["count"] > 0 and v["brier"] is not None and v["brier"] > worst_brier:
        worst_brier = v["brier"]
        worst_tier = t

print(f"\n  Worst-calibrated tier: {worst_tier} (Brier={worst_brier:.4f})")

print(f"\n{'='*70}")
print("ALL SWEEPS COMPLETE")
