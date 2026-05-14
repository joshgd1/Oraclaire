---
type: DECISION
date: 2026-05-13
created_at: 2026-05-13T21:30:00+08:00
author: co-authored
phase: analyze
topic: FN cost anchor uses sourced $4K-$21K figure instead of salary assumptions
tags: [fn-cost, dollar-exposure, anchor, market-data]
---

# DECISION 3: FN Cost Anchor — Sourced Market Data

## Decision

The FN cost anchor uses the sourced figure $4,000–$21,000 per burned-out employee per year from the market landscape analysis (01-market-landscape.md §4), replacing the salary-assumption approach from the initial draft.

- **Base case:** $4,000/employee/year (conservative end)
- **Sensitivity analysis:** $21,000/employee/year (upper bound)
- **Daily FN cost formula:** `(N_burned_out × r × cost_anchor) / 365`
- **r (FN rate) is left as a variable** — founder's Phase 5 call

This figure already bakes in productivity loss, absenteeism, and turnover. No derived salary anchor needed.

## Alternatives Considered

1. **Salary-assumption approach (original draft)** — Rejected. Deriving FN cost from 34% × assumed salary requires inventing a salary figure ($60K). When asked "where did the salary number come from?" the answer is "I assumed it." Weak in a presentation context.

2. **Gallup 34% productivity loss only (without replacement)** — Rejected. This captures only the recurring drag, not the lump-sum turnover event. Understates the real cost.

3. **Replacement cost only (50-200% of salary)** — Rejected. This captures only the departure event, not the months of reduced productivity before departure. Also requires a salary assumption.

## Chosen Approach

Use the sourced composite figure ($4K–$21K) that already incorporates all cost categories. Present the formula with r as a variable. Show sensitivity at both bounds.

## Rationale

"Market landscape research" is a stronger answer than "I assumed average salary of X" when presenting to Dr. Hong. The sourced figure is defensible, comprehensive, and does not require defending an auxiliary assumption.

## Dollar Exposure Summary

**Formula:** `Daily FN cost = (125 × r × anchor) / 365`

- At base ($4K): `$1,369.86 × r` — maximum $1,370/day (r=1.0)
- At sensitivity ($21K): `$7,191.78 × r` — maximum $7,192/day (r=1.0)

At a 500-employee company, daily FN exposure **cannot exceed $10,000/day** at either cost anchor. The $10K threshold only becomes reachable at ≥1,000 employees (sensitivity case) or ≥2,500 employees (base case).

## Trade-offs Accepted

- **The $4K–$21K range is wide** — a 5× spread between base and sensitivity means threshold recommendations will depend heavily on which end is more realistic for the target customer. This should be narrowed with customer-specific data.
- **The figure is industry-agnostic** — burnout costs vary significantly by industry (tech vs healthcare vs finance). The current frame does not differentiate. Industry-specific anchors could sharpen the exposure calculation for specific customer segments.
- **r remains unspecified** — the frame presents the math but does not recommend a specific FN rate. This is by design (founder's Phase 5 call) but means the dollar-exposure tables show ranges, not point estimates.

## For Discussion

1. Should the base case be $4K (conservative) or a midpoint like $8K–$10K? The conservative end may understate the case for investment in model accuracy.
2. For the presentation to Dr. Hong, is it stronger to show the full table (r as variable) or pick one illustrative r value (e.g., r=0.10) and show the dollar impact?
3. At what company size does this product become economically compelling? If daily FN exposure is <$150/day at 500 employees, the ROI case may be stronger at enterprise scale (5,000+).
