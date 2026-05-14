# Phase 10 — Objective Function

# Oraclaire Burnout Risk Scorer

# Sprint 1

Date: 2026-05-14
Status: DRAFT — awaiting founder edits before Phase 11

---

## Decision Variable Space

| Tier     | Probability range | Action              | Description                                                                                                    |
| -------- | ----------------- | ------------------- | -------------------------------------------------------------------------------------------------------------- |
| low      | 0.00–0.20         | no_action           | No HR visibility. Employee sees trend only. No individual alert.                                               |
| moderate | 0.20–0.35         | employee_resources  | SHAP-matched curated content delivered to employee. No HR notification. Employee-facing only.                  |
| high     | 0.35–0.90         | hr_aggregate_signal | Team aggregate surfaced to HR. Manager prompt triggered. Individual data protected.                            |
| critical | 0.90–1.00         | human_review_gate   | Mandatory human reviewer assigned within 48-hour window (D8). No HR visibility until reviewer clears the flag. |

The tier-to-action mapping is determined by the product architecture (D14, D15). The allocation problem is: given the distribution of employees across tiers per quarterly cycle, what is the expected cost and how does the product minimise it?

Decision variables:

```
x[tier, action] = number of employees in each (tier, action) pair per quarterly cycle

Where:
  x[low, no_action]              = employees scored Low (0.00–0.20)
  x[moderate, employee_resources] = employees scored Moderate (0.20–0.35)
  x[high, hr_aggregate_signal]    = employees scored High (0.35–0.90)
  x[critical, human_review_gate]  = employees scored Critical (0.90–1.00)
```

Per-cycle total: `N = x[low] + x[moderate] + x[high] + x[critical]`

---

## Cost Parameters

### Sourced (from decision log)

**FN cost (verbatim from D3):**

> "$4,000 per missed burned-out junior employee per year (conservative base case). $21,000 per missed burned-out senior employee per year (knowledge-work deployment)."

Junior/senior split (D14 Parameter 3): 60% junior / 40% senior.

Blended annual FN cost per missed employee:
`FN_blended = 0.60 × $4,000 + 0.40 × $21,000 = $2,400 + $8,400 = $10,800`

Per-quarter FN cost (annual / 4):
`FN_blended_quarter = $10,800 / 4 = $2,700`

Per-quarter FN cost by tier:

- Junior: $4,000 / 4 = $1,000 per quarter
- Senior: $21,000 / 4 = $5,250 per quarter

**FP cost (verbatim from D2):**

> "$15 per unnecessary HR check-in per employee."

Applies per FP event per quarterly cycle.

### Unvalidated (require founder confirmation before Phase 11)

**Reviewer cost:**
"$35–65 per hour for HR specialist review time (unvalidated — founder must confirm before Phase 11 constraint setting)."
Per-minute: $0.58–$1.08.
Estimated review time per Critical flag: 30 minutes (assumed — unvalidated).
Per-review cost: 30 × $0.58–$1.08 = $17.40–$32.40.

**Assessment cost:**
"$2–5 per employee per quarterly CBI cycle in survey platform and HR administration cost (unvalidated — founder must confirm)."

---

## Objective Formula

```
minimise: C_total(x) = C_FN(x) + C_FP(x) + C_reviewer(x) + C_assessment(x)
```

### Term 1: False-Negative Cost

```
C_FN(x) = sum over tier in {low, moderate, high, critical} [
    FN_rate(tier) × x[tier, action] × FN_cost(seniority)
]
```

Where:

- `FN_rate(tier)` = probability that an employee in this tier is truly burned out (Burn Rate ≥ 0.45) but not flagged for intervention
- Low tier: `FN_rate(low) = 1` (all burned-out employees in Low are missed — no action taken)
- Moderate tier: `FN_rate(moderate) = 0` (employee receives resources — counted as detected, not missed)
- High tier: `FN_rate(high) = 0` (HR aggregate signal triggered — counted as detected)
- Critical tier: `FN_rate(critical) = 0` (human review gate — counted as detected)
- `FN_cost(seniority)` = $1,000/quarter (junior) or $5,250/quarter (senior) per D3

Expanding with the seniority split (D14 Parameter 3):

```
C_FN(x) = FN_rate(low) × x[low, no_action]
          × (0.60 × $1,000 + 0.40 × $5,250)
        = 1.0 × x[low, no_action] × $2,700
```

Only employees in the Low tier who are truly burned out contribute to FN cost. The tier-to-action mapping ensures Moderate, High, and Critical employees receive intervention — their FN rate is zero. The FN cost is carried entirely by missed employees in Low and by false negatives in Moderate (employees who are burned out but scored below the Moderate boundary).

More precisely, using the model's FN rate at the operating threshold:

```
C_FN(x) = r_FN × N_positive × FN_blended_quarter

Where:
  r_FN       = model FN rate at THRESHOLD_A = 0.35 (currently passing the 15% target per D26)
  N_positive = number of truly burned-out employees in the population per quarter
  FN_blended_quarter = $2,700 (weighted junior/senior per D3 and D14)
```

### Term 2: False-Positive Cost

```
C_FP(x) = sum over tier in {high, critical} [
    FP_rate(tier) × x[tier, action] × $15
]
```

Where:

- FP applies to employees flagged High or Critical who are not truly burned out (Burn Rate < 0.45)
- `FP_rate(high)`: fraction of x[high] that are false positives
- `FP_rate(critical)`: fraction of x[critical] that are false positives
- $15 per unnecessary HR check-in per D2

Using the model's FP rate at the operating threshold:

```
C_FP(x) = r_FP × N_negative × $15

Where:
  r_FP       = model FP rate at THRESHOLD_A = 0.35 (currently 16.6% — accepted per D26)
  N_negative = number of non-burned-out employees in the population per quarter
```

### Term 3: Reviewer Cost

```
C_reviewer(x) = x[critical, human_review_gate] × review_minutes × reviewer_rate
```

Where:

- `review_minutes` = estimated 30 minutes per Critical flag (unvalidated)
- `reviewer_rate` = $0.58–$1.08 per minute ($35–$65/hour, unvalidated)
- Per-review cost: $17.40–$32.40

```
C_reviewer(x) = x[critical] × 30 × $0.83(midpoint)
             = x[critical] × $24.90
```

Reviewer cost applies only to the Critical tier — the human_review_gate action. All other tiers have zero reviewer cost.

### Term 4: Assessment Cost

```
C_assessment(x) = N × assessment_cost_per_employee
```

Where:

- `N` = total scored employees per quarterly cycle (all tiers)
- `assessment_cost_per_employee` = $2–$5 per CBI cycle (unvalidated)
- Midpoint: $3.50

```
C_assessment(x) = N × $3.50(midpoint)
```

Assessment cost applies to every employee who completes the CBI, regardless of tier. It is the cost of running the product at all — the participation cost that erodes engagement if the product's value does not justify the time investment.

### Full Objective

```
minimise: C_total(x) = r_FN × N_positive × $2,700
                      + r_FP × N_negative × $15
                      + x[critical] × 30 × $0.83
                      + N × $3.50
```

Subject to: tier boundaries, threshold values, and population distributions (Phase 11 will formalise constraints).

---

## Defenses Per Term

### FN Cost Defense

This term is in the objective because omitting it produces a cost-minimising solution that drives all employees toward Low tier — zeroing reviewer cost, FP cost, and assessment cost while missing every burned-out employee. The annual FN exposure at the do-nothing baseline is $1,137,500 (D10 corrected formula at e=0.10, r=1.0). The blended quarterly FN cost is $2,700 per missed employee (D3: "$4,000 per missed burned-out junior employee per year" at 60% and "$21,000 per missed burned-out senior employee per year" at 40%, D14 Parameter 3). Without this term the optimiser has no incentive to detect anyone — the cheapest employee is one the product never scores.

### FP Cost Defense

This term is in the objective because omitting it produces a recall-maximising solution that flags every employee as High or Critical — zeroing FN cost but triggering the Organisational Risk Threshold (D14 Parameter 10, ceiling 20%) and suppressing all individual alerts when the organisation exceeds capacity. The FP cost is "$15 per unnecessary HR check-in per employee" (D2). The participation decay model (D5) shows that above 20% FP rate, 40–60% of burned-out employees drop out by cycle 3 — the product eats its own training data. Without this term the optimiser has no incentive to be selective — every employee gets flagged because flagging is free.

### Reviewer Cost Defense

This term is in the objective because omitting it allows the model to drive unlimited employees to Critical tier — where each requires a human reviewer within 48 hours (D8 EU AI Act constraint). Without this term the LP does not account for reviewer capacity. If 200 employees hit Critical in one cycle and each requires 30 minutes of specialist review, that is 100 reviewer-hours in a 48-hour window — approximately 12.5 full-time reviewers working around the clock. The reviewer cost ($0.58–$1.08 per minute, unvalidated) makes Critical-tier volume visible in the objective so that Phase 11 constraints can formalise the reviewer capacity bound.

### Assessment Cost Defense

This term is in the objective because omitting it ignores participation decay — if assessment burden is not in the cost model the product does not penalise high-frequency assessment cadences that erode participation. The D13 architecture target is 40% sustained participation over 12 cycles. Assessment cost ($2–$5 per employee per quarterly CBI, unvalidated) is the per-cycle cost of keeping an employee in the scored population. Without this term the optimiser treats assessment as free and has no cost signal against cadences that push participation below the 40% target — at which point aggregate statistics become unreliable and the buyer's ROI degrades.

---

## Defendable Trade-Offs

### Trade-Off 1: FN-Minimisation vs Reviewer Capacity

Pure FN-minimisation drives every employee to Critical tier — reviewer cost explodes, the 48-hour review window (D8 EU AI Act) is breached, and Critical flags become invisible to HR because they cannot be reviewed in time. When every employee is Critical, no employee is Critical — the tier loses its meaning and the mandatory human review gate becomes a bottleneck that prevents any action. The objective must balance detection sensitivity against the operational capacity to respond to what is detected.

### Trade-Off 2: Cost-Minimisation vs FN Exposure

Pure cost-minimisation drives every employee to Low tier — zero reviewer cost, zero FP cost, zero assessment cost (if the product is not running, assessment is zero). But FN exposure reaches the do-nothing annual baseline of $1,137,500 (D10 corrected formula at e=0.10, r=1.0). The product exists to reduce this number. The objective must balance the cost of running the product against the cost of the problem the product was built to solve. A product that costs $0 and detects $0 is not a product — it is an absence.

### Trade-Off 3: Two-Tier FN Cost vs Single Average

Ignoring the two-tier FN cost (junior $4,000 / senior $21,000, D3 and D14 Parameter 3) and using a single average ($10,800 blended) produces a model that under-invests in detecting senior employee burnout — the most expensive misses at 5.25× the junior cost — while over-investing in junior detection where the FN cost is lower. The two-threshold architecture (THRESHOLD_A = 0.35 for general, THRESHOLD_B = 0.30 provisional for senior) exists because the cost asymmetry demands different operating points for different populations. Collapsing the two tiers into one average in the objective collapses the product's primary architectural differentiation into a rounding error.

---

## Unvalidated Cost Terms

The following figures are estimates from industry benchmarks, not sourced from the Oraclaire decision log. They require founder confirmation before Phase 11 constraint setting:

1. **Reviewer rate:** $35–$65 per hour ($0.58–$1.08 per minute) for HR specialist review time. Source: industry benchmark. Not in D-cost model.

2. **Review time per Critical flag:** 30 minutes assumed. Source: no source — this is an assumption about the time a qualified reviewer needs to assess one Critical-tier employee, review their SHAP waterfall, and make a disposition decision. Must be validated against the pilot customer's HR team.

3. **Assessment cost per CBI cycle:** $2–$5 per employee per quarterly cycle. Covers survey platform licensing, HR administration time, and opportunity cost of employee time completing the instrument. Source: industry benchmark. Not in D-cost model.

4. **FN_rate and FP_rate per tier:** Currently computed at the model level (overall FN = passing 15% target, overall FP = 16.6% at threshold 0.35). Per-tier FN/FP rates require the full-dataset per-tier validation that is a Sprint 2 commitment (D26 disposition S4-F1, S4-F2).

---

Phase 10 objective drafted. Waiting for your edits before Phase 11 constraints.
