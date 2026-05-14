# Phase 5 — Implications

# Oraclaire Burnout Risk Scorer

# Sprint 1

Date: 2026-05-14
Dataset: data/processed/train_clean.csv (13 rows)
Status: PICK CONFIRMED (D17) — RANDOM FOREST

## MFS SHAP Lines

Random Forest (CANDIDATE): MFS = 25.3%. PASS
Logistic Regression (CANDIDATE, artifact flag): MFS = 0.0%. PASS
XGBoost (DISQUALIFIED): MFS = 97.4%. FLAG
Naive Baseline (BASELINE): N/A.

## Step 1 — Comparison Table

| Model               | Status                    | AUC separation from baseline | LOOCV stability (std dev) | Training complexity | Interpretability  | MFS SHAP % |
| ------------------- | ------------------------- | ---------------------------- | ------------------------- | ------------------- | ----------------- | ---------- |
| Random Forest       | CANDIDATE                 | +0.475                       | 0.361                     | Medium              | Medium (post-hoc) | 25.3% PASS |
| Logistic Regression | CANDIDATE (artifact flag) | +0.500                       | 0.000                     | Low                 | High (native)     | 0.0% PASS  |
| XGBoost             | DISQUALIFIED (D16a)       | +0.200                       | 0.421                     | High                | Medium (post-hoc) | 97.4% FLAG |
| Naive Baseline      | BASELINE                  | 0.000                        | 0.487                     | None                | N/A               | N/A        |

### Tension: Logistic Regression vs Random Forest

Logistic Regression leads Random Forest by 2.5 points on AUC separation and appears perfectly stable (0.000 std dev). Both are artifacts of perfect separation on tenure_days alone — the model found a single boundary that happens to split 13 employees cleanly. That boundary will not hold on 22,750 rows. The AUC lead, the zero variance, and the 100% concentration on one signal are three expressions of the same artifact. Applying the interpretability-over-AUC weight (within 2 points) is complicated because the LR "lead" is not a real lead — it is the artifact expressed as a performance metric. This tension is named here and not resolved. That is the user's call.

Random Forest's 0.361 stability is imperfect but genuine — the model makes different decisions across folds because it is actually weighing multiple signals, not riding one spurious boundary.

## Step 2 — Model Profiles

### Random Forest

This model identifies employees whose combined circumstances — time in role, sustained energy decline, and workload demands — create conditions where burnout is likely. It draws on all three signals simultaneously and in roughly equal measure, which means it can catch employees early: people who are beginning to show strain across several areas at once, not just the ones who are already exhausted. It pays attention to seniority level and working arrangement as contributing context. It struggles with employees who are new to the organisation and already overwhelmed — the model has limited history to work with and may underestimate risk for someone in their first year who was handed too much too fast. It also misses borderline cases: employees whose signals are mixed — moderate energy, moderate workload, moderate tenure — get a moderate score, which is honest but means the model will not aggressively flag someone who is coasting toward burnout slowly.

### Logistic Regression

On this validation sample, the model appears to perfectly separate burned-out employees from healthy ones using a single signal: how long they have been with the organisation. It correctly identifies every employee. However — this performance is almost certainly a coincidence of the small dataset rather than a genuine predictive relationship. The model has found a tenure threshold that happens to cleanly divide thirteen people into two groups. On a larger workforce, tenure alone cannot distinguish a burned-out senior from a thriving senior, or an overwhelmed new hire from an energised one. What the model appears to do well — perfect identification — is exactly what cannot be trusted on thirteen rows. Its real behaviour on the full workforce is unknown and must be verified before any deployment decision.

## Step 3 — Recommendation

I am recommending Random Forest because it is the only candidate whose results are not contaminated by a known data artifact. It identifies employees whose length of time in role, sustained energy decline, and heavy workload converge into a burnout pattern — drawing on all three signals in balance rather than collapsing onto any single indicator. Its explanations can be presented to a Data Protection Officer or Legal counsel through post-hoc analysis showing which factors drove each individual score, though this requires an additional interpretation step compared to a model whose reasoning is visible by design. The trade-off accepted is twofold: the model misclassifies one borderline junior employee on this sample — someone showing early strain that the model rates lower than the situation may warrant — and the model sacrifices native interpretability for genuine multi-signal detection, which means each employee's score requires a supporting explanation rather than standing alone. The simpler alternative appears to outperform by a margin that would normally earn it the recommendation, but that margin is a statistical artifact of the small sample, not genuine superiority.

### Founder's Rationale (D17)

Random Forest was picked not because it won cleanly but because it was the only candidate that told the truth about what it was doing — using three signals roughly equally to describe a three-dimensional problem. The other candidates either collapsed to one signal or collapsed to one row.

## Step 4 — Rejected Alternatives

XGBoost produces usable predictions but is almost entirely a fatigue detector — it scores employees based on how tired they report feeling and ignores workload, tenure, seniority, and working conditions; that single-signal dependency was identified and disqualified in Decision D16 as incompatible with a product that must catch burnout before fatigue becomes visible.

Logistic Regression achieves perfect classification on the validation sample but does so by finding a single spurious tenure boundary that accidentally separates thirteen employees — a coincidence that will not hold on the real workforce, making its apparent superiority unreliable until proven otherwise on the full dataset.

The naive baseline correctly identifies all at-risk employees by simply flagging everyone as elevated, which produces zero missed cases but also generates unnecessary HR check-ins across the entire workforce — a strategy that works on thirteen rows but cannot scale to a real organisation where most employees are healthy.

## Distinct-Action Test

LOW: No HR visibility. Employee sees their own trend. No action required.

MODERATE: Employee-only signal. Curated resources surfaced to the employee matched to their risk drivers. No HR notification. No manager visibility.

HIGH: HR receives aggregate signal at team level. Manager receives a prompt to check in. Individual identity protected unless the employee opts to share.

CRITICAL: Human review gate required before any action, per D8 EU AI Act high-risk employment classification. HR escalation with mandatory reviewer sign-off. Individual identity visible to the reviewer.

### Collapse Check

No collapse candidates. All four tiers produce functionally distinct actions:

- LOW triggers nothing external
- MODERATE triggers employee-facing resources without employer visibility
- HIGH triggers employer-side aggregate visibility without individual identification
- CRITICAL triggers individual identification with mandatory human gate

The escalation path is one-directional (employee-only → aggregate → individual with gate). No two tiers share the same action set.

## Stakeholder References

HR Director owns the alert ceiling: how many High and Critical flags per cycle before the Organisational Risk Threshold fires at twenty percent combined rate (D14 Parameter 10, D15-2). Random Forest's balanced signal profile means the alert volume will be driven by genuine multi-factor risk rather than a single fatigue threshold, giving the HR Director a defensible basis for organisational escalation.

Legal and Data Protection Officer must approve the model explanation format. Random Forest requires post-hoc explanations, which are legible to a DPO but require the supporting analysis to be generated and presented. The DPO should review the SHAP decomposition format before Sprint 1 deployment to confirm it meets their interpretability standard.

Employee owns their individual score and risk driver breakdown. The three-signal balance means the employee sees which factors contributed to their score — not just a single "you are tired" message. The employee-facing output must be readable by a non-technical person in under sixty seconds, with the action they can take made immediately visible.

## Phase 6 Pre-Commitments (from D17)

1. Re-run full sweep on Kaggle dataset (~22,750 rows) with stratified 80/20 split — Random Forest must beat naive baseline on AUC
2. LR artifact resolution — confirm LR does not achieve perfect separation on full dataset; if it does, investigate data leakage
3. Random Forest MFS SHAP re-check on full dataset — must remain below 40%
4. Threshold selection on full dataset cost curve — 0.30 is provisional. Drift tolerance: ±0.05 from provisional 0.30. Movement outside this range requires a new cost rationale recorded in the decision log. Pre-registered to prevent opportunistic threshold movement after seeing full dataset numbers.
5. Gender fairness audit — run on final model outputs using Gender as audit variable (not feature), per D11 Nuance 4
6. XGBoost Sprint 2 re-entry — re-run sweep with behavioral features; MFS must be below 40%
7. Random Forest SHAP profile must remain balanced across at least three features with no single feature above 40% on the full dataset. If it concentrates — stop and investigate before proceeding to threshold selection.

## Phase 6 Exit Criteria (from D17)

- Random Forest beats naive baseline on AUC on full dataset
- MFS SHAP below 40% on full dataset
- SHAP balanced across at least three features
- Threshold within ±0.05 drift tolerance or new cost rationale recorded
- Gender fairness audit completed (no disparate impact)
- DPO sign-off on SHAP output format required before first customer deployment. Not optional. Not deferrable to Sprint 2.
- Four-tier escalation architecture locked — no changes in Phase 6

## Sprint 1 Model (confirmed D17)

Model: Random Forest (n_estimators=100, max_depth=5, random_state=42)
Provisional threshold: 0.30 (drift tolerance ±0.05)
Feature set: 9 confirmed features (8 active after Designation multicollinearity drop)
Four-tier escalation: locked
DPO sign-off gate: required before deployment
Two-threshold serving layer (D11 Nuance 3): Threshold A general FN target 15% / FP ceiling 15%; Threshold B senior FN target 10% / FP ceiling 20%
Disqualified: XGBoost (Sprint 2 re-entry on behavioral features, MFS SHAP below 40%)
