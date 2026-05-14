---
type: DECISION
date: 2026-05-14
created_at: 2026-05-14T11:00:00+08:00
author: human
phase: analyze
topic: Phase 5 model pick — Random Forest confirmed as Sprint 1 model
tags:
  [
    phase5,
    model-selection,
    random-forest,
    sprint-1,
    threshold,
    dpo-gate,
    escalation,
  ]
---

# DECISION D17: Random Forest Confirmed as Sprint 1 Model

## Pick

Random Forest. Confirmed.

Rationale (founder's words): "Random Forest was picked not because it won cleanly but because it was the only candidate that told the truth about what it was doing — using three signals roughly equally to describe a three-dimensional problem. The other candidates either collapsed to one signal or collapsed to one row."

## Four-Tier Escalation Architecture — Locked

The escalation path is the product's ethical architecture expressed as a decision tree. It does not change in Phase 6.

| Tier     | Employee sees                 | HR sees                  | Manager sees    | Action                                                                                                   |
| -------- | ----------------------------- | ------------------------ | --------------- | -------------------------------------------------------------------------------------------------------- |
| LOW      | Own trend                     | Nothing                  | Nothing         | None                                                                                                     |
| MODERATE | Own score + matched resources | Nothing                  | Nothing         | Resources surfaced to employee only                                                                      |
| HIGH     | Own score + resources         | Team aggregate           | Check-in prompt | Identity protected unless employee shares                                                                |
| CRITICAL | Own score + resources         | Escalation with reviewer | Escalation      | Human review gate mandatory (D8 EU AI Act). Individual visible to reviewer only. Sign-off before action. |

## DPO Hard Gate

Sprint 1 does not deploy to a real customer until the SHAP output format has been reviewed and approved by a qualified legal or data protection professional.

This is the product's primary defence against the most likely litigation scenario: an employee whose score influences an employment decision they did not consent to.

Not optional. Not deferrable to Sprint 2.

## Provisional Threshold

0.30 confirmed as Sprint 1 operating threshold on this sample.

Pre-registered drift tolerance: ±0.05 from 0.30. When the full dataset cost curve is produced, if the cost minimum is within 0.25–0.35 the threshold stays at 0.30. If outside, threshold moves and the decision is recorded with new cost rationale.

Pre-registering prevents opportunistic threshold movement after seeing full dataset numbers.

## Pre-Commitments Carried to Phase 6

1. Full sweep re-run on Kaggle dataset — RF must beat naive baseline
2. LR artifact resolution on full dataset
3. RF MFS SHAP re-check — must stay below 40%
4. Threshold selection with ±0.05 drift tolerance
5. Gender fairness audit using Gender as audit variable
6. XGBoost Sprint 2 re-entry on behavioral features
7. RF SHAP balance check — at least three features, none above 40%

## Alternatives Considered

- Logistic Regression — perfect separation artifact, real performance unknown
- XGBoost — disqualified per D16a, fatigue detector
- Naive Baseline — flags everyone, does not scale

## Consequences

1. Random Forest is the Sprint 1 production model
2. Phase 6 validates on full Kaggle dataset with pre-registered parameters
3. DPO review gates first customer deployment
4. Four-tier escalation architecture is locked through Sprint 1
5. Threshold 0.30 provisional with pre-registered drift tolerance

## For Discussion

1. Should the DPO review cover only the SHAP output format, or also the employee-facing risk tier explanation?
2. If Random Forest SHAP concentrates above 40% on one feature in the full dataset — does Sprint 1 stop, or does the concentration get investigated while the pipeline continues?
3. Is the ±0.05 drift tolerance tight enough for a two-threshold serving system, or should each threshold (general / senior) have its own drift tolerance?
