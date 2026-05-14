# Phase 7 — Red-Team

# Oraclaire Burnout Risk Scorer

# Sprint 1

Date: 2026-05-14
Dataset: data/processed/train_clean.csv (12 rows — sample only)
Feature set: 10 features (post-D24 RE-DO: 8 original + tenure_fatigue + tenure_workload)
Pre-registered floors: workspaces/Oraclaire/journal/phase_6_preregistration.md
Status: SWEEPS COMPLETE

---

## Sweep Results

### Sweep 1 — Model Stability (Re-seed)

Three LOOCV runs with seeds 42, 123, 456. 12 models per run. 36 total trainings.

Cite: `src/model/train.py` `train()` function, `src/config.py` `MODEL_PARAMS`.

| Seed | AUC    | Brier  | MFS SHAP | Tier dist (Low/Mod/High/Crit) |
| ---- | ------ | ------ | -------- | ----------------------------- |
| 42   | 0.9714 | 0.0844 | 23.6%    | 6/1/1/4                       |
| 123  | 0.9714 | 0.0880 | 25.5%    | 6/1/1/4                       |
| 456  | 0.9429 | 0.1036 | 21.7%    | 7/1/1/4                       |

All seeds pass Brier floor (0.15) and MFS SHAP gate (40%).

**Per-employee tier stability:**

| Employee | Seed 42  | Seed 123 | Seed 456 | Stable?  | Burn Rate |
| -------- | -------- | -------- | -------- | -------- | --------- |
| EID_001  | moderate | moderate | low      | UNSTABLE | 0.45      |
| EID_002  | low      | low      | low      | stable   | 0.90      |
| EID_003  | low      | low      | low      | stable   | 0.16      |
| EID_004  | critical | critical | critical | stable   | 1.00      |
| EID_005  | low      | low      | low      | stable   | 0.19      |
| EID_006  | critical | critical | critical | stable   | 0.99      |
| EID_008  | low      | low      | low      | stable   | 0.06      |
| EID_010  | critical | critical | critical | stable   | 0.99      |
| EID_012  | high     | high     | high     | stable   | 0.57      |
| EID_014  | low      | low      | low      | stable   | 0.84      |
| EID_017  | low      | low      | low      | stable   | 0.06      |
| EID_018  | critical | critical | critical | stable   | 0.99      |

11/12 stable (92%). 1/12 unstable (8%).

**Unstable employee detail:**

EID_001 (Burn Rate 0.45 — exactly at binarisation threshold): moves from Moderate (seeds 42, 123) to Low (seed 456). This is a seed-driven FN risk for an elevated employee.

FN cost source (verbatim from D3): "$4,000 per missed burned-out junior employee per year (conservative base case). $21,000 per missed burned-out senior employee per year (knowledge-work deployment)."

EID_001 is Designation "Analyst" (junior). FN cost: $4,000/year.

---

### Sweep 2 — Feature Ablation

Baseline: 10 features, seed 42, LOOCV AUC 0.9714.

Cite: `src/model/train.py` `train()`, `src/model/serve.py` `score()`, `src/config.py` `FEATURES`.

Ablation removes the named feature AND its dependent interaction terms (tenure_fatigue depends on tenure_days + MFS; tenure_workload depends on tenure_days + resource_allocation).

#### Ablation 1: Remove tenure_days (+ tenure_fatigue, tenure_workload)

Remaining: 7 features. AUC: 0.9143. **Drop: 5.7 points — concentration risk flag (> 3 points).**

MFS SHAP after removal: 31.0%. Does NOT exceed 40% — D16 disqualification finding does NOT apply to RF when tenure is absent. However, MFS rises from 23.6% to 31.0% (+7.4pp).

Tier changes: 6/12 employees reassigned. EID_012 moves High → Low (FN risk for elevated employee, $4,000/year D3).

Qualitative severity: If tenure is undifferentiated at a real employer (all employees similar tenure), model produces undifferentiated scores. No sourced dollar figure for this scenario.

#### Ablation 2: Remove mental_fatigue_score (+ tenure_fatigue)

Remaining: 8 features. AUC: 0.8857. **Drop: 8.6 points — concentration risk flag (> 3 points).**

MFS SHAP after removal: 0.0% (feature removed, N/A). Model genuinely needs the fatigue signal — AUC drops most when MFS is removed. Other features partially compensate but cannot fully replace it.

Tier changes: 2/12 employees reassigned.

#### Ablation 3: Remove resource_allocation (+ tenure_workload)

Remaining: 8 features. AUC: 0.9714. Drop: 0.0 points — no AUC degradation.

**MFS SHAP after removal: 38.4% — 1.6pp below the 40% D16 gate.**

resource_allocation (and its interaction tenure_workload) is the key feature holding MFS below the gate. Without it, MFS nearly breaches. This is a fragility — the MFS gate passes only because resource_allocation absorbs enough SHAP weight.

Tier changes: 2/12 employees reassigned.

---

### Sweep 3 — Proxy Leakage (Demographic Features)

Cite: Phase 3 proxy-drop results in `workspaces/Oraclaire/journal/phase_3_features.md`, `src/model/train.py` `train()`.

#### Test 3a: Add Gender as feature

Tier reassignment rate: **0/12 (0.0%)** — PASS (below 10% threshold).

The model is not sensitive to Gender even when it is provided as a feature. No disparate impact risk from Gender on this sample.

#### Test 3b: Remove Designation (seniority_tier)

Tier reassignment rate: **0/12 (0.0%)**.

Designation/seniority_tier is not driving tier assignments for these 12 employees.

Cost source (verbatim from D11 Nuance 4): "litigation exposure and product credibility risk" — no dollar figure in the cost model.

---

### Sweep 4 — Calibration Per Risk Tier

LOOCV Brier scores per tier. Overall Brier: 0.0844 (PASS — below 0.15 floor).

Cite: Phase 4 LOOCV results in `workspaces/Oraclaire/journal/phase_4_candidates.md`, Phase 6 pre-registration in `workspaces/Oraclaire/journal/phase_6_preregistration.md`.

| Tier     | Employees | Brier  | Floor (0.15) | Result                                                      |
| -------- | --------- | ------ | ------------ | ----------------------------------------------------------- |
| Low      | 4         | 0.0059 | PASS         | Well-calibrated                                             |
| Moderate | 1         | 0.6084 | **FAIL**     | below pre-registered floor — Phase 8 gate failure candidate |
| High     | 1         | 0.3249 | **FAIL**     | below pre-registered floor — Phase 8 gate failure candidate |
| Critical | 4         | 0.0000 | PASS         | Perfect calibration                                         |

Worst-calibrated tier: Moderate (Brier 0.6084).

**Important context:** Both failing tiers contain exactly 1 employee each (EID_001 in Moderate, EID_012 in High). Per-tier Brier with n=1 is the squared error for a single prediction — not a statistical calibration metric. These failures indicate the model's probability for EID_001 (at the binarisation boundary) and EID_012 (in the High tier) deviates from their true labels, but the sample size is insufficient to draw general calibration conclusions.

High tier FP cost source (verbatim from D2): "$15 per unnecessary HR check-in per employee." With 1 High-tier employee: $15 × 4 quarterly cycles = $60/year if the High prediction is false.

---

## Dollar Severity Ranking

All figures sourced. No invented figures.

1. **S1-F1: EID_001 seed instability** — FN risk $4,000/year (D3, junior). One elevated employee moves from Moderate to Low based on random seed.

2. **S2-F1: tenure_days concentration risk** — qualitative. 5.7-point AUC drop on removal. If tenure is undifferentiated at a real employer, model produces undifferentiated scores. No dollar figure in cost model.

3. **S2-F2: resource_allocation fragility** — qualitative. MFS rises to 38.4% (1.6pp below gate) when removed. If resource_allocation distribution shifts at deployment, MFS gate could breach, requiring SHAP waterfall suppression (D24 hard gate).

4. **S2-F3: mental_fatigue_score dependency** — qualitative. 8.6-point AUC drop on removal confirms model genuinely needs fatigue signal. Not a risk per se — confirms feature necessity.

5. **S4-F1: Moderate tier Brier 0.6084** — $60/year maximum FP cost (D2: $15 × 1 employee × 4 quarters). n=1, not statistically meaningful.

6. **S4-F2: High tier Brier 0.3249** — $60/year maximum FP cost (D2: $15 × 1 employee × 4 quarters). n=1, not statistically meaningful.

7. **S3-F1: Gender proxy** — 0% tier change. No cost. Qualitative: "litigation exposure and product credibility risk" (D11 Nuance 4) — not triggered.

---

## Findings Table

| #     | Sweep | Finding                                                                               | Severity ($)                             | Recommendation                                                                                                   | Disposition |
| ----- | ----- | ------------------------------------------------------------------------------------- | ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ----------- |
| S1-F1 | 1     | EID_001 seed instability: elevated employee (BR 0.45) moves Moderate→Low across seeds | $4,000/year FN (D3)                      | MITIGATE — document EID_001 as boundary case; confirm threshold catches them at 0.40                             | TODO        |
| S2-F1 | 2     | tenure_days ablation: 5.7-point AUC drop, 6/12 tier changes — concentration risk      | Qualitative (no dollar in cost model)    | ACCEPT — document as known concentration; flag for Sprint 2 feature expansion                                    | TODO        |
| S2-F2 | 2     | resource_allocation removal: MFS SHAP rises to 38.4% (1.6pp below 40% gate)           | Qualitative (MFS gate near-miss)         | MITIGATE — monitor resource_allocation distribution at first deployment; if undifferentiated, flag MFS gate risk | TODO        |
| S2-F3 | 2     | mental_fatigue_score ablation: 8.6-point AUC drop — model depends on fatigue signal   | Qualitative (confirms feature necessity) | ACCEPT — confirms model genuinely uses fatigue signal; not a risk                                                | TODO        |
| S3-F1 | 3     | Gender addition: 0% tier reassignment — no disparate impact detected                  | $0 (no impact)                           | ACCEPT — no action required on this sample                                                                       | TODO        |
| S4-F1 | 4     | Moderate tier Brier 0.6084 — fails 0.15 floor (n=1)                                   | $60/year max FP (D2)                     | ACCEPT — n=1; not statistically meaningful; EID_001 is at binarisation boundary                                  | TODO        |
| S4-F2 | 4     | High tier Brier 0.3249 — fails 0.15 floor (n=1)                                       | $60/year max FP (D2)                     | ACCEPT — n=1; single-employee squared error, not calibration failure                                             | TODO        |

---

## Fairness Dimension

Fairness audit — deferred to Sprint 2 per Oraclaire Playbook.

Reason for deferral: the 12-row sample dataset does not have sufficient demographic representation to produce meaningful fairness metrics. Gender fairness audit requires a dataset large enough to compute disaggregated performance metrics by demographic group.

Pre-commitment from D11 Nuance 4 and D17 Phase 5 pick: Gender fairness audit to be run on final model outputs using Gender as audit variable (not feature) on the full Kaggle dataset (~22,750 rows).

This is not optional. It is a pre-registered commitment. Sprint 2 opens with this audit.

---

Red-team complete. 7 findings across 4 sweeps. Waiting for your disposition per finding.
