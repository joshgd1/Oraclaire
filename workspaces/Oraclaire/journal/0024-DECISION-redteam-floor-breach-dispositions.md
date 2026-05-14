---
type: DECISION
date: 2026-05-14
created_at: 2026-05-14T15:45:00+10:00
author: human
session_id: resume-post-clear
session_turn: 3
project: Oraclaire
topic: Three floor breaches dispositioned — RE-DO, MITIGATE, ACCEPT
phase: redteam
tags:
  [D16-gate, D18, D20, threshold-calibration, critical-boundary, MFS-dominance]
---

# Decision D24 — Red-team Floor Breach Dispositions

**Title:** Three floor breaches dispositioned — one RE-DO, one MITIGATE pending band review, one ACCEPT with boundary change

Dispositions for the three D23 findings from the full 21,626-row Kaggle dataset re-run.

---

## Disposition 1: MFS SHAP 46.9% — RE-DO

46.9% is not borderline. The pre-registered D16 gate at 40% exists for this moment. The 12-row sample showed 19.4%; the full dataset shows 46.9%. The sample misled. The full dataset is the truth.

The D16 principle: a model where one feature dominates is not a burnout model. That principle does not change at 46.9%.

**RE-DO sequence:**

Round 1 — Interaction terms:

- `tenure_fatigue = tenure_days × mental_fatigue_score`
- `tenure_workload = tenure_days × resource_allocation`
- Capture what MFS alone misses — moderate fatigue + high workload + short tenure is a different risk profile from moderate fatigue alone.
- Retrain. Check MFS SHAP. If below 40% — done.

Round 2 — If Round 1 fails: tenure_bucket (categorical: 0-180 / 181-540 / 541+ days). Non-linear tenure effects may absorb MFS weight. Retrain. If below 40% — done.

Round 3 — If Round 2 fails: dataset limitation. Kaggle burnout dataset is dominated by fatigue signal. No feature engineering on this dataset will fix it. Sprint 2 behavioral features (D9 Option 2 — Jira/Linear/Asana) are the structural fix. Document as Sprint 2 gate: "Oraclaire cannot claim multi-dimensional burnout detection until behavioral features dilute MFS below 40%."

**Hard gate:** Do not ship the employee-facing SHAP waterfall until MFS is below 40%. An employee who receives a fatigue-dominant explanation and correctly identifies it as circular will lose trust in the product.

---

## Disposition 2: FP Rate 20.1% at Threshold 0.30 — REVISED: KEEP at 0.30

**Original disposition:** MITIGATE — raise to 0.35 pending band review.
**Revised after band data:** NOT 0.35. Keep Threshold A at 0.30.

**Why the band data changes the call:**

The pre-condition was: "If any have Burn Rate above 0.60 — raising to 0.35 misses genuinely burned-out employees at $4,000 to $21,000 cost. That changes the decision."

The band data shows:

- 5 employees with Burn Rate ≥ 0.60
- 1 employee with Burn Rate 0.84
- 61 elevated employees total in the 0.30-0.35 band

The pre-condition fired. The decision changes.

**The real problem the band data reveals:**

The 1 employee with Burn Rate 0.84 has RF probability 0.34. That is not a threshold problem — that is a model problem. A genuinely severely burned-out employee should not produce RF probability 0.34. This is the MFS dominance problem (Finding 1) expressing itself in the threshold decision. A fatigue-dominant model produces high confidence on employees who report high fatigue — regardless of actual burnout severity. An employee who is severely burned out (0.84) but has not yet reported high fatigue gets probability 0.34.

Raising the threshold from 0.30 to 0.35 does not fix this. The threshold cannot compensate for a model that lacks the signal to detect this employee. That is a feature problem, not a threshold problem.

**Rationale for keeping 0.30:**

0.30 catches the BR=0.84 employee at probability 0.34 — barely, but it catches them. 0.35 misses them. At $4,000 to $21,000 FN cost, the asymmetry does not justify the move.

The FP cost at 0.30 is 20.1% — above the 15% pre-registered ceiling. Breach ACCEPTED with this rationale:

"Threshold A FP ceiling breach accepted at 0.30. The alternative (0.35) misses 61 elevated employees including 5 with Burn Rate ≥ 0.60 and 1 with Burn Rate 0.84 at RF probability 0.34. At D3 FN costs of $4,000-$21,000 per missed employee the cost of missing these 61 outweighs the cost of 113 false positive check-ins at $15 each ($1,695 total FP cost vs $244,000-$1,281,000 FN cost). The FP ceiling breach is documented. The threshold stays at 0.30 until the MFS RE-DO produces a model that can detect the BR=0.84 employee with higher confidence — at which point the threshold decision is revisited."

**What the floor decision reveals about the floor:**

The 15% FP ceiling was set to prevent participation decay (D5: above 20% FP rate, trust erosion begins). We are at 20.1% — at the margin, not catastrophically above it. The participation decay risk at 20.1% is real but not immediate. The FN cost of moving to 0.35 is immediate and quantified.

**Correct response:**

1. Keep 0.30 now
2. Fix the model (RE-DO Finding 1)
3. After MFS RE-DO — recheck FP rate on corrected model
4. A model that detects the BR=0.84 employee with higher confidence will produce a different threshold curve — one where 0.35 may pass the FP ceiling without missing the elevated employees

The threshold decision and the model RE-DO are not independent. Fixing the model first may resolve the threshold problem without requiring a floor breach acceptance.

---

## Disposition 3: Critical Tier 39.1% at 0.75 — ACCEPT with boundary change to 0.90

39.1% at 0.75 is not a model failure. It is the Kaggle dataset skewing toward burned-out employees — collected specifically because burnout was the research question. Not a representative workplace population.

The 5% ceiling from D14 was calibrated against a typical workplace deployment. On a burnout-overrepresented dataset, 5% at 0.75 is not achievable.

**Why 0.90 not 0.99:** 0.99 makes Critical mathematically near-impossible. The human review gate (D8) would almost never fire. A gate that never fires is a compliance checkbox. 0.90 means the model is highly confident — not certain. On a real deployment, ≥ 0.90 is genuinely alarming.

**Action:** Update `config.py` TIER_BOUNDARIES critical from (0.75, 1.00) to (0.90, 1.00).

**Record:** "Critical boundary raised from 0.75 to 0.90. Reason: Kaggle dataset skews toward burned-out population — not representative of typical workplace deployment. 0.90 boundary produces a Critical tier that fires on genuinely alarming predictions without becoming a compliance checkbox. The 5% ceiling from D14 will be validated on first real customer deployment with representative workforce data."

---

## Disposition 4: Senior Population 100% Positive — ACCEPT

Anticipated. D18 Check 4 was already marked PENDING — requires HRIS data. Threshold B cannot be validated on the Kaggle dataset.

**Condition:** Threshold B validation is a Sprint 2 exit criterion. Oraclaire cannot make performance claims about senior-tier detection until validated on a real customer deployment with genuine HRIS seniority data. This belongs in the product's honest capability statement — not buried in a pre-commitment.

---

## Summary

| #   | Finding                | Disposition                                    |
| --- | ---------------------- | ---------------------------------------------- |
| 1   | MFS 46.9%              | RE-DO: interaction terms first                 |
| 2   | FP 20.1% at 0.30       | ACCEPT breach — keep 0.30, revisit after RE-DO |
| 3   | Critical 39.1% at 0.75 | ACCEPT: raise boundary to 0.90                 |
| 4   | Senior 100% positive   | ACCEPT: Sprint 2 gate                          |

## Execution Sequence

1. ~~Show 0.30-0.35 probability band employees~~ DONE — band data changed decision
2. ~~User confirms 0.35 or revises~~ DONE — revised to KEEP 0.30
3. Update config.py: THRESHOLD_A stays 0.30, TIER_BOUNDARIES critical = (0.90, 1.00)
4. RE-DO: engineer interaction terms, retrain, report MFS SHAP + BR=0.84 employee probability + FP/FN at 0.30
5. If MFS < 40% AND BR=0.84 probability > 0.50: model fixed — recheck FP rate, may resolve floor breach
6. If MFS ≥ 40% after Round 2: document as Sprint 2 gate, ship with SHAP waterfall suppressed

## For Discussion

1. The RE-DO sequence has three rounds with escalating intervention. Should Round 3 (Sprint 2 gate) also carry a hard commitment to behavioral feature timeline, or remain open-ended?

2. The Critical boundary at 0.90 produces ~27% Critical on the Kaggle dataset. At first real customer deployment, this ratio will shift. Should the 5% D14 ceiling be re-validated after the boundary change, or does the 0.90 boundary itself satisfy the D14 intent regardless of ratio?

3. The hard gate on SHAP waterfall suppression means the employee dashboard ships without per-feature explanations until MFS < 40%. Is the tier label + resources sufficient for the MVP employee experience, or does the waterfall need a replacement explanation format?
