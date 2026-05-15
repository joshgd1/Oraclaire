# Phase 14 — Fairness Audit

Status: DEFERRED TO SPRINT 2
Deferred by: D11 Nuance 4, D17 Phase 5 pick, Phase 7 S3-F1
This is a planned phase — not a gap and not a skip.

---

## Why This Phase Is Deferred

A fairness audit done without the right foundations produces a defensive document, not a real audit.

Running it well requires three things Sprint 1 has not yet built:

1. **Sufficient deployment data** — the 12-row sample dataset does not have sufficient demographic representation to produce meaningful fairness metrics. A Gender fairness audit on 12 rows with 6 females and 6 males produces confidence intervals so wide they are uninformative. The full Kaggle dataset (22,750 rows) is required — and even that dataset may not represent the demographic composition of a real customer's workforce.

2. **Jurisdiction-specific protected classes** — Singapore (PDPA, Employment Act), EU (GDPR Article 22, Equal Treatment Directives), US (ADA, Title VII, ADEA) each define protected classes differently. A fairness audit against the wrong protected classes is a compliance liability, not a compliance asset. The pilot customer's jurisdiction must be confirmed before the audit is designed.

3. **Statistical baseline** — what differential rate is acceptable requires a legal baseline (US uses the 4/5ths rule; EU uses indirect discrimination standards; Singapore has no formal statistical threshold). Running disparate impact tests without a baseline produces numbers with no interpretive framework.

A half-done fairness audit ("Gender showed 0% tier change in the proxy-drop test, so we're fine") is worse than a deferred one — it creates a document that will be referenced as real evidence when it is not.

---

## What Phase 14 Covers When It Runs In Sprint 2

Three parts:

### PART 1 — Disparate impact analysis

Does the Random Forest model produce materially different burnout risk tier distributions for different demographic subgroups?

Test requires:

- A baseline (what differential rate is acceptable — jurisdiction-specific)
- Statistical significance (is the observed differential larger than sampling noise?)
- Protected classes confirmed per customer jurisdiction

Primary protected classes for Oraclaire:

- Gender (all jurisdictions)
- Age (ADEA US, EU Age Directive, Singapore Employment Act)
- Race/ethnicity (Title VII US, EU Equal Treatment)
- Disability status (ADA US, GDPR Article 9)
- Caregiving status (disproportionate burnout in caregivers — correlates with gender, protected in some jurisdictions)

### PART 2 — Subgroup metrics

Instead of one overall AUC, Brier score, FP rate, FN rate — compute the same metrics per identifiable subgroup and report the gaps.

Key subgroup metrics for Oraclaire:

- FN rate by Gender — does the model miss burned-out employees at different rates by gender?
- FP rate by Age cohort — does the model falsely flag healthy employees at different rates by age?
- Tier distribution by Designation level — does seniority predict tier assignment independent of burnout signal?

### PART 3 — Mitigation

If a gap is found, three options:

- (a) Adjust training data — rebalance representation of underrepresented groups
- (b) Add a fairness constraint to Phase 11 — a hard constraint that bounds the differential rate per protected class
- (c) Document that the gap is accepted with a business reason and regulatory sign-off

None of these options are available without first measuring the gap in Part 1.

---

## What Sprint 1 Did Instead

Three interim steps stand in for Phase 14 until Sprint 2:

### STEP 1 — Phase 3 proxy check

Gender was excluded from the feature set on Axis 3 (protected characteristic, D17 Phase 3 feature decisions). Proxy-drop test in Phase 3 showed 0% tier change when Gender was added — the model is not using Gender as a signal even implicitly (S3-F1, Phase 7). This is necessary but not sufficient for the fairness audit.

### STEP 2 — Phase 7 S3-F1

Gender proxy 0% finding documented in `phase_7_red_team.md` with disposition ACCEPT and explicit note: "Fairness audit pre-commitment unchanged — S3-F1 is a proxy-drop result, not a disparate impact analysis."

### STEP 3 — D11 Nuance 4 and D17 pre-commitment

Both decisions explicitly pre-committed a Gender fairness audit as a Sprint 2 requirement — using Gender as an audit variable not a model feature, on the full dataset.

These three steps ensure Phase 14 is visibly deferred — not silently skipped. The trail exists.

---

## Sprint 2 Opening Context

Phase 14 is a scheduled deliverable in Sprint 2.

These existing journal entries feed directly into Sprint 2 Phase 14 opening context:

- `phase_3_features.md` — Gender proxy-drop result, Axis 3 exclusion rationale
- `phase_7_red_team.md` — S3-F1 Gender proxy 0% finding
- D11 Nuance 4 decision — fairness audit as pre-commitment
- D17 Phase 5 pick — Gender as audit variable not feature, confirmed
- `phase_14_fairness_deferred.md` (this file) — full audit design for Sprint 2

No additional setup required in Sprint 1.

---

## Pre-Conditions For Sprint 2 Phase 14 Activation

Before Phase 14 runs in Sprint 2, confirm all three:

- [ ] Full Kaggle dataset available at `data/raw/train.csv` (22,750 rows — pre-commitment 1 from D18)
- [ ] Pilot customer jurisdiction confirmed — protected classes and statistical baseline identified for that jurisdiction
- [ ] At least one full quarterly cycle of real deployment data available from the pilot customer — real workforce demographics are more important than Kaggle dataset demographics for a fairness audit that will be cited in any regulatory context

---

## Journal Trail

| Phase    | Entry                 | Fairness content                             |
| -------- | --------------------- | -------------------------------------------- |
| Phase 3  | `phase_3_features.md` | Gender excluded Axis 3, proxy-drop 0%        |
| Phase 7  | `phase_7_red_team.md` | S3-F1 Gender proxy finding                   |
| Phase 11 | D28                   | C5 GDPR re-identification, C6 consent regime |
| Phase 14 | This file             | Full audit deferred to Sprint 2              |

---

Phase 14 fairness audit deferred to Sprint 2. Trail documented. Three pre-conditions confirmed before activation.
