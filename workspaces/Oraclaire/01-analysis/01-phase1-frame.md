# Phase 1 — Frame: Oraclaire Burnout Risk Scorer

**Sprint:** Sprint 1 — Employee Burnout Risk Scorer (4 tiers: Low / Moderate / High / Critical)
**Model family (pre-selected, not decided here):** XGBoost + SHAP
**Date:** 2026-05-13
**Status:** CLOSED — D15 locked, Phase 1 complete (rev 4)

---

## 1. Target (CHALLENGE D4 — Classification, Not Prediction)

Oraclaire classifies each employee into one of four burnout risk tiers (Low / Moderate / High / Critical) per employee per assessment cycle, reflecting the employee's **current** risk state as of the assessment date.

This is a **classification** product, not a predictive product. The distinction is material: classification requires cross-sectional validation. Prediction requires longitudinal validation. Oraclaire is designed and validated as a classifier. The Kaggle MBI survey dataset supports cross-sectional classification of current burnout severity — it does not support temporal prediction of future burnout onset.

---

## 2. Population — Two-Tier Scoring (DECISION 1, CHALLENGE 3)

### Tier 1 — Individual Scoring (Opt-In Only)

Employees who actively opt in through the Oraclaire consent screen during onboarding receive individual-level burnout risk scores.

- **Opt-in is explicit and informed** — employees see what data is collected, how it's used, who can see their score
- **Withdrawal is immediate** — if an employee withdraws consent, their individual scores are suppressed from everyone, including their own history view. Not just from HR. From everyone
- **No retroactive re-activation** — withdrawal clears visibility; re-opting-in starts fresh

### Tier 2 — Team Aggregate Only (Default)

Employees who have not opted in appear only in team-level aggregate scores.

- **Minimum team size: 5** — if fewer than 5 members, aggregate scores are suppressed entirely
- **HR sees team trends only** — no individual-level data for Tier 2 employees
- **Employees see nothing** — Tier 2 employees do not see scores unless they opt in

### Explicit Exclusions (Both Tiers)

**Operational exclusions:**

- Test accounts and API-generated submissions
- Employees currently on medical leave (including mental health leave)
- Employees already flagged and receiving active support through a structured intervention program
- Contractors and temporary staff without a defined assessment pathway

**Legal-safety exclusions (CHALLENGE 3, 2026-05-13):**

Employees in the following categories are excluded from individual scoring entirely — not because the model cannot score them, but because a score in these contexts creates discoverable data in employment disputes:

- Employees currently on a Performance Improvement Plan (PIP)
- Employees under active disciplinary review
- Employees in a protected category process: ADA accommodation, FMLA leave, workers' compensation claim
- Employees who have filed a workplace complaint or grievance within the last 90 days (cooldown window)

**Rationale:** A burnout risk score generated during a PIP or ADA process will be subpoenaed. The score becomes evidence — either for the employer ("see, they were burned out, not discriminated against") or for the employee ("the company knew I was at risk and took adverse action anyway"). Either way, the score creates liability that the product did not intend. This exclusion is a population definition that changes the FN/FP arithmetic, not a compliance afterthought.

### Participation Implication

This two-tier structure means FN/FP arithmetic splits into two populations. The model may need separate calibration per tier, or a single model scoring everyone with output routed differently based on tier membership. Architecture decision belongs to Phase 5.

---

## 3. Horizon — Assessment Recalibration Window (CHALLENGE D4)

Oraclaire classifies each employee's current burnout risk tier at each assessment cycle. The classification informs interventions for the inter-cycle window (draft: 30 days). The following cycle's classification measures whether the risk tier improved, held, or worsened.

**This is a CLASSIFICATION product, not a PREDICTIVE product.** The distinction is material: classification requires cross-sectional validation. Prediction requires longitudinal validation. Oraclaire is designed and validated as a classifier.

**Why the 30-day predictive window was rejected:**

- The enterprise intervention cycle alone exceeds 30 days (user personas §2C: 6–9 months procurement, manager needs time for 1:1, escalation, intervention design, impact measurement)
- A 30-day prediction window claims longitudinal validity that a cross-sectional MBI survey dataset cannot support. This claim would not survive scrutiny
- The best-performing burnout ML models in the literature (research §3.1) classify current burnout severity from single-timepoint MBI data — they do not predict future states
- Reframing as classification is a stronger product position: "we classify current burnout risk accurately, transparently, and without claiming to predict the future from data that cannot support that claim" is more credible than "we predict burnout 30 days before it happens"

---

## 4. Cost Terms

### FN Cost — Split by Employee Tier (DECISION 3, CHALLENGE 1)

**Anchor:** $4,000–$21,000 per burned-out employee per year (sourced: market landscape §4). The spread is not random — it is driven by seniority and replacement difficulty.

> A junior analyst costs closer to $4,000 to replace. A senior engineer or team lead costs closer to $21,000. (Rationale: ethical risk analysis §3.4 — seniority and replacement difficulty drive the upper end.)

**Split for a 500-employee company (UPDATED — DECISION D14, changed from 70/30 to 60/40):**

| Employee tier           | % of workforce | Count | Burnout prevalence | Burned-out count | Cost/year | Daily cost each |
| ----------------------- | -------------- | ----- | ------------------ | ---------------- | --------- | --------------- |
| Junior / IC             | 60%            | 300   | 25%                | 75               | $4,000    | $10.96          |
| Senior / Lead / Manager | 40%            | 200   | 25%                | 50               | $21,000   | $57.53          |

**Why a single average ($12,500) was rejected:** A midpoint obscures the real trade-off. A model that misses a junior employee costs $4K. Missing a senior team lead who takes 6 months to replace costs $21K. If the model performs differently across these populations — which it likely will, because senior employees have different burnout signal patterns — the aggregate average hides the failure mode that matters most.

**Why 60/40 instead of 70/30 (DECISION D14):** Oraclaire's target market is knowledge-work organisations (tech, professional services, function-heavy enterprise) where the senior IC and manager layer is 40-45% of headcount, not 30%. The 70/30 split understated FN cost exposure. The 60/40 split makes the ROI story more conservative — a CFO who pushes back on the cost model sees conservative assumptions, not optimistic ones.

**Daily FN cost formula (corrected — DECISION D10, updated constant — DECISION D14):**

```
Daily FN = $3,698.63 × [(1 - e) × r + e]
```

Where:

- **r** = FN rate on the scorable population (model misses this fraction of scorABLE burned-out employees)
- **e** = fraction of burned-out employees in excluded categories (PIP, ADA, FMLA, workers comp, grievance, disciplinary — never scored, always missed)
- **$3,698.63** = daily cost constant from tier-split: `(75 × $4,000 + 50 × $21,000) / 365`

The original formula (`$3,116.44 × r`) assumed all 125 burned-out employees were scorable. The legal-safety exclusions (Decision 0006) remove a fraction `e` of burned-out employees from the scorable population entirely — their FN rate is 1.0 by design. The corrected formula separates model errors on the scorable population (`r`) from the irreducible cost of employees the model is never allowed to see (`e`).

**Properties:**

- When e = 0: reduces to `$3,698.63 × r` (no exclusions)
- When r = 0: gives `$3,698.63 × e` (perfect model still misses the excluded fraction)
- **Irreducible FN floor** = `$3,698.63 × e` — no model improvement can reduce it

**Known simplification:** The formula treats `e` as static. In practice, `e` compounds upward over cycles because FP-driven participation decay (Decision 0005) causes burned-out employees to disengage from the scorable population, functionally joining the excluded population. A third variable for this decay is correct in theory but over-engineered for Sprint 1. The simplification is acknowledged.

**Sensitivity table (e = 0.10 conservative, e = 0.20 stressed — DECISION D10, constant updated D14):**

| r (FN rate) | e = 0.10 Daily | e = 0.10 Annual | e = 0.20 Daily | e = 0.20 Annual | Original formula Daily | Original formula Annual |
| ----------- | -------------- | --------------- | -------------- | --------------- | ---------------------- | ----------------------- |
| 0.05        | $537           | $195,906        | $890           | $324,678        | $185                   | $67,500                 |
| 0.10        | $703           | $256,438        | $1,036         | $378,110        | $370                   | $135,000                |
| 0.15        | $868           | $316,970        | $1,183         | $431,543        | $555                   | $202,500                |
| 0.20        | $1,036         | $378,110        | $1,333         | $486,630        | $740                   | $270,000                |
| 0.50        | $1,664         | $607,403        | $1,849         | $674,975        | $1,849                 | $674,975                |
| 1.00        | $3,699         | $1,349,950      | $3,699         | $1,349,950      | $3,699                 | $1,349,950              |

**Irreducible FN floor:**

| e    | Daily floor | Annual floor |
| ---- | ----------- | ------------ |
| 0.10 | $370        | $134,995     |
| 0.20 | $740        | $269,990     |

e = **0.10 (conservative) / 0.20 (stressed) — founder placeholder, not validated** (DECISION D10). First number measured at every deployment — added to onboarding checklist (DECISION D14). FMLA ~2-3% workforce, PIP ~3-5% at healthy companies, ADA/workers comp/grievance ~2-4% additional; intersection with burnout prevalence skews excluded group toward burnout by definition.

r = **15% general population, 10% senior tier** (DECISION D14 — two-threshold architecture). The two-threshold design reflects the $4K/$21K cost asymmetry: higher FP tolerance (20%) for senior staff is justified because a missed senior employee costs $21K versus $4K for junior.

### FP Cost — Participation Decay as Structural Cost (DECISION 2, CHALLENGE 2, UPDATED D14)

**Visible cost:** $15 per false positive (30-min HR check-in at loaded labour cost)

**FP ceiling (DECISION D14): 15% on High/Critical combined.** The FP ceiling applies specifically to the High and Critical tiers — the tiers that trigger HR action. FP at Low and Moderate is less damaging because those tiers do not trigger HR intervention. Trust erosion comes from being incorrectly flagged as High or Critical — not from being told Moderate when Low.

**FP ceiling by tier (D14 two-threshold architecture):**

| Tier                                       | FP ceiling | Rationale                                                                                           |
| ------------------------------------------ | ---------- | --------------------------------------------------------------------------------------------------- |
| General population, High/Critical combined | 15%        | 5-point buffer against model drift below the 20% death spiral threshold                             |
| Senior tier, High/Critical combined        | 20%        | Higher FP tolerance justified: false alarm = $15 check-in, false negative = $21K + replacement risk |

**Structural cost — participation decay (quantified):**

The real FP cost is not the check-in. It is the erosion of trust that causes participation to collapse, destroying the data the model needs to function.

**Mechanism (sourced: user personas §3A, ethical risk §1.3, enterprise audit §3):**

1. A healthy employee gets flagged as "High" or "Critical" burnout risk
2. HR schedules a check-in. The employee is confused — they feel fine
3. The employee tells colleagues. Trust in Oraclaire drops
4. Participation in the next assessment cycle declines
5. The employees most likely to disengage are the burned-out ones — they are already overwhelmed and a pointless check-in is the last straw
6. The model loses signal on precisely the people it needs to find
7. By cycle 3, if FP rate exceeded 20%, participation has dropped 40–60% (Microsoft Productivity Score 2020 precedent)
8. Below 50% participation, the sample is biased. The model trains on the engaged minority, not the at-risk population
9. The product churns itself out of existence — the enterprise audit calls this the "So What?" failure: dashboards nobody trusts, data nobody acts on, renewal gets cancelled

**FP cost is not a dollar figure. It is a compounding structural constraint:**

```
At FP rate ≤ 15% (High/Critical):  participation stable. FP cost ≈ $15 per event.
At FP rate > 20%:                   participation begins decay. FP cost = $15 + data quality erosion.
At FP rate > 30%:                   participation drops 40-60% by cycle 3. FP cost = model failure.
At participation < 50%:             product cannot retrain. Self-inflicted death spiral.
```

**Critical insight:** Burned-out employees are the most likely to disengage from the tool after a false positive. This means FP does not just waste time — it selectively destroys signal on the highest-value detection targets. The FP cost compounds because each false positive disproportionately removes burned-out employees from the training data.

**Why this matters for Phase 5:** A high-precision operating point is justified economically, not just ethically. Tuning for recall at the expense of precision doesn't just annoy healthy employees — it blinds the model to the people it most needs to find.

---

## 5. Throughput Ceiling — Two-Level Participation Targets (CHALLENGE 4, DECISION 13)

**Sprint 1 ship target:** **20% sustained participation**
**Architecture target:** **40% sustained participation over 12 assessment cycles**

**Ceiling owner:** Product Owner (founder)

The original framing (10,000 submissions/day server capacity) was the wrong unit of analysis. For a 500-person company with monthly assessments, throughput is not a server constraint. It is a human behavior constraint.

**Why two levels:** The ethical analysis says opt-in gives 30–50% initial adoption. The user personas say participation declines to 5–10% by month six when the tool does not deliver personal value. A 40% sustained target with no mechanism requires the product to be exceptional from day one — with no evidence it can achieve that. The two-level structure separates what Sprint 1 ships with (20%, supported by literature) from what the architecture must be designed to sustain (40%, supported by mechanisms).

**40% is the architecture floor** because:

- Below 40% participation, the sample is no longer representative of the workforce
- Below 30%, the model cannot reliably distinguish burnout signal from self-selection bias
- The model needs longitudinal data (same employees across multiple cycles) to detect trajectory — participation below 40% means insufficient repeat-participation for trajectory analysis

**20% is the Sprint 1 ship target** because:

- 20% sustained is achievable without the mechanisms that push toward 40%
- 20% is the floor where the model produces useful (if noisy) scores for a pilot deployment
- Below 20%, the model cannot reliably calibrate risk tiers

### Participation Mechanisms (DECISION 13)

Four mechanisms designed to close the gap between 20% (Sprint 1) and 40% (architecture target):

**A. Weekly pulse (10 seconds, 1 question)**

- Single question drawn from CBI item pool, rotating weekly
- Employee sees their own trend over time — personal value, not organisational surveillance
- No HR visibility on individual pulse responses — aggregated team trend only
- Purpose: maintain touch between monthly CBI cycles, reduce survey fatigue, provide longitudinal signal

**B. Monthly CBI (19 items, ~3 minutes)**

- Full Copenhagen Burnout Inventory — the validated instrument that is Sprint 1's primary signal
- This is the model's training data — the pulse supplements but does not replace it
- Employee sees their own scores with SHAP decomposition after each cycle

**C. Employee-first 24-hour data visibility gate**

- After each assessment cycle, employees see their own results 24 hours before HR
- Hardcoded delay — not configurable by the organisation
- Purpose: the employee owns their data first. This is not a feature — it is a participation mechanism. Employees who feel the tool works for them, not for HR, participate at higher rates

**D. SHAP-matched curated content library**

- After each assessment, employees receive 2–3 curated resources matched to their top SHAP factors
- Content mapped to risk tier: Low (self-guided), Moderate (team resources), High/Critical (professional pathways)
- Purpose: every assessment delivers immediate personal value, not just a score

**This reframes every engineering decision:** The product's bottleneck is not how fast it scores. It is how many people are willing to be scored. Feature design, UX, communication, and intervention quality all become throughput levers.

---

## Structural Constraints (Acknowledged, Not in Cost Math)

### Singapore PDPA — Mental Health Data Hard Floor

Singapore's Personal Data Protection Act imposes specific requirements on the collection, use, and disclosure of personal data, with heightened obligations around health data (which includes mental health / burnout indicators). This is a **structural compliance floor** — it gates what data can be collected, how consent is obtained, and whether cross-border transfer is permitted.

The two-tier scoring model (Decision 1) is designed to satisfy PDPA's consent requirements. Addressed in its own compliance specification during Phase 2.

### EU AI Act — High-Risk Employment AI (CHALLENGE 5)

Automated scoring in employment contexts is classified as a **high-risk AI system** under EU AI Act Annex III. This applies to any Oraclaire customer with EU-based employees.

**Hard constraint — human oversight for Critical tier:**

The EU AI Act requires human oversight mechanisms for high-risk AI systems. Oraclaire cannot produce a fully automated "Critical" burnout risk tier that triggers action without a human in the loop. Specifically:

- **Critical-tier flags must require a human review step** before any intervention or escalation is triggered
- The system must support a conformity assessment documenting how risk scores are generated, what data flows in, and how decisions are audited
- Transparency obligations: employees have the right to know they are being scored and how the scoring works
- This is not a Phase 2 compliance spec — it is a Phase 1 architectural constraint. The intervention workflow must be designed with a human gate at the Critical tier from day one. Adding this later requires redesigning the escalation pipeline.

**Why this was not deferred to Phase 2:** If the system is designed without this constraint and added later, the intervention workflow (Phase 3) must be redesigned. Better to acknowledge now and build around it.

### Model Family (Pre-selected)

XGBoost + SHAP. SHAP satisfies the EU AI Act transparency requirement by making the ML model interpretable — each score can be decomposed into contributing features. This is the response to the ethical risk analysis recommendation: "prefer transparent, rule-based scoring over ML models." SHAP delivers interpretability without abandoning predictive power.

Architecture decisions belong to Phase 5. This frame is silent on model design.

---

## Founder-Owned Calls — ALL LOCKED (DECISION D14, 2026-05-13)

- [x] Inter-cycle window length — **30 days** (monthly CBI + weekly pulse)
- [x] FN rate r — **15% general population, 10% senior tier** (two-threshold architecture)
- [x] Exclusion fraction e — **0.10/0.20 placeholders** confirmed; first measurement at deployment
- [x] FP rate ceiling — **15% on High/Critical combined** (DECISION D14; updates D2)
- [x] Burnout prevalence — **25%** (confirmed; pilot recalibrates)
- [x] Auto-flag ceiling — **20% default, configurable** (Organisational Risk Threshold)
- [x] Risk-tier thresholds — **principle locked: Critical ≤5%, High 10-15%, Moderate 20-25%, Low remainder** (exact numbers Phase 5)
- [x] Employee tier split — **60/40** (changed from 70/30 — knowledge-work target market)
- [x] Participation rate targets — **20% Sprint 1 / 40% architecture** (D13 confirmed)
- [x] Grievance cooldown — **90 days default, configurable per jurisdiction**

### D15 Resolutions (Phase 1 Closure)

- [x] Seniority identification — **configurable per deployment, HRIS default, self-reported fallback** (seniority_tier field, source: hris_derived or self_reported, null rejected)
- [x] Auto-flag ceiling scope — **High+Critical combined, triggers on two consecutive weekly pulse elevations OR single quarterly CBI above 20%** (not single-week spike)
- [x] Withdrawal cooling-off — **48-hour automatic, no HR notification, confirmation screen with cancel option**
- [x] Participation denominator — **scoreable population only** (excluded employees removed from denominator, exclusion count reported separately at category level)

### New Todos from D14

1. **e measurement as first onboarding step** — every deployment measures exclusion fraction before any other metric
2. **Grievance cooldown as configurable deployment parameter** — default 90 days, not hardcoded
3. **Auto-flag ceiling as configurable deployment parameter** — default 20%, named Organisational Risk Threshold
4. **Update D2 FP ceiling** — applies to High/Critical combined, not all tiers (recorded in journal D14)

### New Todos from D15

1. **seniority_tier field in employee schema** — values: junior / senior, source: hris_derived or self_reported, null not accepted
2. **Self-reported seniority question in opt-in consent flow** — required when HRIS field absent
3. **Update D14 Parameter 10** — auto-flag triggers on two consecutive weeks or single quarterly cycle, not single spike
4. **Withdrawal confirmation screen** — 48-hour countdown, cancel option, no HR notification, automatic suppression logic
5. **Exclusion count summary in HR dashboard** — category level only, no individual identification
