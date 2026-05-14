---
type: DECISION
date: 2026-05-14
created_at: 2026-05-14
author: human
phase: analyze
topic: Deployment architecture confirmed with two amendments and one addition
tags:
  [
    phase6,
    deployment,
    architecture,
    tier-boundaries,
    threshold-b,
    pulse-log,
    d20,
  ]
---

# DECISION D20: Deployment Architecture Confirmation

Title: "Phase 6 deployment architecture confirmed with two amendments and one addition — cleared for implementation"

## Amendment 1: Risk Tier Probability Boundaries

Agent proposed Critical at ≥ 0.60. Changed to ≥ 0.75.

Why 0.75: The Phase 4 prediction table shows genuinely high-burnout employees (BR > 0.60) produce RF probabilities of 0.85, 0.99, 0.99, 0.99, 1.00. The only borderline case (EID_001, BR=0.45) sits at 0.31 — comfortably High, not approaching Critical. 0.75 as the Critical floor means the human review gate fires on genuinely high-confidence predictions — not on every employee above the operating threshold. This protects the reviewer from alert fatigue and keeps Critical rare as D14 Parameter 7 requires.

Full dataset validation target: Critical fires on ≤ 5% of scorable population at 0.75. If above 5% — raise to 0.80. If below 2% — lower to 0.70.

Confirmed boundaries: Low 0.00–0.20, Moderate 0.20–0.30, High 0.30–0.75, Critical 0.75–1.00.

## Amendment 2: Threshold B Configurable From Day One

Threshold B starts at 0.30 same as Threshold A. But must be configurable in config.py — not hardcoded. When HRIS seniority data is available and the full dataset senior sub-population cost curve is produced, Threshold B is updated in config.py without touching any other code.

The two-threshold architecture is live from Sprint 1 even if both thresholds start at the same value.

## Addition: Weekly Pulse Storage in Audit Trail

Component 2 includes the weekly pulse interface but the audit trail schema covered CBI predictions only. Pulse gets its own audit record in data/audit/pulse.jsonl with pulse_id, timestamp, employee_id, week, pulse_score, drift_flag, drift_weeks_consecutive. Pulse log entries are never surfaced to HR — employee-only.

## Pre-Commitments Carried Into Implementation

Eight total. Six from architecture document plus two from D20:

7. Critical boundary 0.75 — validate on full dataset. Target: ≤ 5% of scorable population.
8. Threshold B configurable from day one in config.py.

## Consequences

1. Implementation begins with config.py (Step 1)
2. Nine implementation steps in dependency order, each confirmed before proceeding
3. Integration test against 12-row clean dataset as final gate

## For Discussion

1. Should the feature label translation table include seniority_tier for the employee view, or is "Your role level" too vague?
2. Is the 48-hour review timeout the right window, or should it be shorter for a first deployment?
3. Should the curated resources be configurable per deployment, or is the Sprint 1 set fixed?
