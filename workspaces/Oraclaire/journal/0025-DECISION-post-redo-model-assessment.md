---
type: DECISION
date: 2026-05-14
created_at: 2026-05-14T16:30:00+10:00
author: human
session_id: resume-post-clear
session_turn: 4
project: Oraclaire
topic: MFS RE-DO successful — FP breach persists, threshold drift tolerance formally exceeded
phase: redteam
tags:
  [
    D16-gate,
    D18,
    threshold-calibration,
    MFS-REDO,
    interaction-terms,
    drift-tolerance,
  ]
---

# Decision D25 — Post-RE-DO Model Assessment

**Title:** MFS RE-DO successful — FP breach persists, threshold drift tolerance formally exceeded, new decision required

---

## MFS Gate: CONFIRMED PASS

MFS SHAP reduced from 46.9% to 29.9%. Interaction features `tenure_fatigue` (30.3%) and `tenure_workload` (17.0%) share the load with MFS (29.9%). No single feature dominates. SHAP waterfall hard gate lifted.

**Record:** "MFS RE-DO successful. Interaction features tenure_fatigue and tenure_workload added to feature set. MFS SHAP reduced from 46.9% to 29.9%. 40% gate passes. SHAP waterfall hard gate lifted."

## BR=0.84 Employee: ACCEPTED as Known Outlier

Probability moved from 0.34 to 0.3736. Still caught at threshold 0.30. The other 37 employees with BR ~0.84 all score 0.91-0.998. This one employee is a genuine outlier — likely a case where feature values do not match the burnout label in ways the model cannot resolve.

**Note for product documentation:** "A small number of employees may have burnout signals not captured by the current feature set. Sprint 2 behavioral features are designed to address this."

## Threshold Decision: PROVISIONAL 0.40

The corrected model at 0.30 still produces 21.1% FP — above the 15% ceiling and above the participation decay threshold (D5). At 0.40, both FP (12.1%) and FN (12.1%) pass pre-registered floors.

0.40 exceeds the ±0.05 drift tolerance from D17/D18. Exceeding requires a new cost rationale — which is:

1. At 0.30, corrected model produces 21.1% FP — above 15% ceiling and above D5 participation decay threshold
2. At 0.40, both FP and FN pass floors — the floor system was designed to find this threshold
3. The drift tolerance was pre-registered to require a new decision at this point — this IS that decision

**Condition:** band review confirms no Burn Rate ≥ 0.60 employees in the 0.30-0.40 range on the corrected model.

**Formal record:** "Threshold A moved from 0.30 to 0.40. This exceeds the pre-registered drift tolerance of ±0.05 from D17 and D18. New cost rationale: at 0.30 the corrected model produces 21.1% FP rate — above the pre-registered 15% ceiling and above the participation decay threshold from D5. At 0.40 both FP (12.1%) and FN (12.1%) pass pre-registered floors. The drift tolerance was pre-registered to require a new decision at this point — this is that decision."

## Execution Sequence

1. Show 0.30-0.40 probability band on corrected model (count, Burn Rate distribution, any ≥ 0.60)
2. User confirms 0.40 or revises
3. Update config.py: THRESHOLD_A = 0.40, THRESHOLD_B = 0.40
4. Run full Phase 7 sweeps on corrected model at threshold 0.40

## For Discussion

1. The drift tolerance was exceeded with explicit cost rationale. Should this set precedent for future threshold adjustments, or should each exceedance carry its own D-number and rationale?

2. The corrected model's FP rate at 0.35 is 16.6% — still above 15%. Would a future calibration (Platt scaling, per D18 Brier check) potentially bring 0.35 below the ceiling, making the 0.40 move unnecessary?

3. The interaction terms increased feature count from 8 to 10. Should SHAP waterfall display show the interaction terms directly, or roll them back into their parent features for employee-facing explanations?
