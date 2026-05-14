---
type: DECISION
date: 2026-05-13
created_at: 2026-05-13T23:30:00+08:00
author: human
phase: analyze
topic: Self-reporting strategy — Option 2 adopted as product vision, Option 1 as Sprint 1 build scope
tags:
  [
    self-reporting,
    behavioral-signals,
    sprint-scope,
    positioning,
    enterprise-buyer,
    MBI,
    CBI,
  ]
---

# DECISION D10: Self-Reporting Strategy

## Decision

Adopt Option 2 (augment self-reporting with project management integration) as the product vision. Ship Option 1 (self-reporting only, clinically validated instrument) as Sprint 1 scope. Reject Option 3 (reposition to HR consultants) entirely.

This is not a contradiction. Option 1 is the right answer for what can be built and validated now. Option 2 is the right answer for what Oraclaire needs to be commercially viable. Sprint 1 builds the validated foundation; Sprint 2 adds the causal layer.

## Sprint 1 Scope — Option 1 Foundation

- Primary signal: Copenhagen Burnout Inventory (free, validated, 19 items)
- Model: XGBoost trained on burnout dataset augmented with synthetic data
- SHAP explainability for every score
- Employee and HR dashboard
- Positioning: "We measure burnout — the subjective experience — using the instrument that measures it best. Viva Insights measures overwork. We measure burnout. They are not the same thing."

## Sprint 2 Vision — Option 2 Integration

- Jira / Linear / Asana connector at team-aggregate level only
- Output: workload-capacity gap analysis alongside SHAP burnout decomposition
- This answers "what is CAUSING the burnout" — not just "who has it"
- Timeline: 6-9 weeks post Sprint 1

## What Was Rejected

**Option 1 as permanent product position.** Reason: enterprise audit is correct. A survey-only product cannot answer "what is CAUSING the burnout" — only "who has it." The causal answer is where commercial value lives.

**Option 3 entirely.** Reason: HR consultant repositioning shrinks the addressable market and makes Oraclaire a precision instrument rather than a platform. Oraclaire is not a services business.

**Option 2 connectors in Sprint 1.** Reason: Sprint 1 scope is the scoring model, SHAP explainability, and dashboards. Adding three API integrations at this stage trades model quality and explainability depth for feature count. Wrong trade-off.

## Trade-Offs Accepted

A sophisticated buyer will ask "when does the Jira integration ship?" and Sprint 1 cannot demo it. This is acceptable because the decision log records the gap identified, the commercial implication understood, the solution designed, and the deliberate scope call made.

## Consequences

- Sprint 1 ships with a defensible scientific foundation but without the causal analysis layer that differentiates from Viva Insights
- The Sprint 1 positioning statement must distinguish burnout measurement from overwork detection without relying on features that don't exist yet
- The Sprint 2 connector work is now a documented commitment, not a "maybe later" — it must be resourced within 6-9 weeks of Sprint 1 completion

## Alternatives Considered

1. Ship Option 2 fully in Sprint 1 (rejected: wrong scope trade-off, delays model quality)
2. Option 1 as permanent position (rejected: commercially non-viable per enterprise audit)
3. Option 3 repositioning (rejected: abandons platform opportunity for services business)
4. Ship Option 2 connectors without the validated instrument (rejected: behavioral data alone cannot measure burnout — it measures overwork)

## For Discussion

1. If Sprint 1 validation shows CBI response rates below 40% at the first pilot, does that change the Option 2 timeline — or does it confirm the enterprise audit's warning about self-report dependency?
2. The Sprint 2 connector work assumes Jira/Linear/Asana APIs remain stable and accessible at team-aggregate granularity. What happens if Atlassian restricts API access (they have been tightening)? Is there a fallback behavioral signal that doesn't depend on a single vendor?
3. Counterfactual: if behavioral analytics were added first and the validated instrument second (reversing the build order), would the product be in a stronger or weaker position at the Series A pitch?
