---
type: DECISION
date: 2026-05-13
created_at: 2026-05-13T21:45:00+08:00
author: human
phase: analyze
topic: Throughput ceiling reframed as sustained participation rate, not server capacity
tags: [throughput, participation, ceiling, behavioral-constraint]
---

# CHALLENGE 4: Throughput Ceiling Reframed as Participation Rate

## Decision

The throughput ceiling is **40% sustained participation over 12 assessment cycles**, owned by the Product Owner (founder).

The original framing (10,000 submissions/day server capacity) was the wrong unit of analysis for this product.

## Alternatives Considered

1. **10,000 submissions/day server capacity (original draft)** — Rejected. For a 500-person company with monthly assessments, this is trivially handled. The real constraint is whether enough people participate to keep the model's training data representative.

2. **Both metrics (server capacity AND participation rate)** — Rejected. Having two ceilings dilutes the frame. The binding constraint is participation. Server capacity is an engineering detail, not a frame-level parameter.

## Chosen Approach

Single ceiling: 40% sustained participation over 12 cycles. This reframes every engineering decision — the product's bottleneck is not how fast it scores but how many people are willing to be scored. Feature design, UX, communication, and intervention quality all become throughput levers.

## Rationale

User personas §2C: individual employee participation drops from 30–50% in month one to 5–10% by month six when the tool does not deliver personal value. A server processing 10K submissions/day that receives 20 submissions is not a throughput success — it is a participation failure.

Framing throughput as a participation rate demonstrates understanding of the business problem, not just the technical implementation. That is the difference between a default submission and a differentiated one.

## Trade-offs Accepted

- **40% is an asserted floor, not empirically derived.** The minimum participation rate for representative sampling depends on the population size and burnout prevalence. For 500 employees at 25% prevalence, 40% participation (200 responses) yields ~50 burned-out employees in the sample. Whether this is sufficient for model retraining depends on feature dimensionality — a Phase 5 question.
- **Server capacity is a real constraint at enterprise scale.** At 10,000 employees, burst submission rate during a 5-day window is ~1,600/day. XGBoost handles this easily, but the feature computation pipeline may not. This is acknowledged as an engineering concern but not a frame-level parameter.
- **Participation rate is harder to measure than submissions/day.** It requires tracking unique respondents across cycles, which introduces its own data-collection requirement.

## For Discussion

1. Should the frame include a minimum sample size per team for the aggregate scoring (Tier 2)? A team of 5 with 40% participation is 2 responses — not enough for a meaningful aggregate.
2. Is 40% the right floor for the 500-employee anchor, or should it scale with company size (higher floor for smaller companies)?
3. What is the intervention when participation drops below the ceiling? Is there an automated alert, or does the Product Owner monitor manually?
