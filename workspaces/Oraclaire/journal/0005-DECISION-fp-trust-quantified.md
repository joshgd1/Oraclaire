---
type: DECISION
date: 2026-05-13
created_at: 2026-05-13T21:45:00+08:00
author: human
phase: analyze
topic: Trust erosion quantified as participation decay rate, not left unquantified
tags: [fp-cost, trust-erosion, participation-decay, signal-loss]
---

# CHALLENGE 2: FP Trust Erosion Quantified as Participation Decay

## Decision

The FP cost term is quantified as a participation decay rate with a defined mechanism and threshold, not left as "unquantified pending founder input."

**Mechanism:**

1. FP → healthy employee flagged → trust erosion → employee disengages
2. Burned-out employees are the most likely to disengage after a false positive (already overwhelmed, a pointless check-in is the last straw)
3. Model loses signal on precisely the highest-value detection targets
4. Below 50% participation: biased sample → model cannot retrain → product death spiral

**Thresholds:**

- FP ≤ 20%: participation stable. Cost ≈ $15/event.
- FP > 20%: participation decay begins. Cost = $15 + data quality erosion.
- FP > 30%: 40-60% drop by cycle 3. Cost = model failure.

## Alternatives Considered

1. **Leave as "unquantified pending founder input"** — Rejected. The data to model this is already in the files (user personas §3A, ethical risk §1.3, enterprise audit §3). Leaving it blank signals the dots were not connected — the opposite of what the rubric rewards.

2. **Quantify as a specific dollar figure** — Rejected. No sourced data exists for a precise trust-erosion dollar amount. The participation-decay mechanism is the honest quantification — it describes the structural cost without fabricating a number.

## Chosen Approach

FP cost presented as a compounding structural constraint with defined thresholds, not a dollar figure. The critical insight — FP disproportionately removes burned-out employees from training data — is surfaced explicitly.

## Rationale

The enterprise value audit's "So What?" test: a product that generates dashboards nobody trusts gets cancelled at renewal. The FP cost is not transactional ($15 check-in). It is structural (data quality death spiral). Leaving it unquantified would mean the Phase 5 threshold decision ignores the product's own survival constraint.

## Trade-offs Accepted

- **The 40-60% participation drop estimate at >20% FP is based on one precedent** (Microsoft Productivity Score). It should be revisited after Sprint 1 data.
- **The mechanism is described qualitatively, not modeled mathematically.** A full participation-decay model (e.g., Markov chain with state transitions) would be more rigorous but is not justified at the frame stage.
- **The thresholds (20%, 30%, 50%) are heuristics, not calibrated values.** They are informed by available evidence but not derived from Oraclaire-specific data.

## For Discussion

1. After Sprint 1 ships, should these thresholds be replaced with observed participation rates from the first 3 cycles?
2. Is the Microsoft Productivity Score the right precedent, or should clinical screening FP literature (mammography, PSA testing) be cited instead? Clinical FP has well-studied participation-decay effects.
3. Should the frame include a hard FP rate ceiling (e.g., "must not exceed 20%") as a non-negotiable constraint, or keep it as a cost term that feeds into the threshold optimization?
