---
type: DECISION
date: 2026-05-13
created_at: 2026-05-13T21:30:00+08:00
author: human
phase: analyze
topic: Two-tier scoring model for individual vs team-level burnout risk
tags: [privacy, pdpa, scoring-model, consent, population]
---

# DECISION 1: Two-Tier Scoring Model

## Decision

Oraclaire implements a two-tier scoring model:

- **Tier 1 (Individual scoring):** Only for employees who actively opt in through the consent screen during Oraclaire onboarding. No opt-in, no individual score.
- **Tier 2 (Team aggregate only):** Everyone else. HR sees team-level trends only, and only when the team has at least 5 members. Below 5, data is suppressed.

**Consent is revocable.** Withdrawal suppresses individual scores immediately — including the employee's own history view. Not just from HR. From everyone.

## Alternatives Considered

1. **Full individual scoring visible to HR** — Rejected. PDPA kills this immediately. Individual burnout scores visible to managers without consent is the number one litigation risk identified in ethical/legal analysis (03-ethical-legal-risks.md §3).

2. **Team aggregates only, no individual scoring at all** — Rejected. If employees cannot see their own score, participation dies. Without participation, the model becomes useless. The product needs individual-level value to drive engagement.

3. **Opt-out model (individual by default, can opt out)** — Rejected. Under PDPA and GDPR employment context, consent under employment relationships is considered coerced (GDPR Article 7(4)). Opt-in is the legally defensible position.

## Chosen Approach

Two-tier with active opt-in, immediate withdrawal, and minimum team size of 5 for aggregation.

## Rationale

The ethical analysis presented a binary choice (individual vs team). That was too narrow. The two-tier approach keeps value for employees who actually want to see their own data while protecting everyone else under PDPA. Mental health inferences are sensitive data — individual scores visible to managers without consent is unacceptable.

## Trade-offs Accepted

- **FN/FP arithmetic splits into two populations** — the model may need separate calibration per tier, or a single model with output routed differently based on tier membership. Architecture decision deferred to Phase 5.
- **Participation will skew toward Tier 2 initially** — most employees will not opt in. The individual-scoring population will be smaller, making individual-level FN/FP estimates noisier.
- **Withdrawal is destructive** — historical individual scores are suppressed on withdrawal. This is by design (trust) but means longitudinal individual analysis has gaps.

## For Discussion

1. If Tier 1 opt-in rate is below 20%, is individual-level scoring worth the engineering complexity, or should the product default to team-only?
2. What happens when a team of 5 loses a member (drops to 4) — does historical aggregate data get retroactively suppressed?
3. Should withdrawal have a cooling-off period (e.g., 48 hours) before suppression takes effect, to prevent impulsive decisions during acute stress?
