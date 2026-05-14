---
type: DECISION
date: 2026-05-13
created_at: 2026-05-13T23:30:00+08:00
author: human
phase: analyze
topic: Founder locks all ten remaining Phase 1 decisions (D14)
tags:
  [
    fn-cost,
    fp-ceiling,
    tier-split,
    risk-thresholds,
    auto-flag,
    grievance-cooldown,
    exclusion-fraction,
    burnout-prevalence,
    participation,
    inter-cycle,
  ]
---

# DECISION D14: Founder Locks All Ten Remaining Phase 1 Calls

## Decision

All ten founder-owned decisions from the Phase 1 frame are now locked. Seven confirmed, one changed, all finalized.

### D14-1: Inter-cycle window — 30 days (CONFIRMED)

Monthly cadence matches HR operating rhythm. Weekly pulse fills the gap between cycles. 30 days locked.

### D14-2: Burnout prevalence — 25% (CONFIRMED)

Gallup and WHO alignment sufficient. 25% is the prior, not the truth. First pilot deployment recalibrates.

### D14-3: Employee tier split — 60/40 (CHANGED from 70/30)

**Previous:** 70% junior ($4K) / 30% senior ($21K).
**New:** 60% junior ($4K) / 40% senior ($21K).

**Reason:** Oraclaire's first customer is a knowledge-work organisation (tech, professional services, function-heavy enterprise). In those organisations the senior IC and manager layer is 40-45% of headcount, not 30%. The 70/30 split understates FN cost exposure for the target market.

**Effect on cost tables:**

- New tier split for a 500-employee company:

| Tier                    | %   | Count | Burnout prevalence | Burned-out | Cost/year |
| ----------------------- | --- | ----- | ------------------ | ---------- | --------- |
| Junior / IC             | 60% | 300   | 25%                | 75         | $4,000    |
| Senior / Lead / Manager | 40% | 200   | 25%                | 50         | $21,000   |

- New daily cost constant: `(75 × $4,000 + 50 × $21,000) / 365 = $3,698.63`
- Previous constant was $3,116.44 — the 60/40 split raises the cost floor by 18.7%
- This makes the ROI story more conservative, which is the right direction for CFO conversations

- 70/30 rejected because: wrong for the target market. A generic workforce split does not represent a knowledge-work buyer.

### D14-4: Participation targets — 20%/40% (CONFIRMED, D13 stands)

### D14-5: Exclusion fraction e — 0.10/0.20 placeholders (CONFIRMED)

First pilot deployment generates the real `e` value.

**Addition:** `e` is the FIRST number measured at deployment. Not participation rate. Not model accuracy. `e` determines what the model can actually see — everything else depends on it. Added to product onboarding checklist as a required data collection step.

### D14-6: Grievance cooldown — 90 days configurable (CONFIRMED)

Default 90 days. Configurable per jurisdiction as a deployment parameter. Not hardcoded.

### D14-7: Risk-tier thresholds principle (DECIDED)

Exact numbers deferred to Phase 5 model calibration. Principle locked:

- **Critical** — fires rarely, always triggers human review gate. Target: ≤5% of scorable population per cycle. If >5% score Critical, something is wrong (model miscalibration or genuine organisational crisis).
- **High** — the action tier. HR gets signal, manager gets prompt. Target: 10-15% of scorable population. Meaningful signal without alarm fatigue.
- **Moderate** — early warning. Visible to employee only unless they choose to share. Target: 20-25%.
- **Low** — baseline. Everyone else.

These are calibration guides, not hard constraints. Data may produce different distributions; thresholds move to match reality. The principle holds.

### D14-8: FP rate ceiling — 15% on High/Critical combined (CONFIRMED)

15% ceiling applies to High and Critical tiers combined. FP at Low and Moderate is less damaging because those tiers do not trigger HR action. Trust erosion comes from being incorrectly flagged as High or Critical — not from being told Moderate when Low.

**Update to D2:** The FP ceiling clarification (High/Critical combined, not all tiers) is recorded here and updates the D2 cost analysis.

### D14-9: FN rate target — two-threshold architecture (CONFIRMED)

**Threshold A — general population:** FN target 15%, FP ceiling 15%.

**Threshold B — senior tier:** FN target 10%, FP ceiling 20%.

Higher FP accepted for senior staff because a false alarm costs one 30-minute HR check-in. A false negative costs $21K plus replacement risk. The asymmetry justifies the different threshold.

This confirms the D11 Nuance 3 two-threshold architecture as a Phase 5 commitment.

### D14-10: Auto-flag ceiling — 20% default, configurable (DECIDED)

The auto-flag ceiling is the maximum percentage of the workforce that can be in High or Critical tier simultaneously before the system stops auto-generating individual alerts and triggers an organisational review instead.

**Problem it solves:** If 40% of a team scores High/Critical, that is not individual burnout — it is organisational failure (understaffing, bad management, unrealistic deadlines, toxic culture). Sending 40 individual alerts individualises what is an organisational problem.

**Decision:**

- Below 20% High/Critical: normal alert workflow. Individual flags to HR. Manager prompts.
- Above 20% High/Critical: system suppresses individual alerts and generates a single organisational risk report. HR gets one report: "this team or department has a systemic burnout signal — individual alerts suppressed pending organisational review."

**Why 20%:** The enterprise value audit noted companies already know who is burned out when it is systemic. The product adds no value generating 50 individual alerts that all say the same thing. It adds significant value by naming the systemic pattern and routing it to the right level.

**Named feature:** Organisational Risk Threshold.

**Configurable per deployment.** Default 20%. High-stress industries (healthcare, emergency services) may need higher. Low-baseline environments may want 15%.

## Rationale

Founder's stated reasoning: "A CFO who pushes back on the cost model needs to see conservative assumptions, not optimistic ones." The 60/40 split and the two-threshold FN architecture both reflect this principle — conservative where the money conversation matters, aggressive where the detection conversation matters.

## Alternatives Considered

- **70/30 tier split** — rejected: wrong for knowledge-work target market
- **Quarterly inter-cycle window** — considered: user raised this. Rejected in favour of monthly CBI + weekly pulse (more frequent full signal, sustainable employee time)
- **Single FN threshold** — rejected: the $21K vs $4K cost asymmetry justifies different operating points per tier
- **FP ceiling on all tiers** — rejected: trust erosion is tier-specific (High/Critical), not uniform

## Consequences

1. All Phase 1 decisions are locked. Phase 1 is COMPLETE.
2. The FN cost formula constant must be recalculated for the 60/40 split.
3. Sprint 1 build scope must include: configurable deployment parameters for cooldown period and auto-flag ceiling.
4. Phase 5 model calibration receives two explicit constraints: Critical ≤5%, and two-threshold FN architecture (15%/10%).
5. Product onboarding checklist gains `e` measurement as the first required data collection step.

## For Discussion

1. The 60/40 split raises the daily cost constant by 18.7%. Does the updated sensitivity table change the FP ceiling or FN target decisions at the new constant?
2. The auto-flag ceiling (20%) and the Critical population target (≤5%) interact — if Critical alone hits 5%, High could add another 10-15%, putting combined High+Critical near the 20% ceiling. Is the ceiling measured on High+Critical combined, or Critical alone?
3. The two-threshold FN architecture means the model must identify senior vs junior employees in the scoring pipeline. Is seniority self-reported, derived from HR directory data, or configurable per deployment?
