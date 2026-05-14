---
type: DECISION
date: 2026-05-14
created_at: 2026-05-14T10:00:00+08:00
author: human
phase: analyze
topic: XGBoost MFS flag disposition — disqualification from Sprint 1 candidate pool
tags:
  [
    phase4,
    xgboost,
    disqualification,
    mfs-shap,
    sprint-1,
    sprint-2,
    model-selection,
  ]
---

# DECISION D16: XGBoost Disqualified from Sprint 1 — MFS 97.4%

## D16a: XGBoost Disqualified from Sprint 1

XGBoost is disqualified from Sprint 1 Phase 5 candidate selection.

MFS SHAP = 97.4% of total importance. One feature accounts for 97.4% of all predictive weight. The model is a fatigue threshold with extra steps, not a burnout classifier.

The early warning use case requires detecting burnout before fatigue becomes visible. A fatigue-only model misses employees with moderate fatigue but high workload, low autonomy, and declining engagement until fatigue spikes — the lagging indicator problem Phase 3 flagged.

The duty-of-care positioning (D11 Nuance 5) requires the model to be defensible to a General Counsel or Chief Risk Officer. A single-feature threshold is not defensible as an ML product — it is a rule. A rule does not justify the governance architecture, SHAP audit trails, or two-threshold operating system (D11, D14).

## D16b: XGBoost Re-enters Sprint 2 on Expanded Features

XGBoost is not permanently disqualified. It is disqualified on this feature set.

Sprint 2 adds project management integration (D9 Option 2) — Jira/Linear/Asana workload signals at team-aggregate level. Those features are orthogonal to Mental Fatigue Score: they measure what the workload IS, not how the employee FEELS about it.

On a richer feature set, MFS dominance should dilute below 40% because the model has genuinely informative alternatives.

Sprint 2 pre-commitment: re-run Phase 4 candidate sweep with behavioral feature layer. XGBoost MFS SHAP must be below 40% before it enters Phase 5 candidate selection.

## D16c: Logistic Regression Perfect Separation Flag

Logistic Regression achieves AUC=1.000 on 13 rows via perfect separation on tenure_days alone (100% SHAP). This is a small-data artifact — a spurious boundary that accidentally splits this tiny dataset.

Logistic Regression remains in the candidate pool with this flag recorded. Real performance is unknown until evaluated on the full Kaggle dataset (~22,750 rows). On the full dataset, perfect separation will not hold.

## D16d: Phase 1 XGBoost Pre-Selection Revoked

Phase 1 pre-selected XGBoost as the product model. That pre-selection is revoked by this finding.

Pre-selections made before data audit, feature framing, and model training are hypotheses. This one did not survive contact with the actual dataset.

Record: Phase 1 pre-selection of XGBoost revoked at Phase 4. Reason: 97.4% MFS SHAP dominance disqualifies the model from Sprint 1 candidate set. XGBoost remains a candidate for Sprint 2 on expanded feature set (D16b).

## Honest State of Phase 4 on 13 Rows

| Model               | Status              | Signal                                                          |
| ------------------- | ------------------- | --------------------------------------------------------------- |
| XGBoost             | DISQUALIFIED        | Fatigue detector, not burnout detector                          |
| Logistic Regression | CANDIDATE (flagged) | Perfect separation is 13-row artifact; real performance unknown |
| Random Forest       | CANDIDATE           | 25.3% MFS SHAP, most balanced profile, passes all checks        |
| Naive Baseline      | BASELINE            | The floor                                                       |

Phase 5 on this dataset will recommend Random Forest by elimination as much as by merit. Stated clearly, not buried.

## Consequences

1. Sprint 1 model selection proceeds with Random Forest and Logistic Regression as candidates
2. XGBoost results remain on leaderboard (disqualified row, not removed — hiding data serves no one)
3. Sprint 2 must re-run full Phase 4 sweep with behavioral features before XGBoost re-enters
4. Cost table for Phase 5 covers CANDIDATE rows only
5. Phase 1 documentation referencing XGBoost as product model must be updated

## For Discussion

1. At what sample size does the Random Forest recommendation gain sufficient statistical backing — is the full Kaggle dataset enough, or does it require real deployment data?
2. Should Sprint 2 expand the candidate pool beyond the three families tested here (e.g., gradient-boosted alternatives like LightGBM)?
3. If Random Forest MFS SHAP exceeds 40% on the full dataset, does it face the same disqualification standard, or does the balanced 13-row profile earn it a higher burden of proof?
