# Phase 6 — Pre-Registration

# Oraclaire Burnout Risk Scorer

# Sprint 1

Date: 2026-05-14

Status: PRE-REGISTRATION — PENDING FOUNDER TODO VALUES

## Pre-Registration Timestamp

Pre-registration timestamp: 2026-05-14 (session-local, exact HH:MM pending founder confirmation)

Pre-registration order of operations:

- Phase 4 leaderboard: READ
- Phase 5 model pick: CONFIRMED (Random Forest, D17)
- Phase 5 provisional threshold: KNOWN (0.30)
- Phase 6 floors written: NOW
- Phase 6 leaderboard re-read: PENDING — after founder fills TODO values

TODO values filled: 2026-05-14

Pre-registration is now complete. All floors and threshold rules were written before the Phase 6 leaderboard re-read. Disclosure: model pick and provisional threshold were known before these values were set. See Step 1 disclosure.

## Disclosure

Phase 6 floors are being pre-registered after the Phase 4 leaderboard was read and after Phase 5 model selection was completed. The model pick (Random Forest) and provisional threshold (0.30) were known before these floors were written. This does not invalidate the pre-registration — it documents the honest order of operations for the decision log.

---

## Threshold Rule

### Step 2a — Curve and Why

Curve: Precision-Recall. Rationale: imbalanced classes (25% burnout prevalence), cost-asymmetric errors. Selection criterion: minimum expected cost on the cost table, not maximum F1.

Why PR not ROC: ROC evaluates performance across all classification thresholds assuming equal class prevalence. Oraclaire's burned-out population is 25% of the workforce (D14 Parameter 2). That is a moderately imbalanced problem. More importantly the cost of errors is not symmetric — FN costs 267x more than FP at the minimum. ROC treats both error types as equally costly. PR does not. On an imbalanced, cost-asymmetric problem PR is the honest curve.

The operating threshold is read from the PR curve at the point that minimises expected cost — not maximises F1, not maximises accuracy, not maximises AUC. Minimum expected cost is the selection criterion.

### Step 2b — Cost Asymmetry — Sourced Verbatim

FN cost term — from D3:

"$4,000 per missed burned-out junior employee per year (conservative base case). $21,000 per missed burned-out senior employee per year (knowledge-work deployment)."

FP cost term — from D2:

"$15 per unnecessary HR check-in per employee."

Cost asymmetry ratio: $4,000 / $15 = 267:1 minimum. $21,000 / $15 = 1,400:1 for senior employees.

FN:FP cost asymmetry: 267:1 junior, 1,400:1 senior. Source: D3 and D2 decision log. The threshold rule must favour recall over precision — missing a burned-out employee costs 267 to 1,400 times more than flagging a healthy one incorrectly.

### Step 2c — Calibration Floor

Before threshold selection the model must pass a calibration check.

The calibration metric is Brier score. A well-calibrated model has Brier score below [TODO — founder sets value].

If Brier score exceeds the floor: calibrate using Platt scaling before reading the threshold from the PR curve. Do not select a threshold on an uncalibrated model — the probability outputs the threshold is applied to are unreliable if calibration fails.

Calibration floor: Brier score ≤ 0.15. If breached: apply Platt scaling before threshold selection. Do not set threshold on uncalibrated probability outputs. Phase 4 result: 0.0712 (comparison against floor is founder's decision).

Founder's reasoning: Random Forest Phase 4 result was 0.0712. Setting the floor at 0.15 gives a 2x buffer above the known result. This is not a floor designed to be comfortable — it is a floor that would catch meaningful calibration degradation on the full dataset. A Brier score above 0.15 on a binary classification problem with 25% class prevalence means the model's probability outputs are unreliable enough to distort the cost table. Why not tighter than 0.15: the sample is 13 rows. The full dataset will produce a different Brier score. Setting the floor at 0.10 risks triggering calibration on a model that is well-calibrated on real data simply because the sample Brier was unusually good on 13 rows. Why not looser than 0.15: a floor above 0.20 would allow a poorly calibrated model to proceed to threshold selection. That is the failure mode the floor exists to prevent. 0.15 is the defensible middle.

---

## Two-Threshold Architecture

Oraclaire uses two operating thresholds not one (D11 Nuance 3, confirmed D17).

Two-threshold architecture: Threshold A (general) and Threshold B (senior tier) are read from separate PR curves on the respective population subsets. They are not the same number applied to two populations — they are two separate cost-optimised operating points on two separate curves.

### Threshold A — General Population

Rule: read from PR curve at minimum expected cost using FN cost $4,000 junior.

FP ceiling: 15% — D14 Parameter 8 confirmed. No change. The 5-point buffer against the 20% participation death spiral threshold is the right operating margin for a product that depends on employee trust to function.

FN target: 15% — D14 Parameter 9 confirmed. No change. 15% FN on the general population means the model catches 85% of scorable burned-out employees. Combined with the 15% FP ceiling this is the operating envelope that balances early detection against participation preservation.

### Threshold B — Senior Tier

Rule: read from PR curve at minimum expected cost using FN cost $21,000 senior.

FP ceiling: 20% — D14 Parameter 9 confirmed. No change. I accept higher FP on senior staff because the asymmetry is 1,400:1. A false alarm on a senior employee costs one 30-minute HR check-in. A miss costs $21,000 plus replacement risk. 20% FP ceiling on the senior tier is the right trade-off.

FN target: 10% — D14 Parameter 9 confirmed. No change. The senior tier FN target is tighter than the general population target because the cost of missing a senior employee is 5x higher. 10% FN means the model catches 90% of scorable burned-out senior employees. That is the operating standard the cost asymmetry requires.

Note: the TODO values above are already locked in D14 Parameters 8 and 9. The founder confirms or overrides them here as the Phase 6 floor values. They are not unknown — they are being formally pre-registered.

---

## Dollar-Lift Framework

### Daily FN Exposure Formula

From the corrected D10 formula:

```
Daily FN = [87.5(1-e) × r_A × $4,000
           + 37.5(1-e) × r_B × $21,000]
           / 365
           + [87.5 × e × $4,000
           + 37.5 × e × $21,000]
           / 365
```

Where:

- r_A = FN rate on general scorable population at Threshold A
- r_B = FN rate on senior scorable population at Threshold B
- e = exclusion fraction (placeholder 0.10 conservative, 0.20 stressed per D10)

### Daily FP Exposure Formula

```
Daily FP = FP_count × $15 / 30
```

Where:

- FP_count = number of healthy employees flagged High or Critical in one quarterly cycle

### Lift Formula

```
Daily lift = Daily FN (do nothing) minus Daily FN (at chosen threshold) minus Daily FP cost

Annual lift = Daily lift × 365
```

### Do-Nothing Baseline

Daily FN at r=1.0 (miss everyone):

```
= [87.5(1-e) × $4,000 + 37.5(1-e) × $21,000] / 365
  + [87.5 × e × $4,000 + 37.5 × e × $21,000] / 365
= $3,116.44 × (1-e) + $3,116.44 × e
= $3,116.44 per day (full exposure, model catches nobody)
```

Annual do-nothing baseline: $3,116.44 × 365 = $1,137,500

### Oraclaire Lift at Threshold

```
Annual lift = $1,137,500
             minus (Daily FN at chosen r_A and r_B × 365)
             minus (Annual FP cost)
```

Dollar-lift formula recorded. Founder plugs in r_A, r_B, and e after threshold selection. Do-nothing annual baseline: $1,137,500 at e=0.10. $1,137,500 × (1-e) scales with deployment-specific exclusion fraction.

---

## TODO — Founder Values

These values are pre-registered as floors. The founder fills them before the Phase 6 leaderboard is re-read.

| Parameter              | Value | Source            |
| ---------------------- | ----- | ----------------- |
| Brier floor            | 0.15  | Founder sets      |
| Threshold A FP ceiling | 15%   | D14 locked at 15% |
| Threshold A FN target  | 15%   | D14 locked at 15% |
| Threshold B FP ceiling | 20%   | D14 locked at 20% |
| Threshold B FN target  | 10%   | D14 locked at 10% |

### Threshold Drift Tolerance

Threshold drift tolerance: ±0.05 from provisional 0.30.

Acceptable range: 0.25 to 0.35.

Source: D17 commitment.

If the full dataset cost minimum falls within 0.25 to 0.35 — keep threshold at 0.30.

If the full dataset cost minimum falls outside that range — move the threshold and record the new cost rationale in the decision log.
