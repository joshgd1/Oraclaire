# Cost Model — Misclassification Cost Calculation

**Authority:** This spec is the single source of truth for how false negative and false positive costs are calculated, including employee-tier splits, participation decay mechanics, dollar exposure formulas, and scaling thresholds. Every cost figure used in threshold selection, model evaluation, or business case presentation resolves here.

**Origin:** Phase 1 Frame section 4, Decision 2 (journal/0002), Decision 3 (journal/0003), Challenge 1 (journal/0004), Challenge 2 (journal/0005).

**Cross-references:**

- Population exclusions (which affect the scorable population and therefore these cost calculations) are in `population-and-scoring.md` sections 2 and 3.
- The Critical-tier human oversight requirement (which adds cost to FN routing) is in `regulatory-constraints.md` section 3.
- The classification-not-prediction framing (which determines how these costs are validated) is in `product-identity.md` section 2.

---

## 1. FN Cost — Split by Employee Tier

### Source

The FN cost anchor uses the sourced composite figure $4,000–$21,000 per burned-out employee per year from market landscape analysis. This figure already bakes in productivity loss, absenteeism, and turnover. No derived salary assumption is required.

- **Base case:** $4,000/employee/year (conservative end — junior/IC)
- **Upper bound:** $21,000/employee/year (senior/lead/manager)
- The spread is not random — it is driven by seniority and replacement difficulty (ethical risk analysis: seniority and replacement difficulty drive the upper end)

### Why a Single Average Was Rejected

A single midpoint ($12,500) was rejected because it obscures the real trade-off. A model that misses a junior employee costs $4K. Missing a senior team lead who takes 6 months to replace costs $21K. If the model performs differently across these populations — which it likely will, because senior employees have different burnout signal patterns — the aggregate average hides the failure mode that matters most.

### Tier Split for a 500-Employee Company

| Employee tier           | % of workforce | Count | Burnout prevalence | Burned-out count | Cost/year | Daily cost each |
| ----------------------- | -------------- | ----- | ------------------ | ---------------- | --------- | --------------- |
| Junior / IC             | 60%            | 300   | 25%                | 75               | $4,000    | $10.96          |
| Senior / Lead / Manager | 40%            | 200   | 25%                | 50               | $21,000   | $57.53          |

**Assumptions acknowledged:**

- The 60/40 split is locked per D14 (journal/0013). Real workforce composition varies by industry and company; the deployment parameter store allows per-customer configuration.
- Burnout prevalence is 25% per founder specification. Founder owns confirmation of this parameter.
- The $21K upper bound may be conservative for specialized roles (surgeons, ML engineers, principals).

### Daily FN Cost Formula

```
Daily FN = (75 x r x $4,000 + 50 x r x $21,000) / 365
         = $821.92 x r + $2,876.71 x r
         = $3,698.63 x r
```

Where **r** = FN rate (false negative rate). Per D14-9, the two-threshold FN architecture sets separate targets: general population FN ≤ 15%, senior tier FN ≤ 10%.

### Dollar Exposure by FN Rate

| r (FN rate) | Junior daily | Senior daily | Total daily | Total annual |
| ----------- | ------------ | ------------ | ----------- | ------------ |
| 0.05        | $41          | $144         | $185        | $67,500      |
| 0.10        | $82          | $288         | $370        | $135,000     |
| 0.15        | $123         | $432         | $555        | $202,500     |
| 0.20        | $164         | $575         | $740        | $270,000     |
| 0.50        | $411         | $1,438       | $1,849      | $674,688     |
| 1.00        | $822         | $2,877       | $3,699      | $1,349,375   |

### Scaling: When Does Daily Exposure Exceed $10,000?

```
$3,698.63 x r > $10,000  ->  r > 2.70 (impossible at 500 employees)
```

At 500 employees, daily FN exposure cannot exceed $10K. The constraint only hits at larger companies:

| Company size | r to hit $10K/day |
| ------------ | ----------------- |
| 500          | impossible        |
| 1,000        | r > 0.68          |
| 2,500        | r > 0.27          |
| 5,000        | r > 0.14          |
| 10,000       | r > 0.07          |

**Implication:** The economic case for model accuracy strengthens with company size. At enterprise scale (5,000+), even a 16% FN rate produces $10K/day exposure.

### Interaction with Legal-Safety Exclusions

Legal-safety exclusions (see `population-and-scoring.md` section 3) remove a high-risk sub-population from scoring. Employees on PIPs and in protected category processes are often the most burned-out. Their exclusion means:

- The FN dollar exposure above is calculated on the scorable population only.
- The true organizational cost of burnout is higher than these tables show, because the highest-risk subset is excluded by design.
- The model's training data systematically under-represents employees under active management processes.

---

## 2. FP Cost — Participation Decay as Structural Cost

### Visible Cost

$15 per false positive event (30-minute HR check-in at loaded labour cost).

This is the tip of the iceberg.

### Structural Cost — Participation Death Spiral

The real FP cost is not the check-in. It is the erosion of trust that causes participation to collapse, destroying the data the model needs to function.

**Mechanism (sourced: user personas, ethical risk analysis, enterprise audit):**

1. A healthy employee gets flagged as "High" or "Critical" burnout risk.
2. HR schedules a check-in. The employee is confused — they feel fine.
3. The employee tells colleagues. Trust in Oraclaire drops.
4. Participation in the next assessment cycle declines.
5. The employees most likely to disengage are the burned-out ones — they are already overwhelmed and a pointless check-in is the last straw.
6. The model loses signal on precisely the people it needs to find.
7. By cycle 3, if FP rate exceeded 20%, participation has dropped 40–60% (Microsoft Productivity Score 2020 precedent).
8. Below 50% participation, the sample is biased. The model trains on the engaged minority, not the at-risk population.
9. The product churns itself out of existence — the enterprise audit calls this the "So What?" failure: dashboards nobody trusts, data nobody acts on, renewal gets cancelled.

### FP Cost Thresholds

```
At FP rate <= 20%:   participation stable. FP cost ~= $15 per event.
At FP rate >  20%:   participation begins decay. FP cost = $15 + data quality erosion.
At FP rate >  30%:   participation drops 40-60% by cycle 3. FP cost = model failure.
At participation < 50%: product cannot retrain. Self-inflicted death spiral.
```

### Critical Insight: FP Selectively Destroys Signal on Highest-Value Targets

Burned-out employees are the most likely to disengage from the tool after a false positive. This means FP does not just waste time — it selectively removes burned-out employees from the training data. The FP cost compounds because each false positive disproportionately removes the highest-value detection targets.

### Why High Precision Is Justified Economically

A high-precision operating point is justified economically, not just ethically. Tuning for recall at the expense of precision does not just annoy healthy employees — it blinds the model to the people it most needs to find. This is the insight for threshold selection in Phase 5:

- If the threshold is tuned to chase recall, FP rate rises.
- Above ~20% FP, participation collapses within 3 cycles.
- The model trained on cycle 1 cannot be retrained on cycle 4 because cycle 4 has <50% participation.
- The product enters a death spiral: more false positives -> less data -> worse model -> more false positives.

### Participation Decay Estimate Caveats

- The 40–60% participation drop at >20% FP is based on one precedent (Microsoft Productivity Score 2020). It is an estimate, not a validated model. It should be revisited after Sprint 1 data is available.
- The thresholds (20%, 30%, 50%) are heuristics, not calibrated values. They are informed by available evidence but not derived from Oraclaire-specific data.
- The mechanism is described qualitatively. A full participation-decay model (e.g., Markov chain with state transitions) would be more rigorous but is not justified at the spec stage.

---

## 3. Combined Dollar Exposure Formula

For a company of size N employees with burnout prevalence p, junior tier fraction j, and FN rate r:

```
Daily FN = (N x j x p x r x $4,000 + N x (1-j) x p x r x $21,000) / 365
```

For the default parameters (N=500, p=0.25, j=0.60, locked D14):

```
Daily FN = (75 x r x $4,000 + 50 x r x $21,000) / 365
         = $3,698.63 x r
```

The FP cost does not have a clean dollar formula because it is a compounding structural constraint. The visible component is $15 per FP event. The structural component is participation decay above 20% FP rate, which cannot be expressed as a dollar figure without fabricating a number.

Per D14-9, the model uses a two-threshold FN architecture with separate targets per tier:

- General population: FN ≤ 15%, FP ≤ 15%
- Senior tier: FN ≤ 10%, FP ≤ 20%

The senior tier tolerates higher FP (20%) because the FN cost of missing a senior burnout ($21K/year) justifies more aggressive screening. Per D14, the FP ceiling applies to High + Critical combined — Moderate FPs are lower-stakes.

---

## 4. Parameters Locked by D14/D15

| Parameter               | Value                           | Decision              |
| ----------------------- | ------------------------------- | --------------------- |
| Employee tier split     | 60% junior / 40% senior         | D14 (journal/0013)    |
| Daily cost constant     | $3,698.63                       | D14 (journal/0013)    |
| General FN target       | ≤ 15%                           | D14-9                 |
| Senior FN target        | ≤ 10%                           | D14-9                 |
| General FP ceiling      | ≤ 15% (High+Critical combined)  | D14                   |
| Senior FP ceiling       | ≤ 20% (High+Critical combined)  | D14                   |
| Burnout prevalence      | 25%                             | Founder specification |
| FP structural threshold | 20% (participation decay onset) | D2                    |

## 5. Open Questions Remaining

- [ ] After Sprint 1, should the 20% FP → 40–60% decay estimate be replaced with observed data from the first 3 assessment cycles?
- [ ] Should the frame include a third tier (executive / C-suite) with a higher cost anchor?
