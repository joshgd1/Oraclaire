---
type: DECISION
date: 2026-05-13
created_at: 2026-05-13T21:30:00+08:00
author: co-authored
phase: analyze
topic: FP cost includes participation decay, not just visible HR check-in cost
tags: [fp-cost, trust-erosion, participation, thresholds, precision]
---

# DECISION 2: FP Cost Anchors on Trust Erosion, Not Check-In Cost

## Decision

The false-positive cost in the Phase 1 frame includes a structural participation-decay term, not just the visible $15 HR check-in cost.

- **Visible FP cost:** $15 per false positive (30-min HR check-in at loaded labour cost)
- **Structural FP cost:** Participation decay. If FP rate exceeds 20%, participation drops an estimated 40–60% by the third assessment cycle (based on Microsoft Productivity Score 2020 backlash pattern)
- **Failure threshold:** If participation drops below 50%, the model's predictions become unreliable. The product has destroyed its own data collection.

**Effective FP cost:** $15 × (1 + participation_decay_multiplier)

This is not a clean dollar figure. It is a structural constraint on threshold selection: high precision is justified economically, not just ethically.

## Alternatives Considered

1. **FP cost = $15 only (visible cost)** — Rejected. The $15 is the tip of the iceberg. The real cost is the cascading data-quality loss. Ignoring it means threshold selection in Phase 5 will over-optimize for recall and destroy the product.

2. **FP cost = participation drop only (ignore dollar cost)** — Rejected. The check-in cost is real and measurable. Both terms matter.

3. **Quantify trust erosion as a specific dollar figure** — Rejected. No sourced data exists for a precise trust-erosion dollar amount. The participation-decay multiplier is an estimate grounded in the Microsoft Productivity Score precedent. Pretending it's precise would be dishonest.

## Chosen Approach

Dual-layer FP cost: visible ($15) + structural (participation decay above 20% FP rate). Presented as a formula with an estimated multiplier, not a fabricated dollar figure.

## Rationale

This directly affects threshold selection in Phase 5. If the threshold is tuned to chase recall, FP rate rises. Above ~20% FP, participation collapses within 3 cycles. The model trained on cycle 1 cannot be retrained on cycle 4 because cycle 4 has <50% participation. The product enters a death spiral: more false positives → less data → worse model → more false positives. High precision operating point is justified economically, not just ethically. This is the insight to show Dr. Hong.

## Trade-offs Accepted

- **The arithmetic is more complex** — the FP cost is no longer a single dollar figure but a function of cumulative FP rate over time. Worth it because it's more honest.
- **The participation-decay estimate (40–60% at >20% FP) is based on one precedent** (Microsoft Productivity Score). It is an estimate, not a validated model. This should be revisited after Sprint 1 data is available.
- **The multiplier is not quantified as a specific number** — it remains a structural warning rather than a precise cost term. This limits its direct use in threshold optimization math.

## For Discussion

1. After Sprint 1 ships, should the 20% FP → 40-60% decay estimate be replaced with observed data from the first 3 assessment cycles?
2. Should the frame include a hard FP rate ceiling (e.g., "FP rate must not exceed 20%") as a non-negotiable constraint, separate from the cost calculation?
3. Is the Microsoft Productivity Score precedent the right analogy, or is there a closer precedent in clinical screening tools (where FP rates are well-studied)?
