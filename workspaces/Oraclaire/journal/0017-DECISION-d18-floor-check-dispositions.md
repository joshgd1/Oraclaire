---
type: DECISION
date: 2026-05-14
created_at: 2026-05-14
author: human
phase: analyze
topic: Phase 6 floor check dispositions — four pass, one marginal accepted, two pending, one pipeline integrity finding raised
tags:
  [
    phase6,
    floor-checks,
    brier,
    fp-ceiling,
    fn-target,
    threshold,
    fakeEMP_007,
    pipeline-integrity,
  ]
---

# DECISION D18: Phase 6 Floor Check Dispositions

Title: "Four checks pass, one marginal accepted, two pending full dataset — proceed to deployment architecture"

## Check Dispositions

### Check 1 — Brier 0.0712 vs 0.15

ACCEPTED — PASS confirmed.

0.0712 is well below the floor. No Platt scaling required on this sample.

Standing instruction for the full dataset run: if Brier exceeds 0.15 on 22,750 rows — stop. Apply Platt scaling. Recheck before threshold selection proceeds. This is not a judgement call at that point — it is an automatic gate.

### Check 2 — FP Rate 20% vs 15% Ceiling

ACCEPTED — MARGINAL noted and condition set.

1 out of 5 negatives is not a meaningful FP rate. It is one borderline employee (EID_012, BR=0.42) whose Burn Rate sits just below the 0.45 binarisation threshold and whose RF probability sits at 0.57 — well above the 0.30 operating threshold.

EID_012 is the hardest classification in this dataset. BR=0.42 is genuinely ambiguous — below the burned-out label threshold but not by much. The model flagging this employee at 0.57 probability is not a failure. It is the model doing what it should do on a borderline case.

Not moving the threshold to avoid this FP. Moving to 0.60 to exclude EID_012 would miss EID_001 (BR=0.45, RF=0.31) — a genuinely burned-out employee caught only because the threshold is at 0.30.

Accepting EID_012 as a FP at $15 cost to protect against missing EID_001 at $4,000 cost is the correct asymmetric decision.

Condition set for full dataset: FP rate on High/Critical must be recalculated on the full 22,750-row dataset with proper population denominators — not 5 negatives. If it exceeds 15% on the full dataset: consider raising the operating threshold within the ±0.05 drift tolerance. Do not move threshold above 0.35.

Pre-commitment added: "Check 2 full dataset: recompute FP rate on negative population of full dataset at threshold 0.30. If above 15% — adjust within ±0.05 drift tolerance (max threshold 0.35). EID_012 analog cases at BR=0.40-0.45 are expected and accepted at $15 FP cost."

### Check 3 — FN Rate 0% vs 15% Target

ACCEPTED — PASS confirmed.

Zero false negatives at threshold 0.30 on this sample. All eight burned-out employees correctly identified.

Note for full dataset: 0% FN on 13 rows will not hold on 22,750 rows. The target is below 15% — not zero. The full dataset will produce a more realistic FN rate. That is expected and acceptable.

### Check 4 — Senior Tier FN 0% vs 10% Target

ACCEPTED — PASS with caveat.

Zero FN across all employees means zero senior FN. The pass is technically correct.

Caveat: the 13-row sample does not have a validated seniority split. seniority_tier was added as a schema field in D15 but the Kaggle source data does not carry it. The senior tier threshold (Threshold B) cannot be properly validated until the full dataset is run with real seniority labels.

Pre-commitment added: "Check 4 full dataset: validate Threshold B separately on the senior sub-population once seniority_tier field is populated from HRIS or self-reported data at deployment. 13-row validation is structural only — not a performance claim."

### Check 5 — Drift Tolerance Pending

PENDING confirmed. No decision yet.

The full Kaggle dataset is not on disk. Pre-commitment 4 and Check 5 both depend on it. Both stay pending until the dataset is available.

This does not block deployment architecture. The pipeline is validated. The model is selected. The thresholds are pre-registered. What is pending is the production validation run — which happens when the first real customer deploys.

## Finding F1 — Pipeline Integrity: fakeEMP_007

fakeEMP_007 appears in the Phase 4 prediction table with BR=0.60, label=1, RF prob=0.85, result=TP.

This row was flagged in Phase 2 Finding 3. The Phase 2 disposition log records:

- Finding 1: "EXCLUDE row 14 (fakeEMP_007 duplicate) — kept row 7" — only the duplicate was excluded
- Finding 3: "FLAG — resolved by Finding 1 exclusion. Note: fakeEMP\_ prefix rows excluded immediately in real Kaggle dataset." — the flag was noted but the original was kept

The flag was treated as resolved because the duplicate was excluded. The original fakeEMP_007 remained in `data/processed/train_clean.csv`.

Resolution applied: fakeEMP_007 removed from `data/processed/train_clean.csv`. Row count dropped from 13 to 12.

This means Phase 4 was run on 13 rows including one contaminated row. The leaderboard results (AUC, Brier, SHAP, cost table) were produced with fakeEMP_007 in the training data. On 12 clean rows the results will differ slightly. The full dataset re-run (Phase 6) will be on clean data and supersedes the 13-row results.

This is a data pipeline integrity finding — not a model performance finding. The model's prediction on fakeEMP_007 is not the issue. The issue is that the row survived Phase 2 exclusion when it should not have.

Todo added: "Verify fakeEMP_007 exclusion was applied to data/processed/train_clean.csv. RESOLVED — row removed, 13→12 rows. Phase 4 13-row results are now known to contain one contaminated row. Full dataset re-run supersedes."

## Consequences

1. Four floor checks pass or are accepted — deployment architecture may proceed
2. Two checks pending full dataset — do not block deployment architecture
3. fakeEMP_007 removed from clean dataset — Phase 4 results are contaminated on one row
4. Full dataset re-run will be on clean data and supersedes all 13-row results
5. Three new pre-commitments added for full dataset validation (Check 2 FP rate, Check 4 senior tier, Check 5 drift tolerance)

## For Discussion

1. Should the 13-row Phase 4 leaderboard be re-run on 12 clean rows before deployment architecture, or is the full dataset re-run sufficient to supersede?
2. Does the fakeEMP_007 contamination affect the D17 model selection (Random Forest), or is the pick robust enough that removing one row from 13 would not change the outcome?
3. Should Finding F1 trigger a full Phase 2 re-audit of the disposition log to check for other exclusions that were noted but not applied?
