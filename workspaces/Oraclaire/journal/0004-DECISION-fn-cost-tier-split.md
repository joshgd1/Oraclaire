---
type: DECISION
date: 2026-05-13
created_at: 2026-05-13T21:45:00+08:00
author: human
phase: analyze
topic: Split FN cost by employee tier instead of using a single range
tags: [fn-cost, dollar-exposure, employee-tier, seniority]
---

# CHALLENGE 1: FN Cost Split by Employee Tier

## Decision

The $4,000–$21,000 FN cost range is split into two tiers driven by seniority and replacement difficulty, not presented as a single range or averaged into a midpoint.

| Tier                    | % workforce | Cost/year | Rationale                                      |
| ----------------------- | ----------- | --------- | ---------------------------------------------- |
| Junior / IC             | 70%         | $4,000    | Lower replacement cost, shorter ramp           |
| Senior / Lead / Manager | 30%         | $21,000   | Hard to replace, team disruption, 6-month ramp |

## Alternatives Considered

1. **Single midpoint ($12,500 average)** — Rejected. A generic submission approach. Hides the real trade-off: missing a junior costs $4K, missing a senior costs $21K. If the model performs differently across tiers (likely — different burnout signal patterns), the average hides the failure mode that matters most.

2. **Keep the $4K–$21K range as-is** — Rejected. A range without an explanation of what drives the spread is hand-waving. Dr. Hong will ask why the spread exists and get no answer.

## Chosen Approach

Two-tier split with driver explanation. The spread is not random — it is driven by seniority and replacement difficulty (ethical risk §3.4). Splitting demonstrates understanding of who burns out and what that costs.

## Rationale

If someone asks why not $21,000, the answer is now specific: "because that end applies to senior employees who are 30% of the population. For the 70% junior tier, the cost anchor is $4,000." This is defensible in a presentation.

## Trade-offs Accepted

- **The 70/30 split is an assumption** — real workforce composition varies by industry and company. A tech company may be 50/50; a retail operation may be 90/10. The frame uses 70/30 as a plausible default for the 500-employee anchor company.
- **The tier split adds complexity to the arithmetic** — two cost terms instead of one. Worth it for the specificity gain.
- **Senior employee cost may exceed $21K** in specialized roles (surgeons, ML engineers, principals). The upper bound may itself be conservative for some populations.

## For Discussion

1. Should the frame include a third tier (executive / C-suite) with a higher cost anchor, or is the junior/senior split sufficient for Sprint 1?
2. Is the 70/30 split the right assumption for the target customer segment, or should it be parameterized (another variable for the user to set)?
3. If the model performs differently across tiers (e.g., higher FN rate for seniors due to signal masking), should Phase 5 report r per tier rather than a single r?
