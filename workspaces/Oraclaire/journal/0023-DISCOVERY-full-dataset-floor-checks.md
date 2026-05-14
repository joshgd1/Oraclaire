---
type: DISCOVERY
date: 2026-05-14
created_at: 2026-05-14T15:30:00+10:00
author: co-authored
session_id: resume-post-clear
session_turn: 2
project: Oraclaire
topic: Full Kaggle dataset re-run fails three D18 floor checks
phase: redteam
tags: [full-dataset, floor-checks, D16-gate, D18, D21, threshold-calibration]
---

# Discovery D23 — Full Dataset Re-run: Three Floor Checks Fail

The 12-row Sprint 1 model passes all floors. The full 21,626-row Kaggle dataset reveals three failures that block deployment.

## Dataset

- **Source:** `data/raw/train.csv` — 22,751 rows total
- **After cleaning:** 21,626 labelled rows (1,124 unlabelled saved to pool)
- **Class balance:** 51.3% elevated at BINARISATION_THRESHOLD=0.45
- **Split:** 80/20 stratified (17,300 train / 4,326 test)

## Bug Fixed: Numeric Designation Handling

Raw Kaggle data uses numeric Designation (0.0-5.0); `engineer_features` mapped string keys ("Analyst", "Manager") only. All rows received `seniority_tier=0`. Fixed to handle both formats. Senior employees: 2,651 (12.3% of full dataset).

## Floor Check Results

| Floor | Check                          | Result    | Value        | Ceiling             | Status |
| ----- | ------------------------------ | --------- | ------------ | ------------------- | ------ |
| 1     | Brier score                    | 0.0783    | 0.15         | **PASS**            |
| 2     | MFS SHAP                       | 46.9%     | 40%          | **FAIL** (by 6.9pp) |
| 3     | FP rate (Threshold A, general) | 20.1%     | 15%          | **FAIL** (by 5.1pp) |
| 4     | FN rate (Threshold A, general) | 5.8%      | 15%          | PASS                |
| 5     | FP rate (Threshold B, senior)  | 0.0%      | 20%          | PASS (vacuous)      |
| 6     | FN rate (Threshold B, senior)  | 0.0%      | 10%          | PASS (vacuous)      |
| 7     | Threshold drift                | Both 0.30 | (0.25, 0.35) | PASS                |
| 8     | Critical tier ≤ 5%             | 39.1%     | 5%           | **FAIL**            |

## Finding 1: MFS SHAP Dominance (46.9%)

MFS accounts for 46.9% of SHAP importance, exceeding the 40% D16 gate. The 12-row model showed 19.4% (well under). The full dataset reveals the model is significantly fatigue-driven.

SHAP profile (full dataset):

- mental_fatigue_score: 46.9%
- resource_allocation: 33.4%
- wfh_setup: 9.3%
- seniority_tier: 7.9%
- missing_mfs: 1.0%

**Options:**

- A) Add features to dilute MFS (tenure interactions, team-level aggregates, engagement proxy)
- B) Accept with documented rationale — risky, defeats D16 purpose
- C) Explore alternative model architectures that distribute importance differently

## Finding 2: FP Rate at 20.1% (Threshold A)

At threshold 0.30, 20.1% of general-population non-burnout employees are flagged — exceeding the 15% ceiling by 5.1 percentage points. The FN rate at 5.8% is well under target, meaning the model has room to shift threshold upward.

Threshold sensitivity (general population, 3,795 employees):

| Threshold | FP rate | FN rate | FP pass? | FN pass? |
| --------- | ------- | ------- | -------- | -------- |
| 0.30      | 20.0%   | 5.8%    | FAIL     | PASS     |
| 0.35      | 14.7%   | 9.4%    | PASS     | PASS     |
| 0.40      | 11.8%   | 11.9%   | PASS     | PASS     |
| 0.45      | 10.4%   | 13.5%   | PASS     | PASS     |
| 0.50      | 8.6%    | 16.4%   | PASS     | FAIL     |

**Threshold 0.35 passes both floors** and remains within drift range (0.25, 0.35). This is the narrow end of the range.

**Options:**

- A) Raise Threshold A to 0.35 — passes both floors, at drift boundary
- B) Raise Threshold A to 0.40 — more margin on both floors
- C) Keep 0.30 and accept higher FP — requires D18 ceiling revision

## Finding 3: Critical Tier at 39.1%

At the 0.75 Critical boundary, 39.1% of employees are classified Critical — far exceeding the D14 Parameter 7 target of ≤5%. The model produces very high probabilities for a large portion of employees (P75 = 0.90, P90 = 0.96).

Critical tier at different boundaries:

| Boundary | Critical % | Passes ≤5%? |
| -------- | ---------- | ----------- |
| 0.75     | 39.1%      | FAIL        |
| 0.90     | 27.1%      | FAIL        |
| 0.95     | 12.0%      | FAIL        |
| 0.99     | 2.3%       | PASS        |

A boundary of ~0.99 would meet the 5% target, but this essentially means "near-certain burnout" — a very narrow definition of Critical.

**Options:**

- A) Raise Critical boundary to ~0.99 — meets 5% target, very narrow Critical definition
- B) Raise Critical boundary to 0.90 — still fails (27%), but more meaningful boundary
- C) Revisit the 5% target — the Kaggle dataset may have higher base rates than production HRIS data
- D) Model improvement — better feature engineering to produce more calibrated probabilities

## Finding 4: Senior Population Is 100% Positive

All 531 senior employees (Designation ≥ 4, i.e. Lead + Manager) in the test set have Burn Rate ≥ 0.45. Threshold B floors (5-6) pass vacuously — there are zero negative cases to falsely flag or miss.

**Implication:** Threshold B cannot be validated on the Kaggle dataset. The D18 pre-commitment "Threshold B senior validation on HRIS data" is the only path to real validation — the Kaggle dataset has no senior non-burnout cases.

## Relationship Between Failures

All three failures share a root cause: the model produces high, confident probabilities for a large portion of employees. This inflates FP rate at 0.30, pushes most employees above 0.75, and concentrates SHAP importance on the strongest single predictor (MFS). The 12-row model was too small to reveal these patterns.

## Immediate Options

| Path                    | What it does                         | Risk                        |
| ----------------------- | ------------------------------------ | --------------------------- |
| Raise threshold to 0.35 | Fixes FP floor, within drift range   | Doesn't fix MFS or Critical |
| Expand features         | Dilutes MFS, may improve calibration | Requires data engineering   |
| Accept and document     | Ship with caveats                    | D16 gate violated, DPO risk |

## For Discussion

1. The MFS SHAP gate at 40% fails by 6.9pp. Should we expand the feature set before deployment, or accept MFS dominance with documented rationale? What features could dilute MFS importance?

2. Threshold A at 0.35 passes both FP and FN floors but sits at the drift boundary. Is 0.35 stable enough, or should we target 0.40 for more margin?

3. The Critical tier target of ≤5% requires a ~0.99 boundary on this dataset, making Critical "near-certain burnout." Does this align with the product intent, or should the 5% target be revisited after HRIS validation?
