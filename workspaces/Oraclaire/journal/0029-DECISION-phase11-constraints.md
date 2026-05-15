---
type: DECISION
date: 2026-05-14
author: co-authored
project: Oraclaire
topic: Phase 11 constraint classification — nine constraints classified, seven approved, two challenged and split, one citation corrected
phase: codify
tags: [phase-11, constraints, hard, soft, d28, gdpr, eu-ai-act, lp]
---

# D29: Phase 11 Constraint Approvals

## Summary

Nine constraints classified HARD or SOFT. Founder reviewed and approved seven without change. Two challenges produced sub-constraint splits. One citation corrected.

## Approvals

| #   | Constraint             | Decision                         | Notes                                                                                                                              |
| --- | ---------------------- | -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| C1  | FP soft 15%            | APPROVED                         | D26 override at 16.6% proves crossable                                                                                             |
| C1b | FP decay 20% hard      | APPROVED                         | Physical product viability limit, not legal                                                                                        |
| C2a | FN general soft 15%    | APPROVED                         | $4,000/missed junior/year (D3)                                                                                                     |
| C2b | FN senior soft 10%     | APPROVED — citation corrected    | $21,000/missed senior/year. Source corrected from D4 to D3                                                                         |
| C4  | Human review gate hard | APPROVED                         | EU AI Act Article 14. Demotion impossible                                                                                          |
| C5  | Min team size hard     | APPROVED                         | GDPR Article 5(1)(c). n=5 is conservative product choice; principle is statutory                                                   |
| C6a | EU consent hard        | APPROVED                         | GDPR Article 9 + Article 7                                                                                                         |
| C6b | SG consent hard        | APPROVED                         | PDPA Part IV                                                                                                                       |
| C6c | US consent soft        | APPROVED — California note added | No federal opt-in. CPRA treats health data as sensitive with opt-in — flag as deployment-time check for California-based customers |
| C8a | No HRIS AUP hard       | APPROVED                         | Contract law                                                                                                                       |
| C8b | No HRIS tech N/A       | APPROVED                         | Architecture choice                                                                                                                |
| C9  | ORT soft               | APPROVED                         | Step function, two-consecutive-weeks design                                                                                        |

## Challenge 1: C3 — Critical ceiling 5%

**Original classification:** SOFT — reviewer capacity constraint.

**Founder challenge:** The 5% ceiling is not a reviewer capacity constraint. It is a model calibration signal. From D14 Parameter 7: "If more than 5% score Critical something is wrong — either the model is miscalibrated or there is a genuine organisational crisis that needs a different response than the product provides."

**Reclassification:**

- **C3a — Critical tier calibration signal: HARD.** Internal product health limit. If Critical fires above 5%, the model is miscalibrated or the deployment population is not representative. Named physical fact: "above 5% Critical the model's probability calibration is inconsistent with the D14 design intent." Response is model review, not more reviewers.

- **C3b — Reviewer queue capacity: SOFT.** Operational target. Dollar penalty per hour of delay per unreviewed Critical flag beyond 48 hours (REVIEW_TIMEOUT_HOURS from config.py).

**Why the split matters for the LP:** C3a is a hard stop. If the solver produces a plan where more than 5% of employees are Critical, the response is model review, not reviewer scaling. C3b is the operational constraint the solver can optimise against.

## Challenge 2: C7 — Retention 12 months

**Original classification:** HARD under GDPR Article 5(1)(e).

**Founder challenge:** Partial. The HARD classification is correct for the principle (data cannot be retained longer than necessary). But the 12-month DEFAULT is soft — GDPR Article 5(1)(e) does not specify 12 months. What is "necessary" for quarterly burnout assessment with longitudinal trend tracking is a legal interpretation question.

**Reclassification:**

- **C7a — Maximum retention principle: HARD.** GDPR Article 5(1)(e). Data cannot be retained longer than necessary. The principle is hard. The value is not.

- **C7b — 12-month default: SOFT.** Operational choice within the hard principle. DPA review determines what "necessary" means for this use case. Until that review completes, 12 months is a conservative default that is likely compliant but not confirmed. Penalty shape: dollar penalty per employee record retained beyond the DPA-approved period.

**DPO review package action:** Add to Appendix B (open question 2): "The 12-month retention default requires DPA confirmation that it satisfies Article 5(1)(e) for this specific use case."

## Infeasibility Check — Confirmed

No LP infeasibility confirmed. Small-team scenario (4 people, all opt in) satisfies all hard constraints simultaneously.

Addition: the small-team scenario produces a product experience with no HR visibility (aggregate suppressed at n<5) and Critical flags visible to reviewer only. The product still functions — it provides less organisational insight for small teams. This is expected behaviour, not an infeasibility.

## Unvalidated Cost Terms — Phase 12 Instruction

Four unvalidated terms: reviewer cost, assessment cost, disparate impact, ORT organisational response cost.

Phase 12 instruction: run the solver with placeholder values for reviewer cost and assessment cost explicitly flagged as [UNVALIDATED — FOUNDER TO CONFIRM]. The LP output is directionally useful even with placeholders — it shows the structure of the optimal plan. Absolute cost numbers are unreliable until placeholders are replaced.

Add to Phase 12 instructions: "All cost calculations involving reviewer cost or assessment cost are directional only. Replace placeholders before using Phase 12 output for any customer-facing cost justification."

## For Discussion

1. C1b (FP decay 20%) is HARD as a physical limit. Is this the right LP classification, or should it be SOFT with an extreme penalty that lets the solver approach asymptotically?

2. C5 (min team size) n=5 is a product choice implementing k-anonymity. Should n be configurable per deployment with DPA sign-off on the chosen k?

3. C3a is HARD as a model calibration signal. What operational procedure fires when Critical exceeds 5% — model retrain, threshold adjustment, or deployment pause?
