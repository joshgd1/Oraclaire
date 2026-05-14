---
type: DECISION
date: 2026-05-13
created_at: 2026-05-13T23:45:00+08:00
author: human
phase: analyze
topic: FN formula corrected for excluded population — irreducible floor acknowledged as product constraint
tags:
  [
    fn-cost,
    formula,
    exclusion-discount,
    irreducible-floor,
    population,
    cost-model,
    compounding,
  ]
---

# DECISION D11: FN Formula Correction

## Decision

Adopt the corrected FN cost formula introducing exclusion discount `e` alongside FN rate `r`. The original formula used 125 burned-out employees as a fixed base, overstating the scorable population. The corrected formula separates model errors on the scorable population from the irreducible cost of employees the model is never allowed to see.

## The Formula

```
Daily FN = $3,116.44 × [(1 - e) × r + e]
```

- `r` = FN rate on the scorable population
- `e` = fraction of burned-out employees in excluded categories
- Irreducible floor = `$3,116.44 × e` (no model improvement can reduce it)

## What Was Wrong With The Original

The original formula (`$3,116.44 × r`) assumed all 125 burned-out employees were scorable. Decision 0006 excludes PIP, ADA, FMLA, workers comp, grievance, and disciplinary employees from scoring. Decision 0005 compounds this: burned-out employees are the most likely to disengage after FP, functionally joining the excluded population in subsequent cycles. The formula treated `e` as zero when it is structurally positive.

## Compounding Effect

Decision 0006 excludes employees on PIPs, in ADA accommodation, on FMLA leave, in workers comp claims, under disciplinary review, or in a 90-day grievance window from scoring entirely — because a burnout score generated during an employment dispute becomes discoverable data that creates liability. These are also the employees most likely to be burned out: PIP performance drops are frequently burnout-driven, and employees filing grievances are often responding to the conditions that cause burnout. Decision 0005 then compounds this blind spot: when false positives occur, burned-out employees — the most overwhelmed people in the organization — are the most likely to disengage from the tool, removing themselves from the scorable population in subsequent cycles. The model faces a double exclusion: it is legally prohibited from seeing the most burned-out sub-population, and operationally likely to lose the next-most burned-out sub-population through participation decay. The corrected formula introduces an exclusion discount `e` to separate the cost of model errors on the scorable population (`r`) from the irreducible cost of employees the model is never allowed to see (`e`). Both terms compound: every point of `e` raises the FN floor, and every point of FP-driven participation decay effectively increases `e` over time.

## Values Set

- e = 0.10 (conservative placeholder): FMLA ~2-3%, PIP ~3-5% at healthy companies, ADA/workers comp/grievance ~2-4% additional; intersection with burnout skews excluded group toward burnout
- e = 0.20 (stressed scenario): organisations with higher PIP rates, active restructuring, or elevated grievance filings
- Both are placeholders — require org-specific measurement at deployment, cannot be derived from Kaggle dataset
- r remains Phase 5 threshold decision (higher stakes per corrected formula)

## Known Simplification

The formula treats `e` as static. In practice `e` compounds upward because FP-driven participation decay causes burned-out employees to disengage from the scorable population. A third variable for this decay is correct in theory but over-engineered for Sprint 1. Acknowledged as a known simplification, not a gap.

## What Was Rejected

- Keeping the original formula with 125 as fixed base (overstates scorable population)
- Adding a third variable for participation decay in Sprint 1 (correct theory, over-engineered scope)
- Using a single `e` value across all deployment scenarios (implies precision the data does not support)

## Trade-Off Accepted

The corrected formula makes Oraclaire's FN exposure look worse than the original frame. A product that shows the buyer the honest cost of what it cannot see is more credible than one built on an overstated base. The irreducible floor is a feature of the problem space, not a failure of the product.

## For Discussion

1. If Sprint 1 pilot data shows e > 0.20 at the target customer, does the product's value proposition survive — or does the irreducible floor eat the ROI case?
2. The compounding of e through FP-driven decay means the formula is most accurate at cycle 1 and least accurate by cycle 6. Should the sensitivity table include a cycle-indexed version for the business case?
3. Counterfactual: if legal-safety exclusions were NOT required (no PIP/ADA/grievance exclusions), would the formula change meaningfully — or do the operational exclusions (medical leave, active intervention) already capture most of the high-risk sub-population?
