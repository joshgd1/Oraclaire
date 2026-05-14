---
type: DECISION
date: 2026-05-13
created_at: 2026-05-13T21:45:00+08:00
author: human
phase: analyze
topic: Expanded population exclusions for legal-safety — PIP, ADA, FMLA, workers comp
tags:
  [population, exclusions, litigation, employment-dispute, discoverable-data]
---

# CHALLENGE 3: Expanded Legal-Safety Population Exclusions

## Decision

Add a second exclusion category beyond operational exclusions: legal-safety exclusions covering employees in employment-dispute-adjacent contexts.

**Additional exclusions:**

- Employees currently on a Performance Improvement Plan (PIP)
- Employees under active disciplinary review
- Employees in a protected category process: ADA accommodation, FMLA leave, workers' compensation claim
- Employees who have filed a workplace complaint or grievance within the last 90 days (cooldown window)

These employees are excluded from individual scoring entirely. A score in these contexts creates discoverable data in employment disputes.

## Alternatives Considered

1. **Treat as Phase 2 compliance specification** — Rejected. This is a population definition that changes the FN/FP arithmetic. If left to Phase 2, the model is built on a population that will change later. That is the feature-leakage-from-post-hoc-exclusions failure mode.

2. **Include these employees but suppress scores from HR view** — Rejected. Suppression from the HR interface does not prevent the data from existing in the database. A subpoena reaches the database, not the UI. The data must not be generated in the first place.

## Chosen Approach

Two-category exclusion structure: operational (test accounts, medical leave, contractors) and legal-safety (PIP, disciplinary, ADA/FMLA/workers comp, recent grievance). Both categories exclude from scoring entirely.

## Rationale

A burnout risk score generated during a PIP or ADA process will be subpoenaed. The score becomes evidence — either for the employer ("see, they were burned out, not discriminated against") or for the employee ("the company knew I was at risk and took adverse action anyway"). Either way, the score creates liability the product did not intend.

## Trade-offs Accepted

- **The excluded population may include burned-out employees.** Employees on PIPs are often burning out — that's why their performance dropped. Excluding them from scoring means the model will have a systematic blind spot for a high-risk sub-population. The FN rate on this sub-population is, by definition, 100% (they are never scored).
- **The 90-day grievance cooldown window is an assumption.** Legal counsel may recommend a different window (30 days, 180 days). Founder owns this parameter.
- **Detection of these exclusions requires HRIS integration.** The system needs to know who is on a PIP, who filed a grievance, etc. Without HRIS integration, this exclusion cannot be enforced automatically. Manual enforcement introduces human error.

## For Discussion

1. Should excluded employees appear in the denominator for participation rate calculations? If yes, the 40% sustained participation ceiling (Challenge 4) becomes harder to maintain.
2. Should the system notify HR when an employee enters an exclusion category ("this employee was being scored and is now on a PIP — their historical scores must be purged")?
3. Is the grievance cooldown 90 days the right window, or should it be tied to the specific jurisdiction's EEOC filing deadline (180 days in the US)?
