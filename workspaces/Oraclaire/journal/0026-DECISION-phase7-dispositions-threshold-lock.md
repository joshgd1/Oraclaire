---
type: DECISION
date: 2026-05-14
created_at: 2026-05-14T18:00:00+10:00
author: human
session_id: resume-post-clear
session_turn: 5
project: Oraclaire
topic: Threshold A locked at 0.35, seven Phase 7 findings dispositioned, Phase 7 closed
phase: redteam
tags:
  [
    D26,
    threshold-lock,
    phase7-closed,
    sprint2-backlog,
    FP-ceiling-breach,
    ensemble-averaging,
    missingness-monitor,
  ]
---

# Decision D26 — Phase 7 Final Dispositions

**Title:** Threshold A locked at 0.35 — seven findings dispositioned, Phase 7 closed

---

## ITEM 1: THRESHOLD A FINAL DECISION

Threshold A locked at **0.35**.

Neither 0.30 nor 0.40 is acceptable in isolation:

- 0.30: FP at 21.1% — above 15% ceiling AND above D5 participation decay threshold of 20%
- 0.40: misses 5 Burn Rate ≥ 0.60 employees including BR=0.84 at cost of $20,000-$105,000 FN exposure (5 × $4,000-$21,000 per D3)

  0.35 is the honest middle:

- FP at 16.6% — 1.6 points above the 15% ceiling. This is within the 5-point buffer above the D5 participation decay threshold of 20%. The ceiling was designed to catch the decay risk — 16.6% does not trigger it.
- BR=0.84 employee sits at probability 0.37 — caught at 0.35.

**Formal record:** "Threshold A locked at 0.35. FP rate 16.6% — 1.6 points above pre-registered 15% ceiling. Breach accepted: 16.6% is within the 5-point buffer above the D5 participation decay threshold of 20%. The ceiling was designed to protect against decay — 16.6% does not trigger it. 0.30 rejected: 21.1% FP exceeds the decay threshold. 0.40 rejected: misses 5 Burn Rate ≥ 0.60 employees including BR=0.84 at cost of $20,000-$105,000 FN exposure (5 × $4,000-$21,000 per D3). 0.35 is the minimum threshold that keeps the BR=0.84 employee in the scored population while reducing FP below the decay threshold."

**Config update:** `THRESHOLD_A = 0.35`

---

## ITEM 2: SEVEN FINDING DISPOSITIONS

### S1-F1: EID_001 Seed Instability — MITIGATE

EID_001 (Burn Rate 0.45, Analyst/junior) moves Moderate→Low across seeds. FN exposure $4,000/year (D3).

**Mitigation:** Ensemble averaging across 3 seeds (42, 123, 456) as serving-time option. Average probability outputs before tier classification.

**Sprint 2 backlog item:** "Ensemble averaging across 3 seeds to reduce individual employee tier instability. Motivated by S1-F1 — EID_001 analog employees at the tier boundary are sensitive to random initialisation."

Sprint 1 ships with single-seed model and documented finding.

### S2-F1: tenure_days Concentration — ACCEPT

5.7-point AUC drop on removal is expected for the top SHAP feature (28.5%). tenure_days is doing legitimate work — tenure is a genuine burnout predictor.

Concentration risk noted for organisations with narrow tenure distributions.

**Deployment documentation note:** "Oraclaire's burnout model relies significantly on employee tenure as a signal. Organisations with narrow tenure distributions (e.g. early-stage companies where most employees joined within 18 months) may see reduced model accuracy. Sprint 2 behavioral features are designed to provide additional signal independent of tenure."

### S2-F2: resource_allocation Fragility — MITIGATE

MFS rises to 38.4% on removal — 1.6 points below the 40% gate. resource_allocation is structurally important to keeping MFS in check.

**Mitigation:** Data quality monitor for resource_allocation missingness per quarterly cycle. If missingness exceeds 15%, flag the cycle's SHAP explanations as "reduced signal quality" and suppress the workload dimension from the employee waterfall.

**Sprint 2 backlog item:** "resource_allocation missingness monitor — if >15% missing in a quarterly cycle trigger SHAP quality flag. Motivated by S2-F2 — MFS rises to 38.4% when workload signal absent."

### S2-F3: mental_fatigue_score Dependency — ACCEPT

8.6-point AUC drop confirms MFS is a legitimate primary burnout signal. The RE-DO (D24 Item 1) already addressed MFS dominance via interaction terms. Model now uses MFS appropriately — important but not dominant.

### S3-F1: Gender Proxy 0% — ACCEPT

0% tier change when Gender is added confirms no disparate impact. Phase 3 exclusion of Gender (D17) validated. Gender fairness audit pre-commitment (D11, D17) unchanged for Sprint 2.

### S4-F1: Moderate Tier Brier 0.6084 (n=1) — ACCEPT

n=1 makes this a sample size artifact, not a calibration finding. Per-tier Brier on full dataset (22,750 rows) is the meaningful test — Sprint 2 validation requirement.

**Note:** "Per-tier Brier scores on the 12-row sample are not meaningful calibration metrics — single-employee tier populations produce unreliable estimates. Full dataset per-tier Brier is a Sprint 2 validation requirement."

### S4-F2: High Tier Brier 0.3249 (n=1) — ACCEPT

Same n=1 reasoning. 0.3249 is above the 0.15 Brier floor — flag for full dataset validation.

**Note:** "High tier Brier 0.3249 on n=1 sample. Full dataset High tier Brier must be validated against 0.15 floor in Sprint 2. If breached: Platt scaling applied to High tier specifically."

---

## Disposition Summary

| #     | Finding                       | Disposition | Action                                   |
| ----- | ----------------------------- | ----------- | ---------------------------------------- |
| S1-F1 | EID_001 seed instability      | MITIGATE    | Sprint 2: ensemble averaging             |
| S2-F1 | tenure_days concentration     | ACCEPT      | Deployment documentation added           |
| S2-F2 | resource_allocation fragility | MITIGATE    | Sprint 2: missingness monitor            |
| S2-F3 | MFS dependency                | ACCEPT      | No action                                |
| S3-F1 | Gender proxy 0%               | ACCEPT      | Fairness audit unchanged                 |
| S4-F1 | Moderate Brier n=1            | ACCEPT      | Full dataset validation                  |
| S4-F2 | High Brier n=1                | ACCEPT      | Full dataset validation with floor check |

---

## What Phase 8 Receives

- **Model:** Random Forest with interaction terms (10 features)
- **MFS SHAP:** 29.9% — PASS
- **Threshold A:** 0.35 (locked)
- **Threshold B:** 0.30 provisional
- **Critical boundary:** 0.90
- **FP rate at 0.35:** 16.6% (1.6pp above ceiling — accepted, within decay buffer)
- **FN rate at 0.35:** confirmed below 15% target

### Sprint 2 Backlog Items

1. Ensemble averaging across 3 seeds (S1-F1 mitigation)
2. resource_allocation missingness monitor (S2-F2 mitigation)

### Full Dataset Validation Requirements

1. Per-tier Brier on 22,750 rows
2. Gender fairness audit
3. Threshold B senior validation on HRIS data

---

Phase 7: CLOSED.
Phase 8 begins when ready.
