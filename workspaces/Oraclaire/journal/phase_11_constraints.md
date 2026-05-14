# Phase 11 — Constraints

# Oraclaire Burnout Risk Scorer

# Sprint 1

Date: 2026-05-14
Status: DRAFT — formalises Phase 10 objective into enforceable product constraints

---

## Constraint Classification

**Hard constraint:** Must be satisfied. Violation blocks the product action. Source is a pre-registered floor, legal requirement, or architectural decision.

**Soft constraint:** Penalised in the objective but not blocking. Source is a target, aspiration, or operational guideline.

---

## Hard Constraints

### H1: FP Rate Ceiling

```
r_FP ≤ 0.20 (decay threshold — D5)

r_FP ≤ 0.15 (pre-registered ceiling — D14 Parameter 8, currently accepted at 0.166 with D26 override)
```

Violation at 0.20: participation death spiral activates (D5 — 40-60% drop by cycle 3).
Violation at 0.15: accepted override at 0.166 per D26, within 5-point buffer to decay threshold.

Enforcement: measured quarterly against scored population. If r_FP > 0.20 for two consecutive cycles: rollback trigger fires (Phase 8 Step 5).

### H2: FN Rate Target

```
r_FN ≤ 0.15 (pre-registered target — D14 Parameter 9)
```

Violation: model misses more than 15% of burned-out employees. FN cost exposure increases proportionally.

Enforcement: measured quarterly. If breached: model must be retrained or threshold recalibrated before next cycle.

### H3: Organisational Risk Threshold Ceiling

```
(x[high] + x[critical]) / N ≤ 0.20 (ORT ceiling — D14 Parameter 10)
```

Violation: High+Critical combined exceeds 20% of scored population. Individual alerts suppressed per D14 architecture — the organisation cannot respond to more than 20% flagged employees without alert fatigue.

Enforcement: measured per quarterly cycle. If exceeded: auto-flag ceiling suppresses new High/Critical alerts until next cycle resets.

### H4: Critical Tier Population Cap

```
x[critical] / N ≤ 0.05 (Critical cap — D14 Parameter 7, boundary at 0.90 per D24)
```

Violation: more than 5% of scored population hits Critical. Reviewer capacity cannot absorb the volume within the 48-hour window (D8).

Enforcement: if Critical exceeds 5%, the Critical boundary is raised until the cap is met. Current boundary: 0.90 (D24). Validated on full dataset at 39.1% Critical at 0.75 boundary — raised to 0.90 to meet this cap.

### H5: Critical Tier Review Window

```
review_completion_time ≤ 48 hours (D8 EU AI Act, config.py REVIEW_TIMEOUT_HOURS)
```

Violation: any Critical flag unreviewed beyond 48 hours auto-escalates. Auto-escalation rate tracked as Signal 5 in monitoring plan (alert if > 10% per week).

Enforcement: operational. Reviewer capacity must be sized to clear x[critical] × 30 minutes within each 48-hour window.

### H6: MFS SHAP Dominance Gate

```
SHAP(mental_fatigue_score) < 40% (D16, confirmed post-RE-DO at 29.9%)
```

Violation: SHAP waterfall display blocked for all employees. Product cannot surface employee-facing explanations.

Enforcement: measured at each model retrain. If breached: SHAP waterfall suppressed until feature engineering resolves dominance.

### H7: Brier Calibration Floor

```
Brier ≤ 0.15 (D18, current: 0.0844)
```

Violation: probability outputs unreliable. Threshold cannot be applied to uncalibrated probabilities.

Enforcement: measured at each model retrain. If breached: Platt scaling applied before threshold selection (D18 prescription).

### H8: Minimum Participation Rate

```
participation_rate ≥ 0.20 sustained over 2 consecutive cycles (D13 Sprint 1 target)
```

Violation: aggregate statistics become unreliable. MIN_TEAM_SIZE = 5 (D1) cannot be met if participation is below 20% for most teams.

Enforcement: measured quarterly. If below 20% for 2 consecutive cycles: product pauses assessment cycle and HR Director is notified to investigate participation barriers.

---

## Soft Constraints

### S1: Participation Architecture Target

```
participation_rate → 0.40 (D13 architecture target — aspirational)
```

Not enforced. Tracked as a product health metric. The gap between 0.20 (hard floor) and 0.40 (target) is where the four participation mechanisms (weekly pulse, monthly CBI, employee-first gate, SHAP-matched content) are designed to operate.

### S2: Assessment Cadence

```
assessment_frequency = 1 per quarter (current)
```

Not enforced as a constraint. Assessment frequency affects C_assessment in the objective — higher frequency increases cost and participation risk. The quarterly cadence is a product decision, not a constraint. If the pilot data suggests monthly assessment is viable without participation decay, the cadence can increase.

### S3: Critical Tier Reviewer Capacity

```
x[critical] × 30 minutes ≤ available_reviewer_hours × 60
```

This is an operational constraint that Phase 11 formalises but does not enforce in code. It informs the reviewer cost term in the objective (C_reviewer). If reviewer capacity is constrained, the Critical boundary must be raised to reduce volume — which is a product configuration decision, not a code enforcement.

### S4: Threshold Drift Range

```
THRESHOLD_A ∈ DRIFT_ACCEPTABLE_RANGE = (0.30, 0.40)
```

Currently at 0.35 per D26. Adjustments within this range are operational decisions. Adjustments outside this range require a new D-number with cost rationale (D26 prescription).

---

## Constraint-to-Objective Mapping

| Constraint              | Type | Objective term affected       | Enforcement mechanism                             |
| ----------------------- | ---- | ----------------------------- | ------------------------------------------------- |
| H1 FP ceiling           | Hard | C_FP                          | Quarterly measurement, rollback at 25% × 2 cycles |
| H2 FN target            | Hard | C_FN                          | Quarterly measurement, retrain if breached        |
| H3 ORT ceiling          | Hard | C_FP + C_reviewer             | Auto-flag suppression when High+Critical > 20%    |
| H4 Critical cap         | Hard | C_reviewer                    | Boundary adjustment to meet 5% cap                |
| H5 Review window        | Hard | C_reviewer                    | Auto-escalation after 48 hours                    |
| H6 MFS gate             | Hard | C_FN (via model quality)      | SHAP waterfall suppression                        |
| H7 Brier floor          | Hard | C_FN + C_FP (via calibration) | Platt scaling before threshold                    |
| H8 Participation        | Hard | C_assessment                  | Product pause if below 20% × 2 cycles             |
| S1 Participation target | Soft | C_assessment                  | Tracked, not enforced                             |
| S2 Assessment cadence   | Soft | C_assessment                  | Product decision                                  |
| S3 Reviewer capacity    | Soft | C_reviewer                    | Operational sizing                                |
| S4 Drift range          | Soft | C_FN + C_FP                   | Requires D-number if exceeded                     |

---

## What Phase 11 Does NOT Constrain

Phase 11 constrains the product's operating envelope — not the model's internals. Model hyperparameters (n_estimators, max_depth), feature selection, and training pipeline are governed by the Phase 6 pre-registration and the config.py constants, not by the LP constraint set.

The LP constraint set answers: "given a model that produces scores, what operating bounds must the product respect when acting on those scores?" It does not answer: "what model produces the best scores?" That question was answered in Phases 4–7.

---

Phase 11 constraints drafted. Ready to commit with Phase 10 and pivot to DPO review package.
