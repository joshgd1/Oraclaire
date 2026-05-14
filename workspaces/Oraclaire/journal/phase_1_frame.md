# Phase 1 Frame — Journal Entry

**Date:** 2026-05-13
**Phase:** Playbook Phase 1 — Frame
**Sprint:** Sprint 1 — Employee Burnout Risk Scorer (4 tiers: Low / Moderate / High / Critical)
**Model family (pre-selected):** XGBoost + SHAP (architecture decisions deferred to Phase 5)
**Status:** COMPLETE — pending founder final review

---

## Frame Items

### 1. Target

Oraclaire classifies each employee into one of four burnout risk tiers (Low / Moderate / High / Critical) per employee per assessment cycle, predicting the employee's risk state over the next **[30 | founder decides]** days.

### 2. Population — Two-Tier Scoring (DECISION 1)

- **Tier 1 (Individual):** Opt-in only via consent screen. Immediate withdrawal suppresses scores from everyone including self.
- **Tier 2 (Team aggregate):** Default. HR sees team trends only. Minimum team size 5. Below 5, suppressed.
- **Exclusions:** Test/API accounts; medical leave; active structured intervention; contractors without pathway.

### 3. Horizon

**[30 | founder decides]** days from assessment date.

### 4. Cost Terms

**FN cost (DECISION 3):**

> $4,000–$21,000 per burned-out employee per year (sourced: market landscape §4)

- Base: $4,000. Sensitivity: $21,000.
- Formula: `(125 × r × anchor) / 365` per day. r = Phase 5 call.

**FP cost (DECISION 2):**

> Visible: $15/check-in. Structural: participation decay above 20% FP rate → 40-60% drop by cycle 3.

- Effective: `$15 × (1 + participation_decay_multiplier)`
- High precision operating point justified economically (prevents data death spiral), not just ethically.

**FN:FP cost ratio:** ~9:1 at base case (structural asymmetry driven by $4K/year vs $15/check-in).

### 5. Throughput Ceiling

**[10,000 | founder decides]** submissions/day. Owner: Platform Engineering Lead.

---

## Dollar Exposure — FN Rate r as Variable

```
Daily FN = (125 × r × anchor) / 365

Base ($4K):     $1,369.86 × r   (max $1,370/day at r=1.0)
Sensitivity ($21K): $7,191.78 × r  (max $7,192/day at r=1.0)
```

At 500 employees: **daily FN exposure cannot exceed $10,000.** $10K threshold reachable only at ≥1,000 employees (sensitivity) or ≥2,500 employees (base).

| Company | r to hit $10K/day (base) | r to hit $10K/day (sensitivity) |
| ------- | ------------------------ | ------------------------------- |
| 500     | impossible               | impossible                      |
| 1,000   | impossible               | r > 0.69                        |
| 2,500   | r > 0.58                 | r > 0.28                        |
| 5,000   | r > 0.29                 | r > 0.14                        |
| 10,000  | r > 0.15                 | r > 0.07                        |

---

## Decisions Logged

| #   | Decision                                                      | Journal Entry                     |
| --- | ------------------------------------------------------------- | --------------------------------- |
| 1   | Two-tier scoring (individual opt-in + team aggregate)         | 0001-DECISION-two-tier-scoring.md |
| 2   | FP cost includes participation decay (not just $15 check-in)  | 0002-DECISION-fp-trust-erosion.md |
| 3   | FN cost anchor uses sourced $4K–$21K (not salary assumptions) | 0003-DECISION-fn-cost-anchor.md   |

---

## Structural Constraints

### Singapore PDPA — Hard Floor

Mental health data compliance floor. NOT in FN/FP cost math. Two-tier model (Decision 1) designed to satisfy consent requirements. Phase 2 compliance spec.

### Model Family

XGBoost + SHAP. Pre-selected. Phase 5.

---

## Founder-Owned Calls Remaining

- [ ] Prediction window in days
- [ ] Throughput ceiling exact number
- [ ] FN rate r — Phase 5
- [ ] FP rate ceiling (<20% per Decision 2) — Phase 5
- [ ] Burnout prevalence confirmation (currently 25%)
- [ ] Auto-flag ceiling
- [ ] Risk-tier thresholds (Low/Moderate/High/Critical)
- [ ] "Already flagged" employee handling
