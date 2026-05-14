---
type: DECISION
date: 2026-05-13
created_at: 2026-05-14T01:00:00+08:00
author: human
phase: analyze
topic: Phase 1 closure — seniority identification, auto-flag scope, withdrawal cooling-off, participation denominator
tags:
  [
    phase1-closure,
    seniority,
    auto-flag,
    withdrawal,
    participation-denominator,
    sprint-1,
  ]
---

# DECISION D15: Phase 1 Closed — Four Blocking Items Resolved

## Decision

Four items that blocked Phase 2 build planning are now resolved. Phase 1 is COMPLETE and CLOSED.

### D15-1: Seniority Identification Method

**Configurable per deployment. HRIS-derived as default. Self-reported as fallback.**

The customer maps their own job-level field (grade, band, title tier) to Oraclaire's junior/senior binary at deployment configuration.

If no HRIS integration exists, the employee selects their level during the opt-in consent flow. One question. Junior or Senior. No clinical language. No performance framing.

Why self-reported is acceptable as fallback: seniority self-identification has low incentive to game. The output is the employee's own burnout score, not a compensation or performance decision. Misreporting hurts only themselves.

Schema requirement: `seniority_tier` field on employee record. Values: `junior` / `senior`. Source: `hris_derived` or `self_reported`. Null not accepted — fallback to `self_reported` if HRIS field is missing.

Rejected: HRIS-only — blocks Sprint 1 for customers without clean HRIS API. Self-reported-only — degrades two-threshold architecture over time.

### D15-2: Auto-Flag Ceiling Measurement Scope

**High+Critical combined. Triggers on sustained elevation, not single spikes.**

Ceiling is 20% High+Critical combined. Triggers only when the combined rate exceeds 20% for two consecutive weeks on the weekly pulse aggregate OR in a single quarterly CBI cycle. Single-cycle spikes do not trigger organisational review automatically.

Why the two-consecutive-weeks rule: a single bad week on the pulse is noise. Two consecutive weeks is a signal. Prevents the Organisational Risk Threshold from firing on a one-off event and losing credibility with HR.

Updates D14 Parameter 10.

### D15-3: Withdrawal Cooling-Off Period

**48-hour cooling-off. Automatic suppression. No HR notification.**

During the 48-hour window the employee sees a confirmation screen: "Your withdrawal request has been received. Your individual data will stop being collected in 48 hours. You can cancel this request any time before then." One button: Cancel withdrawal. No guilt language. No "are you sure?" friction.

After 48 hours: automatic. Silent. No notification to HR. No flag visible to managers. Employee disappears from individual scoring layer and appears only in team aggregates (if team size remains above 5).

Why 48 hours not 24: 24 hours may not cover a weekend or crisis period where the employee cannot reconsider calmly. 48 hours covers a full working day on either side.

Why automatic not manual: requiring HR to process withdrawal requests creates a chilling effect. Automatic is the only architecture that is genuinely private.

### D15-4: Excluded Employees in Participation Denominator

**Excluded from denominator.**

Participation rate measures "of the people Oraclaire CAN score, what fraction participated." Excluded employees (PIP, ADA, FMLA, workers comp, disciplinary, grievance cooldown) are not scoreable by design. Including them inflates the denominator and makes the product look like it is underperforming when it is correctly protecting people.

Addition: exclusion count reported separately in HR dashboard at category level. Not individual identities — the count. Example: "47 employees are currently outside the scoring window: 12 on leave, 23 in a protected process, 12 in grievance cooldown." This stops HR from thinking the product is missing people, and gives HR a signal about organisational health.

## Alternatives Considered

- **Seniority: HRIS-only** — rejected: blocks Sprint 1 for customers without HRIS API.
- **Seniority: self-reported only** — rejected: degrades model over time.
- **Auto-flag: single-week trigger** — rejected: noise. One bad week is not systemic.
- **Auto-flag: Critical alone** — rejected: systemic burnout shows at High tier too.
- **Withdrawal: immediate** — rejected: burned-out employees make impulsive decisions under acute stress.
- **Withdrawal: manual HR processing** — rejected: chilling effect on withdrawal.
- **Denominator: total workforce** — rejected: penalises the product for correctly protecting excluded employees.

## Consequences

1. Phase 1 is CLOSED. All 15 decisions (D1–D15) locked.
2. Schema must include `seniority_tier` field with source tracking.
3. Opt-in consent flow includes self-reported seniority question when HRIS absent.
4. Auto-flag logic requires consecutive-week tracking on pulse data.
5. Withdrawal flow requires 48-hour countdown with cancel option.
6. HR dashboard includes exclusion count summary at category level.
7. Six deferred items acknowledged and parked for later phases.

## For Discussion

1. Should the 48-hour cooling-off apply to re-opt-in as well (prevent rapid opt-in/withdrawal cycles)?
2. At what exclusion count threshold does the HR dashboard flag "your exclusion rate is abnormally high" — is there a healthy baseline?
3. Should the self-reported seniority field be auditable (i.e., can the customer see the distribution of self-reported vs HRIS-derived to measure data quality)?
