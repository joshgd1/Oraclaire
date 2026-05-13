---
name: oraclaire-product-knowledge
description: Oraclaire burnout classifier decisions. Use for population, costs, regulation, tiers, participation.
tools: [Read, Grep, Glob]
---

# Oraclaire Product Knowledge — Phase 1 Frame

Read-only institutional knowledge agent. Any future agent working on Oraclaire MUST consult this before making design, model, or product decisions. All decisions below are canonical; contradictions require a new journal entry overturning the prior decision.

---

## 1. Product Identity

Oraclaire is a **classification product**, not a predictive product.

- **Output:** 4-tier burnout risk classification per employee per assessment cycle (Low / Moderate / High / Critical)
- **What it measures:** Current burnout risk state as of the assessment date
- **What it does NOT do:** Predict future burnout onset, claim longitudinal validity, or forecast risk over a time window
- **Model family (pre-selected):** XGBoost + SHAP (architecture decisions deferred to Phase 5)
- **Validation type:** Cross-sectional (single-timepoint classification)
- **Inter-cycle window:** Draft 30 days — assessment recalibration window, not prediction horizon. Founder owns this parameter.

**DO:**

- Frame the product as "classify current burnout risk accurately and transparently"
- Use trajectory analysis across cycles (improved / held / worsened) as the temporal dimension

**DO NOT:**

- Use "predict", "prediction", "predictive", or "forecast" in any product description or model documentation
- Claim the model predicts burnout before it happens
- Adopt any prediction window (14, 30, 60, 90 days) — the Kaggle MBI dataset is cross-sectional and cannot support temporal prediction claims
- Add disclaimers like "preliminary, not longitudinally validated" to soften a prediction claim — reframe as classification instead

**Why:** Cross-sectional survey data cannot support longitudinal prediction claims. The literature's best-performing burnout ML models classify current severity from single-timepoint data. A classification framing is stronger because it can be defended. Origin: journal/0009.

---

## 2. Population Rules — Two-Tier Scoring

### Tier 1 — Individual Scoring (Opt-In Only)

- Employees must actively opt in through the Oraclaire consent screen during onboarding
- Consent is informed: employees see what data is collected, how it is used, who can see their score
- Withdrawal is immediate and total: individual scores suppressed from everyone — including the employee's own history view
- No retroactive re-activation: withdrawal clears visibility; re-opting-in starts fresh

### Tier 2 — Team Aggregate Only (Default)

- Employees who have not opted in appear only in team-level aggregate scores
- Minimum team size: 5. Below 5 members, aggregate scores are suppressed entirely
- HR sees team trends only — no individual-level data for Tier 2 employees
- Tier 2 employees see no scores unless they opt in

### Operational Exclusions (Both Tiers)

- Test accounts and API-generated submissions
- Employees currently on medical leave (including mental health leave)
- Employees already flagged and receiving active support through a structured intervention program
- Contractors and temporary staff without a defined assessment pathway

### Legal-Safety Exclusions (Both Tiers)

Employees in these categories are excluded from individual scoring entirely — a score in these contexts creates discoverable data in employment disputes:

- Employees currently on a Performance Improvement Plan (PIP)
- Employees under active disciplinary review
- Employees in a protected category process: ADA accommodation, FMLA leave, workers' compensation claim
- Employees who have filed a workplace complaint or grievance within the last 90 days (cooldown window, founder-owned)

**DO:**

- Exclude from scoring entirely (data must not be generated, not merely suppressed from display)
- Design population exclusions as a Phase 1 parameter that affects FN/FP arithmetic

**DO NOT:**

- Score excluded employees and suppress only the HR view — a subpoena reaches the database, not the UI
- Treat legal-safety exclusions as a Phase 2 compliance afterthought — they change the model's training population
- Use an opt-out model — under PDPA/GDPR employment context, consent under employment relationships is considered coerced

**Why:** A burnout score generated during a PIP or ADA process will be subpoenaed and becomes evidence for either side. The two-tier structure is designed to satisfy PDPA consent requirements. Origin: journal/0001, journal/0006.

---

## 3. Cost Terms

### FN Cost — Split by Employee Tier

The FN cost range is driven by seniority and replacement difficulty, not a single average.

| Tier                    | % Workforce | Cost/Year | Daily Cost Each |
| ----------------------- | ----------- | --------- | --------------- |
| Junior / IC             | 70%         | $4,000    | $10.96          |
| Senior / Lead / Manager | 30%         | $21,000   | $57.53          |

**Daily FN cost formula (split, 500-employee company):**

```
Daily FN = (87.5 x r x $4,000 + 37.5 x r x $21,000) / 365
         = $3,116.44 x r
```

- r (FN rate) is a **founder-owned Phase 5 call**, not set in this frame
- At 500 employees, daily FN exposure cannot exceed $10,000 regardless of r
- The $10K/day threshold hits at ~1,000 employees (senior case) or ~2,500 employees (junior case)

**DO:**

- Present FN cost as two tiers with driver explanation (seniority, replacement difficulty)
- Show sensitivity at both bounds ($4K and $21K)
- Credit the source: market landscape analysis, not salary assumptions

**DO NOT:**

- Average to a single midpoint ($12,500) — hides the real trade-off
- Derive FN cost from assumed salary figures ($60K salary x 34% Gallup)
- Present the $4K–$21K range without explaining what drives the spread

**Why:** A single average hides the asymmetric failure mode: missing a senior employee costs 5x more than missing a junior. If the model performs differently across tiers, the aggregate hides the failure that matters most. Origin: journal/0003, journal/0004.

### FP Cost — Participation Decay as Structural Cost

**Visible cost:** $15 per false positive (30-min HR check-in at loaded labour cost)

**Structural cost — participation decay (the real cost):**

| FP Rate             | Effect                               | FP Cost                    |
| ------------------- | ------------------------------------ | -------------------------- |
| <= 20%              | Participation stable                 | ~$15/event                 |
| > 20%               | Participation decay begins           | $15 + data quality erosion |
| > 30%               | 40–60% participation drop by cycle 3 | Model failure              |
| < 50% participation | Biased sample, cannot retrain        | Product death spiral       |

**Critical mechanism:** Burned-out employees are the most likely to disengage after a false positive — they are already overwhelmed, and a pointless check-in is the last straw. FP does not just waste time; it selectively destroys signal on the highest-value detection targets.

**FN:FP cost ratio:** ~9:1 at base case (structural asymmetry: $4K/year vs $15/check-in).

**DO:**

- Present FP cost as a compounding structural constraint, not just a dollar figure
- Justify a high-precision operating point economically (prevents data death spiral), not just ethically
- Keep FP rate below 20% as the structural survival threshold

**DO NOT:**

- Reduce FP cost to $15/check-in alone
- Tune for recall at the expense of precision — it blinds the model to the people it most needs to find
- Fabricate a specific dollar figure for trust erosion

**Why:** The real FP cost is the erosion of trust that causes participation to collapse, destroying the data the model needs to function. The Microsoft Productivity Score 2020 precedent documents this pattern. Origin: journal/0002, journal/0005.

---

## 4. Throughput — Reframed as Participation Rate

**Ceiling:** 40% sustained participation over 12 assessment cycles.

**Ceiling owner:** Product Owner (founder).

The original framing (10,000 submissions/day server capacity) was the wrong unit of analysis. For a 500-person company with monthly assessments, throughput is a human behavior constraint, not a server constraint.

**Why 40% is the floor:**

- Below 40% participation, the sample is no longer representative of the workforce
- Below 30%, the model cannot reliably distinguish burnout signal from self-selection bias
- The model needs longitudinal data (same employees across multiple cycles) for trajectory analysis

**This reframes every engineering decision:** The bottleneck is not how fast the product scores — it is how many people are willing to be scored. Feature design, UX, communication, and intervention quality all become throughput levers.

**DO:**

- Frame throughput as sustained participation rate
- Design features that increase willingness to participate

**DO NOT:**

- Frame throughput as server capacity or submissions per day
- Assume server capacity is the binding constraint for a 500-person company

**Why:** Participation drops from 30–50% in month one to 5–10% by month six when the tool does not deliver personal value. A server processing 10K submissions/day that receives 20 submissions is a participation failure, not a throughput success. Origin: journal/0007.

---

## 5. Regulatory Floors

### Singapore PDPA — Mental Health Data Hard Floor

- Structural compliance floor for collection, use, and disclosure of personal data
- Heightened obligations around health data (includes mental health / burnout indicators)
- The two-tier scoring model (Tier 1 opt-in + Tier 2 aggregate) is designed to satisfy PDPA consent requirements
- Detailed compliance specification belongs to Phase 2
- PDPA gates what data can be collected, how consent is obtained, and whether cross-border transfer is permitted

### EU AI Act — High-Risk Employment AI (Annex III)

Automated scoring in employment contexts is high-risk AI. Applies to any Oraclaire customer with EU-based employees — not just EU-headquartered companies.

**Hard constraint — human oversight for Critical tier:**

- Critical-tier flags MUST require a human review step before any intervention or escalation is triggered
- The system MUST support a conformity assessment documenting how scores are generated, what data flows in, and how decisions are audited
- Transparency obligation: employees have the right to know they are being scored and how scoring works
- SHAP satisfies the transparency requirement — each score is decomposable into contributing features

**DO:**

- Design the intervention workflow with a human gate at the Critical tier from day one
- Apply human oversight only to Critical tier (not all tiers — proportional per the Act)

**DO NOT:**

- Defer this to Phase 2 — retrofitting requires redesigning the escalation pipeline
- Apply human review to every tier — it bottlenecks the intervention pipeline and makes the product unusable at scale
- Address only at the documentation level — the Act requires both documentation AND operational mechanisms

**Why:** If the system is designed without this constraint, the intervention workflow (Phase 3) must be redesigned. Adding it later is a structural retrofit. Origin: journal/0008.

---

## 6. Decision Log Index

All 9 Phase 1 decisions with one-line summaries. Each links to its full journal entry in `workspaces/Oraclaire/journal/`.

| #   | Decision                             | One-Line Summary                                                                          | Journal Entry                                    |
| --- | ------------------------------------ | ----------------------------------------------------------------------------------------- | ------------------------------------------------ |
| 1   | Two-tier scoring model               | Individual opt-in scoring + team aggregate default; PDPA-compliant consent architecture   | `0001-DECISION-two-tier-scoring.md`              |
| 2   | FP cost includes participation decay | Structural trust-erosion cost, not just $15 check-in; death spiral above 20% FP           | `0002-DECISION-fp-trust-erosion.md`              |
| 3   | FN cost uses sourced market data     | $4K–$21K from market landscape, not salary assumptions; defensible in presentation        | `0003-DECISION-fn-cost-anchor.md`                |
| 4   | FN cost split by employee tier       | Junior $4K (70%) vs Senior $21K (30%); driven by replacement difficulty                   | `0004-DECISION-fn-cost-tier-split.md`            |
| 5   | FP trust erosion quantified          | Participation decay thresholds: stable <=20%, decay >20%, death spiral >30%               | `0005-DECISION-fp-trust-quantified.md`           |
| 6   | Legal-safety population exclusions   | PIP, ADA, FMLA, workers comp, grievance cooldown; prevent discoverable data               | `0006-DECISION-legal-safety-exclusions.md`       |
| 7   | Throughput reframed as participation | 40% sustained participation over 12 cycles, not server capacity                           | `0007-DECISION-throughput-participation.md`      |
| 8   | EU AI Act as structural floor        | Human oversight at Critical tier; SHAP for transparency; Phase 1 architectural constraint | `0008-DECISION-eu-ai-act.md`                     |
| 9   | Classification, not prediction       | Cross-sectional classifier, not predictive model; data cannot support temporal claims     | `0009-DECISION-classification-not-prediction.md` |

---

## 7. Founder-Owned Parameters (Not Decided in This Frame)

These parameters are deferred to the founder for final specification:

- Inter-cycle window length (currently draft 30 days)
- FN rate r — Phase 5 threshold decision
- FP rate ceiling — must stay below 20% per Decision 2
- Burnout prevalence confirmation (currently 25%)
- Auto-flag ceiling
- Risk-tier thresholds (Low/Moderate/High/Critical boundaries)
- Employee tier split confirmation (currently 70% junior / 30% senior)
- Participation rate floor confirmation (currently 40% sustained)
- Grievance cooldown window (currently 90 days)
