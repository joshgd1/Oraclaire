---
name: oraclaire-product-knowledge
description: Oraclaire burnout classifier Sprint 1 decisions, model, constraints, cost model, deployment gates. Use for any Oraclaire design/model/product question.
tools: [Read, Grep, Glob]
---

# Oraclaire Product Knowledge — Sprint 1 Complete

Read-only institutional knowledge agent. Any future agent working on Oraclaire MUST consult this before making design, model, or product decisions. All decisions below are canonical; contradictions require a new journal entry overturning the prior decision.

Sprint 1 status: **GO** (D27, 2026-05-14). Four conditions named. Customer deployment checklist operational.

---

## 1. Product Identity

Oraclaire is a **classification product**, not a predictive product.

- **Output:** 4-tier burnout risk classification per employee per assessment cycle (Low / Moderate / High / Critical)
- **What it measures:** Current burnout risk state as of the assessment date
- **What it does NOT do:** Predict future burnout onset, claim longitudinal validity, or forecast risk over a time window
- **Model family (Sprint 1 — confirmed D17):** Random Forest + SHAP (n_estimators=100, max_depth=5, random_state=42)
- **Feature set (Sprint 1 — 10 features after RE-DO):** 8 original + `tenure_fatigue` + `tenure_workload` interaction terms (D24)
- **Validation type:** Cross-sectional (single-timepoint classification)
- **Assessment cadence:** Quarterly (monthly CBI + weekly pulse per D14)

**DO:**

- Frame the product as "classify current burnout risk accurately and transparently"
- Use trajectory analysis across cycles (improved / held / worsened) as the temporal dimension

**DO NOT:**

- Use "predict", "prediction", "predictive", or "forecast" in any product description or model documentation
- Claim the model predicts burnout before it happens
- Add disclaimers like "preliminary, not longitudinally validated" to soften a prediction claim

**Why:** Cross-sectional survey data cannot support longitudinal prediction claims. Origin: journal/0009.

---

## 2. Tier Boundaries and Thresholds (Locked)

| Tier     | Score Range | Action              | Description                                                                           |
| -------- | ----------- | ------------------- | ------------------------------------------------------------------------------------- |
| low      | 0.00 – 0.20 | no_action           | No HR visibility. Employee sees trend only.                                           |
| moderate | 0.20 – 0.35 | employee_resources  | SHAP-matched content to employee. No HR notification.                                 |
| high     | 0.35 – 0.90 | hr_aggregate_signal | Team aggregate to HR. Manager prompt triggered. Individual data protected.            |
| critical | 0.90 – 1.00 | human_review_gate   | Mandatory reviewer within 48h (D8 EU AI Act). No HR visibility until reviewer clears. |

**THRESHOLD_A = 0.35** (general population, locked D26). Originally 0.30, raised after RE-DO (D24-D26).

**THRESHOLD_B = 0.30** (senior tier, provisional — requires HRIS validation in Sprint 2).

**Critical boundary = 0.90** (raised from 0.75 in D24 to meet 5% Critical cap).

**DRIFT_ACCEPTABLE_RANGE = (0.30, 0.40)** (±0.05 from 0.35). Adjustments outside require a new D-number with cost rationale.

**Why 0.35:** 0.30 FP=21.1% (above 20% decay threshold), 0.40 misses 5 BR≥0.60 employees including BR=0.84 at $20K-$105K FN exposure. 0.35 keeps BR=0.84 at p=0.37 with FP=16.6% (within decay buffer). Origin: D26.

---

## 3. Population Rules — Two-Tier Scoring

### Tier 1 — Individual Scoring (Opt-In Only)

- Active opt-in through consent screen. Not delegated by manager/HR.
- Withdrawal: 48-hour cooling-off, then total suppression from all viewers (D15-3).
- No retroactive re-activation.

### Tier 2 — Team Aggregate Only (Default)

- Minimum team size: 5. Below 5, aggregates suppressed.
- HR sees team trends only. No individual-level data for Tier 2.

### Legal-Safety Exclusions (Both Tiers)

Data must NOT be generated (not merely suppressed from display):

- PIP employees, disciplinary review, ADA/FMLA/workers comp
- Grievance within 90 days (configurable)

### Operational Exclusions

- Test accounts, medical leave, active intervention, contractors

**Why:** A burnout score during a PIP becomes subpoena evidence. Suppression from UI is insufficient — the database is reachable by subpoena. Origin: journal/0001, journal/0006.

---

## 4. Cost Model

### FN Cost — Split by Employee Tier

| Tier   | % Workforce | Cost/Year | Source          |
| ------ | ----------- | --------- | --------------- |
| Junior | 60%         | $4,000    | D3, market data |
| Senior | 40%         | $21,000   | D3, market data |

Blended quarterly FN cost: $2,700 per missed employee (D14 Parameter 3: 60/40 split).

### FP Cost — Participation Decay

- Visible: $15 per unnecessary HR check-in (D2)
- Structural: above 20% FP, 40-60% participation drop by cycle 3 (D5 Microsoft Productivity Score precedent)
- FP selectively removes burned-out employees from training data (adversarial non-response, D1/D5)

### Objective Function (Phase 10)

```
minimise: C_total = r_FN × N_positive × $2,700
                    + r_FP × N_negative × $15
                    + x[critical] × 30 × $0.83
                    + N × $3.50
```

Unvalidated terms (require founder confirmation): reviewer rate ($35-65/hr), review time (30 min assumed), assessment cost ($2-5/employee/cycle), per-tier FN/FP rates.

### Reviewer Cost

- Critical tier only: estimated $24.90 per review (30 min × $0.83/min midpoint, unvalidated)
- 48-hour review window (D8 EU AI Act, config.py REVIEW_TIMEOUT_HOURS)

---

## 5. Pre-Registered Floors and Model Performance

| Floor              | Value  | Status                                                   |
| ------------------ | ------ | -------------------------------------------------------- |
| Brier score        | ≤ 0.15 | PASS (0.0844)                                            |
| MFS SHAP dominance | < 40%  | PASS (29.9% post-RE-DO)                                  |
| FP ceiling         | ≤ 15%  | FAIL with accepted override (16.6%, within decay buffer) |
| FN target          | ≤ 15%  | PASS                                                     |
| Threshold B FN     | ≤ 10%  | PENDING (requires HRIS validation)                       |
| Threshold B FP     | ≤ 20%  | PENDING (requires HRIS validation)                       |

### SHAP Gate (D16)

No single feature may exceed 40% SHAP importance. XGBoost disqualified at 97.4% MFS (D16). RF post-RE-DO at 29.9% (D24).

### Brier Calibration (D18)

If Brier > 0.15 at retrain: Platt scaling applied before threshold selection.

---

## 6. Hard Constraints (Phase 11)

| ID  | Constraint            | Value                                | Enforcement                             |
| --- | --------------------- | ------------------------------------ | --------------------------------------- |
| H1  | FP ceiling            | ≤ 0.20 decay / ≤ 0.15 pre-registered | Rollback at 0.25 × 2 consecutive cycles |
| H2  | FN target             | ≤ 0.15                               | Retrain if breached                     |
| H3  | ORT ceiling           | High+Crit ≤ 20%                      | Auto-flag suppression when exceeded     |
| H4  | Critical cap          | ≤ 5% of scored                       | Boundary raised until cap met           |
| H5  | Review window         | ≤ 48 hours                           | Auto-escalation after 48h               |
| H6  | MFS SHAP gate         | < 40%                                | SHAP waterfall suppressed if breached   |
| H7  | Brier floor           | ≤ 0.15                               | Platt scaling if breached               |
| H8  | Minimum participation | ≥ 20% × 2 cycles                     | Product pause if below                  |

### Soft Constraints

| ID  | Constraint           | Value                   | Note                          |
| --- | -------------------- | ----------------------- | ----------------------------- |
| S1  | Participation target | → 40%                   | Aspirational, tracked         |
| S2  | Assessment cadence   | Quarterly               | Product decision              |
| S3  | Reviewer capacity    | x[crit]×30m ≤ available | Operational sizing            |
| S4  | Drift range          | (0.30, 0.40)            | Requires D-number if exceeded |

---

## 7. Regulatory Floors

### Singapore PDPA

- Opt-in consent architecture (Tier 1). Opt-out is coerced consent under PDPA.
- Data collected for scoring cannot be repurposed for performance/disciplinary decisions.
- Cross-border transfer requires comparable protection or contractual safeguards.

### EU AI Act — High-Risk Employment AI (Annex III)

- **Human oversight at Critical tier only** (not all tiers — proportional)
- Critical-tier reviewer must have authority to override model classification
- SHAP satisfies transparency obligation — each score decomposable into contributing features
- Conformity assessment required before EU customer engagement
- Applies to any customer with EU-based employees, not just EU-headquartered companies

**DPO hard gate:** SHAP output format must be reviewed by qualified legal/DPO professional before first customer deployment (D17, D27 Condition 1). Employee UI locked until sign-off.

---

## 8. Deployment Gate (D27 — GO)

**Decision:** GO with four named conditions.

1. **DPO sign-off** before employee UI activation (hard gate, D17)
2. **Pilot-only deployment** — no general availability until Sprint 2 validation complete
3. **No model performance claims** until one full quarterly cycle validates pre-registered floors on real data
4. **Sprint 2 items communicated** to pilot customer as known limitations

### Customer Deployment Checklist (6 Gates)

1. Legal/compliance (AUP, DPA, jurisdiction, works council)
2. DPO sign-off (HARD GATE — employee UI locked until complete)
3. Customer configuration (100+ employees, seniority method, exclusions)
4. First deployment measurement (e-value, monitoring plan, rollback process)
5. Known limitations disclosed (S1-F1 seed instability, S2-F2 RA fragility, Threshold B unvalidated, no performance claims)
6. Employee communication (voluntary, privacy, consent)

### Monitoring Plan (7 Signals)

| Signal                          | Frequency | Alert Threshold            |
| ------------------------------- | --------- | -------------------------- |
| MFS SHAP drift                  | Quarterly | > 40%                      |
| FP rate per cycle               | Quarterly | > 20%                      |
| Participation rate              | Quarterly | < 20% for 2 cycles         |
| Pulse drift false trigger       | Weekly    | > 10% per week             |
| Critical tier review completion | Weekly    | > 10% auto-escalation rate |
| Brier score per cycle           | Quarterly | > 0.15                     |
| resource_allocation missingness | Quarterly | > 15%                      |

### Rollback

- **Trigger:** FP rate exceeds 25% for two consecutive quarterly cycles
- **Target:** Pre-Oraclaire manual HR process

---

## 9. Decision Log Index (D1–D27)

| #   | Decision                                   | Journal                                             |
| --- | ------------------------------------------ | --------------------------------------------------- |
| 1   | Two-tier scoring model                     | 0001-DECISION-two-tier-scoring.md                   |
| 2   | FP cost includes participation decay       | 0002-DECISION-fp-trust-erosion.md                   |
| 3   | FN cost uses sourced market data           | 0003-DECISION-fn-cost-anchor.md                     |
| 4   | FN cost split by employee tier             | 0004-DECISION-fn-cost-tier-split.md                 |
| 5   | FP trust erosion quantified                | 0005-DECISION-fp-trust-quantified.md                |
| 6   | Legal-safety population exclusions         | 0006-DECISION-legal-safety-exclusions.md            |
| 7   | Throughput reframed as participation       | 0007-DECISION-throughput-participation.md           |
| 8   | EU AI Act as structural floor              | 0008-DECISION-eu-ai-act.md                          |
| 9   | Classification, not prediction             | 0009-DECISION-classification-not-prediction.md      |
| 14  | Phase 1 closure (D14, D15)                 | 0014-DECISION-d15-phase1-closure.md                 |
| 16  | XGBoost disqualified (MFS SHAP 97.4%)      | 0015-DECISION-d16-xgboost-disqualification.md       |
| 17  | Random Forest Sprint 1 model               | 0016-DECISION-d17-phase5-pick.md                    |
| 18  | Floor check dispositions (Brier 0.0844)    | 0017-DECISION-d18-floor-check-dispositions.md       |
| 19  | Pipeline integrity (fakeEMP_007 removed)   | 0018-DECISION-d19-pipeline-integrity-clearance.md   |
| 20  | Deployment architecture confirmed          | 0019-DECISION-d20-deployment-architecture.md        |
| 24  | RE-DO: interaction features, Critical 0.90 | 0025-DECISION-post-redo-model-assessment.md         |
| 25  | FP breach at 0.30 → RE-DO required         | 0024-DECISION-redteam-floor-breach-dispositions.md  |
| 26  | Threshold locked at 0.35                   | 0026-DECISION-phase7-dispositions-threshold-lock.md |
| 27  | GO with four conditions                    | 0027-DECISION-phase8-go-nogo.md                     |

---

## 10. Sprint 2 Opens With

1. **Gender fairness audit on full Kaggle dataset (~22,750 rows)** — pre-registered commitment (D11, D17, D26). NOT optional.
2. **Per-tier Brier validation on full dataset** — Phase 7 Sweep 4 flagged Moderate/High tier Brier failures (n=1 each on 12 rows). Full dataset per-tier Brier against 0.15 floor. If breached: Platt scaling applied (D26).
3. **Threshold B senior validation on HRIS data** — THRESHOLD_B remains 0.30 provisional. Pilot customer's HRIS data must validate 10% FN and 20% FP targets on senior employees before confirmation.
4. **Ensemble averaging across 3 seeds** — S1-F1 mitigation for tier-boundary instability.
5. **resource_allocation missingness monitor** — S2-F2 mitigation. Flag SHAP quality if >15% missing.

---

## 11. Lessons Learned (Phase 9)

### Transferable

- **T1:** Pre-registration after seeing the leaderboard is rationalisation, not constraint. Sprint 2 pre-registration must be written before the leaderboard is read.
- **T2:** SHAP concentration validated on <1000 rows is a hypothesis, not a finding. Full dataset validation required.
- **T3:** Threshold adjustment is a symptom response. Fix the model first (the RE-DO reduced FP without requiring the threshold to move as far as initially proposed).

### Domain-Specific

- **D1:** Self-report burnout signals have adversarial non-response. Most burned-out employees least likely to complete assessment.
- **D2:** Buyer's motivation (HR Director, reduced turnover) structurally misaligned with user's need (employee, privacy/agency). Product must serve both or participation collapses.

Full lessons: `workspaces/Oraclaire/playbook/appendix-a-lessons.md`
