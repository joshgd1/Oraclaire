---
type: DECISION
date: 2026-05-13
created_at: 2026-05-13T22:00:00+08:00
author: human
phase: analyze
topic: Horizon reframe — classification not prediction. Cross-sectional data cannot support a predictive horizon claim.
tags:
  [horizon, classification, prediction, cross-sectional, validation, framing]
---

# CHALLENGE D4: Horizon Reframe — Classification, Not Prediction

## Decision

Oraclaire is a **classification** product, not a predictive product.

- The model classifies each employee's **current** burnout risk tier at each assessment cycle
- The output informs interventions for the inter-cycle window (draft: 30 days)
- The following cycle's classification measures whether the risk tier improved, held, or worsened
- The "horizon" is the assessment recalibration window — not a prediction window

This replaces the original 30-day predictive horizon ("risk over the next 30 days") with a classification framing ("risk state at this assessment cycle, informing interventions for the next cycle").

## Alternatives Considered

1. **30-day predictive window (original draft)** — Rejected. Claims longitudinal predictive validity that a cross-sectional MBI survey dataset cannot support. The enterprise intervention cycle alone exceeds 30 days. The claim would not survive scrutiny from a methods-aware reviewer.

2. **A different prediction window (14, 60, or 90 days)** — Rejected. All prediction window claims have the same underlying problem: they require temporal validation data. Changing the number does not fix the data limitation. The Kaggle dataset is cross-sectional — it measures burnout at a single point in time, not burnout trajectories.

3. **Keep prediction framing but add a disclaimer ("preliminary, not longitudinally validated")** — Rejected. A disclaimer does not fix a framing error. It signals awareness of the problem without solving it. The honest approach is to choose the framing the data supports.

4. **"We will add longitudinal prediction in a future version"** — Rejected. Future roadmap claims in an MBA submission are not evaluated. Only what the current product does is evaluated. Making claims about future capability is aspirational padding.

## Chosen Approach

Reframe as classification. The model classifies current burnout severity from single-timepoint survey data — this is exactly what the best-performing burnout ML models in the literature do (research §3.1: MBI-based models classify current burnout severity, not future onset). The classification informs the next cycle's intervention decisions. Trajectory analysis (improved / held / worsened across cycles) replaces prediction as the temporal dimension.

## Rationale

Three specific problems with the 30-day predictive framing:

**Problem 1 — Too short to be actionable.** A manager who receives a burnout alert needs to: have a 1:1, escalate to HR, design an intervention, see whether it worked. 30 days is not enough. The user personas file confirms the enterprise cycle alone is 6–9 months.

**Problem 2 — False precision claim.** The market landscape warned that "4-8 weeks before critical threshold" requires longitudinal validation data. 30 days is the same trap. Claiming predictive power from cross-sectional data is a claim that will not survive a single question.

**Problem 3 — Literature does not support it.** The best burnout ML models in the literature are trained on single-timepoint MBI data. They classify current severity. They do not predict future state.

The classification framing is actually **stronger** than the prediction framing because it can be defended: "We classify current burnout risk with XGBoost and SHAP — accurately, transparently, and without claiming to predict the future from data that cannot support that claim" is more credible than "we predict burnout 30 days before it happens."

## Trade-offs Accepted

- **The product sounds less impressive in a one-line pitch.** "We detect burnout before it happens" is catchier than "we classify current burnout risk." This is acceptable because the impressive claim was indefensible.
- **Trajectory analysis (across cycles) is still a form of temporal reasoning** — just not within a single cycle. The model doesn't predict, but the product does track change over time. This distinction must be communicated clearly to avoid the perception that trajectory tracking is prediction under another name.
- **Some competitors (Viva Insights) have behavioral time-series data** (calendar patterns, email volume over time) that genuinely supports prediction. Oraclaire, with survey-based data, does not have this advantage. The classification framing acknowledges this competitive gap honestly.

## What This Gives the Decision Log

This is one of the strongest entries because it demonstrates:

1. Caught a framing error before it became a methodology error
2. Connected the data limitation (cross-sectional dataset) to the product claim (predictive horizon)
3. Chose intellectual honesty over a more impressive-sounding claim
4. Reframed the product more accurately without weakening the value proposition

## For Discussion

1. Should the frame explicitly name which competitors DO have predictive capability (Viva Insights with behavioral time-series), and differentiate Oraclaire as "accurate current-state classification with transparent explanations"?
2. If Oraclaire later adds behavioral signals (calendar patterns, communication frequency), should the frame be revisited to upgrade from classification to prediction — or is the classification framing a permanent product identity?
3. How does classification-only framing affect the marketing narrative? Is "burnout risk scoring" (classification) as compelling as "burnout prediction" — and if not, what's the right positioning language?
