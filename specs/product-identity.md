# Product Identity — What Oraclaire Is and Is Not

**Authority:** This spec is the single source of truth for Oraclaire's product identity: what it does, what it does not do, how it classifies, what model it uses, and how it validates. Every question about the product's capabilities, claims, and boundaries resolves here.

**Origin:** Phase 1 Frame sections 1, 3, and 5; Challenge D4 (journal/0009).

**Cross-references:**

- The population that gets classified is defined in `population-and-scoring.md`.
- The cost model for misclassification is in `cost-model.md`.
- The regulatory constraints (human oversight, transparency) that shape the product's operating model are in `regulatory-constraints.md`.

---

## 1. Product Identity — Classification, Not Prediction

### The Core Distinction

Oraclaire is a **classification** product, not a **predictive** product.

- **Classification:** Each employee is classified into one of four burnout risk tiers (Low / Moderate / High / Critical) based on their current state at the time of assessment.
- **NOT Prediction:** Oraclaire does not predict whether an employee will burn out in the future. It does not claim a temporal horizon. It does not forecast.

This distinction is material:

- Classification requires **cross-sectional validation** — validate the model against held-out data from the same timepoint.
- Prediction requires **longitudinal validation** — validate the model against outcomes measured at a future timepoint.

Oraclaire is designed and validated as a classifier. The Kaggle MBI survey dataset supports cross-sectional classification of current burnout severity — it does not support temporal prediction of future burnout onset.

### Why the 30-Day Predictive Window Was Rejected

The original draft included a 30-day predictive horizon ("burnout risk over the next 30 days"). This was rejected for three specific reasons:

**Reason 1 — Too short to be actionable.** A manager who receives a burnout alert needs to: have a 1:1, escalate to HR, design an intervention, and see whether it worked. The enterprise intervention cycle alone is 6–9 months (user personas). 30 days is not enough time for the alert to be useful.

**Reason 2 — False precision claim.** The market landscape warned that predictive windows require longitudinal validation data. The Kaggle MBI survey dataset is cross-sectional — it measures burnout at a single point in time. Claiming predictive power from cross-sectional data is a claim that will not survive scrutiny from a methods-aware reviewer.

**Reason 3 — Literature does not support it.** The best-performing burnout ML models in the literature classify current burnout severity from single-timepoint MBI data. They do not predict future onset.

### The Stronger Position

The classification framing is stronger than the prediction framing:

- "We classify current burnout risk with Random Forest and SHAP — accurately, transparently, and without claiming to predict the future from data that cannot support that claim" is more credible than "we predict burnout 30 days before it happens."
- Classification can be defended. Prediction from cross-sectional data cannot.

### What This Means for Product Claims

- The product classifies current burnout risk state.
- The product tracks trajectory across cycles (improved / held / worsened).
- The product does NOT predict future burnout onset.
- Trajectory tracking is NOT prediction under another name — it compares two classification outputs, not a classification against a future measured outcome.

### Competitive Acknowledgement

Some competitors (Viva Insights) have behavioral time-series data (calendar patterns, email volume over time) that genuinely supports prediction. Oraclaire, with survey-based data, does not have this advantage. The classification framing acknowledges this competitive gap honestly.

---

## 2. The Four-Tier Burnout Risk Scorer

### Tiers

| Tier     | Meaning                                | Action Implication                                                                       |
| -------- | -------------------------------------- | ---------------------------------------------------------------------------------------- |
| Low      | Current burnout risk is low            | No action needed                                                                         |
| Moderate | Some burnout indicators present        | Monitor; may benefit from preventative support                                           |
| High     | Significant burnout indicators present | HR outreach recommended; intervention planning                                           |
| Critical | Severe burnout indicators present      | Human review gate required before any action (see `regulatory-constraints.md` section 2) |

### Risk-Tier Thresholds

The boundaries between tiers (what score maps to Low vs Moderate vs High vs Critical) are the founder's call. Not proposed here. These thresholds determine the precision-recall trade-off and directly affect the cost model — see `cost-model.md`.

### Auto-Flag Ceiling (Organisational Risk Threshold)

Per D14-10 and D15-2, the auto-flag ceiling is locked at 20% High+Critical combined. When a team's combined High+Critical rate exceeds this ceiling for two consecutive weekly pulses, or a single quarterly CBI cycle, individual alerts for that team are suppressed and a single organisational risk report is generated for HR. The ceiling prevents model-driven alarm fatigue and forces systemic response over individual flagging. Configurable via deployment parameter.

---

## 3. Model Family — Random Forest + SHAP (Sprint 1)

### Confirmed — D17 (2026-05-14)

Random Forest + SHAP is the Sprint 1 model, confirmed via Phase 5 model selection (journal/0016). XGBoost was disqualified in D16 (MFS SHAP 97.4% — fatigue detector, not burnout detector). Random Forest was the only candidate with genuine multi-signal balance (tenure 28.5%, MFS 25.3%, workload 24.5%) and no artifact contamination on the 13-row validation sample.

**Sprint 1 hyperparameters:** n_estimators=100, max_depth=5, random_state=42.

**Locked threshold (D26):** THRESHOLD_A = 0.35 (general population). Originally 0.30 provisional; raised after Phase 7 RE-DO (D24-D26) reduced FP from 20.1% to 16.6%. THRESHOLD_B = 0.30 (senior tier, provisional — requires HRIS validation in Sprint 2). Drift range: (0.30, 0.40).

**Feature set (10 features after RE-DO, D24):** 8 original features after Designation multicollinearity drop (r=0.8865 with seniority_tier) + 2 interaction terms (`tenure_fatigue`, `tenure_workload`) added in Phase 7 RE-DO to reduce MFS SHAP dominance from 46.9% to 29.9%. See `workspaces/Oraclaire/journal/phase_3_features.md` for the full feature classification.

**Critical boundary:** 0.90 (raised from 0.75 in D24 to meet the 5% Critical population cap).

**MFS SHAP post-RE-DO:** 29.9% — below the 40% gate (D16).

**FP rate at 0.35:** 16.6% — 1.6pp above the pre-registered 15% ceiling, accepted within the 5-point buffer to the 20% participation decay threshold (D26).

**DPO hard gate:** SHAP output format must be reviewed by a qualified legal/DPO professional before first customer deployment (D17, D27 Condition 1). Employee UI locked until sign-off.

**Deployment status:** GO (D27) with four conditions: DPO sign-off, pilot-only, no performance claims, Sprint 2 items communicated.

**Sprint 2 re-entry:** XGBoost re-enters candidate pool on expanded behavioral feature layer (D16b), MFS SHAP must be below 40%.

### SHAP as Transparency Mechanism

SHAP (SHapley Additive exPlanations) serves a dual purpose:

1. **Interpretability:** Each score can be decomposed into contributing features. For any employee classified as "High" burnout risk, SHAP shows which factors (e.g., exhaustion score, cynicism score, work hours) drove the classification and by how much.

2. **Regulatory compliance:** SHAP satisfies the EU AI Act transparency requirement (see `regulatory-constraints.md` section 2) by making the ML model interpretable. This is the response to the ethical risk analysis recommendation: "prefer transparent, rule-based scoring over ML models." SHAP delivers interpretability without abandoning predictive power.

3. **Human review support:** When a Critical-tier flag triggers the human review gate (see `regulatory-constraints.md` section 2), the reviewer receives the SHAP decomposition as context for their override decision.

4. **Employee right to explanation:** Any employee can receive a human-readable explanation of their score derived from SHAP output.

---

## 4. Assessment Recalibration Window

### Definition

The "horizon" is the **assessment recalibration window** — the interval between classification cycles. Draft: 30 days.

- Each classification informs interventions for the inter-cycle window.
- The following cycle's classification measures whether the risk tier improved, held, or worsened.
- This is NOT a prediction window — it is the operational cadence at which the classification is refreshed.

### Inter-Cycle Window Length

Locked at 30 days per D14 (journal/0013). Monthly CBI (19 items) + weekly pulse (single CBI item by rotation) provides the operational cadence. This is an operational parameter, not a predictive claim.

### Trajectory Analysis Across Cycles

Trajectory analysis replaces prediction as the temporal dimension:

- **Improved:** Previous cycle was Moderate/High/Critical, current cycle is lower.
- **Held:** Same tier across consecutive cycles.
- **Worsened:** Previous cycle was Low/Moderate, current cycle is higher.

Trajectory requires longitudinal data (same employees across multiple cycles). Participation below 40% means insufficient repeat-participation for meaningful trajectory analysis. See `population-and-scoring.md` section 4 for the participation rate floor.

### Why the Enterprise Cycle Matters

The enterprise intervention cycle (6–9 months procurement, manager 1:1s, escalation, intervention design, impact measurement) is much longer than the assessment recalibration window. The assessment window is not the intervention window — the assessment window feeds data into the intervention cycle at regular intervals.

---

## 5. Throughput Ceiling — Participation Rate

### The Real Constraint

The throughput ceiling is **40% sustained participation over 12 assessment cycles**, owned by the Product Owner (founder).

The original framing (10,000 submissions/day server capacity) was the wrong unit of analysis. For a 500-person company with monthly assessments, server capacity is trivially handled. The binding constraint is human behavior — whether enough people participate to keep the model's training data representative.

### Why 40%

- Below 40% participation, the sample is no longer representative of the workforce.
- Below 30%, the model cannot reliably distinguish burnout signal from self-selection bias.
- The model needs longitudinal data (same employees across multiple cycles) to detect trajectory. Participation below 40% means insufficient repeat-participation for trajectory analysis.

### What This Reframes

This reframes every engineering decision: the product's bottleneck is not how fast it scores but how many people are willing to be scored. Feature design, UX, communication, and intervention quality all become throughput levers.

### Participation Measurement Caveats

- Participation rate is harder to measure than submissions/day. It requires tracking unique respondents across cycles, which introduces its own data-collection requirement.
- Server capacity is a real constraint at enterprise scale (10,000+ employees), but it is an engineering concern, not a frame-level parameter.

---

## 6. HRIS Integration Dependency

Several spec features require HRIS (Human Resource Information System) integration to enforce automatically:

- Operational exclusions (medical leave status, active intervention program) — see `population-and-scoring.md` section 2.
- Legal-safety exclusions (PIP status, disciplinary review, ADA/FMLA/workers comp, grievance filing) — see `population-and-scoring.md` section 3.
- Participation tracking across cycles — requires employee identity linkage.

Without HRIS integration, these features require manual enforcement, which introduces human error and reduces reliability.

---

## 7. Parameters Locked by D14/D15

| Parameter                 | Value                                                     | Decision              |
| ------------------------- | --------------------------------------------------------- | --------------------- |
| Inter-cycle window        | 30 days (monthly CBI + weekly pulse)                      | D14 (journal/0013)    |
| Auto-flag ceiling         | 20% High+Critical combined                                | D14-10, D15-2         |
| Auto-flag trigger         | 2 consecutive weekly pulses or single quarterly CBI       | D15-2                 |
| Participation targets     | 20% Sprint 1, 40% architectural                           | D7, D14               |
| Model family              | Random Forest + SHAP (Sprint 1, confirmed D17)            | D16, D17              |
| Risk tiers                | Low / Moderate / High / Critical                          | Pre-selected          |
| Threshold A (locked)      | 0.35 (drift range 0.30–0.40)                              | D26                   |
| Threshold B (provisional) | 0.30 (senior tier, requires HRIS validation)              | D17, D26              |
| Critical boundary         | 0.90 (raised from 0.75 in D24)                            | D24                   |
| Two-threshold serving     | A: general FN 15%/FP 15%; B: senior FN 10%/FP 20%         | D11, D14              |
| Feature set               | 10 active (8 original + tenure_fatigue + tenure_workload) | Phase 3, Phase 4, D24 |
| MFS SHAP dominance        | 29.9% (below 40% gate)                                    | D24 RE-DO             |
| FP rate at 0.35           | 16.6% (1.6pp above ceiling, accepted within decay buffer) | D26                   |
| Deployment status         | GO with four conditions (D27)                             | D27                   |

## 8. Open Questions Remaining

- [ ] Risk-tier thresholds (exact score boundaries for Low/Moderate/High/Critical).
- [ ] Should the product explicitly differentiate from competitors with predictive capability (Viva Insights), or position classification as the superior approach?
- [ ] If behavioral signals (calendar patterns, communication frequency) are added later, should the framing be revisited to upgrade from classification to prediction — or is classification the permanent product identity?
