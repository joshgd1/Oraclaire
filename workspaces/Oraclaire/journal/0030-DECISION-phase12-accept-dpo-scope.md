---
type: DECISION
date: 2026-05-15
author: co-authored
project: Oraclaire
topic: Phase 12 ACCEPT with conditions — DPO package scoped to SHAP format plus tier explanation
phase: codify
tags: [phase-12, dpo, d16, d27, shap, eu-ai-act, deployment-gate]
---

# D30: Phase 12 Disposition + DPO Package Scope

## Phase 12 Disposition: ACCEPT

**Status:** ACCEPTED with three named conditions.

**Annual delta:** ~$924,000 against do-nothing baseline of $1,137,500. Directional only — not validated for customer-facing cost justification until unvalidated cost terms are confirmed.

**Rationale:** The plan routes employees to the correct action per tier. No hard constraint is violated on real data. The C3a failure on the 12-row sample is a sample artifact (zero Critical employees on 12 rows is expected given the population rate), not a model health finding.

### Condition 1 — C3a re-evaluation at first quarterly cycle

C3a failure on the 12-row sample is documented as a sample artifact. The finding reclassifies as a real model health issue if and only if: **Critical tier exceeds 5% on the full deployment dataset in the first real quarterly cycle.**

If that threshold is breached in the first real cycle, plan disposition reopens as RE-TUNE.

### Condition 2 — Delta not cited externally until cost terms validated

The $924,000 annual delta is directional only. Customer-facing cost justification requires validation of the four unvalidated cost terms (reviewer cost, assessment cost, disparate impact cost, ORT organisational response cost). Use only the sourced $4,000/$21,000 FN and $15 FP terms in any external communication.

### Condition 3 — Schema gaps resolved before go-live

The two schema gaps (consent flag missing from sample dataset; ORT history not in audit trail) must be resolved in the deployment checklist before the plan goes live at a real customer. These are deployment configuration requirements, not model problems. Already captured in `customer-deployment-checklist.md`.

---

## DPO Package Scope: SHAP + Tier Explanation

**D16 question:** Does the SHAP output format meet the DPO's requirements for explainability of automated decision-making?

**Sub-question:** Does the scope also cover the risk tier explanation shown to employees?

**Decision: YES — both are in scope.**

**Rationale:** The SHAP waterfall explains WHY an employee received their score. The risk tier label explains WHAT the score is. A DPO who approves the SHAP format without seeing the tier labels is approving the explanation without approving the conclusion it attaches to.

**Specific risk:** If "Critical" tier is attached to a fatigue-weighted SHAP explanation, the DPO needs to approve that combination — not each component in isolation. A DPO who later sees the combination may raise concerns about whether "Critical" implies a clinical diagnosis. Scoping both together prevents that question arising post-deployment.

### Section 3A Coverage (confirmed)

**3A-i:** SHAP waterfall format as shown to employees — plain language labels, directional indicators, no raw feature names, no probability scores.

**3A-ii:** Risk tier labels (Low, Moderate, High, Critical) and their plain language definitions as shown to employees.

**3A-iii:** The combination — how a tier label and SHAP waterfall appear together on the employee dashboard. The DPO must approve the complete employee-facing screen, not just the SHAP component in isolation.

### Section 5 Ask (confirmed)

"Does the employee-facing presentation of (a) risk tier, (b) SHAP explanation, and (c) their combination on the dashboard meet your organisation's standard for explainability of automated decision-making affecting employees under [applicable regime]?"

The single ask covers all three in one question.

---

## Sequencing for Remaining Sprint 1 Items

| Priority      | Item                                          | Unblocks                      | Notes                                  |
| ------------- | --------------------------------------------- | ----------------------------- | -------------------------------------- |
| NEXT          | Build DPO package                             | D27 Condition 1, D17 DPO gate | Employee UI hard gate                  |
| THEN          | Resolve D29 discussion questions C1b, C5, C3a | Customer deployment           | Three constraint clarifications        |
| THEN          | Validate cost terms with first customer       | External cost justification   |                                        |
| SPRINT 2      | Drift thresholds, Threshold B, Fairness audit | —                             | Require real deployment data           |
| POST-SPRINT 1 | Items 8, 9, 10                                | —                             | Assumption confirmations, housekeeping |

---

## For Discussion

1. D16 named SHAP format as the DPO review subject. Has the DPO been informed that the scope has expanded to include tier labels? Does this change the preparation timeline?

2. D27 Condition 1 names the DPO package as the hard gate before any employee sees their score. What is the expected turnaround time for DPO review, and who is the DPO contact?
