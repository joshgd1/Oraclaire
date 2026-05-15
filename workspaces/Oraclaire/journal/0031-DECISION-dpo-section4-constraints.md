---
type: DECISION
date: 2026-05-15
created_at: 2026-05-15T00:00:00Z
author: human
session_id: current
session_turn: 1
project: Oraclaire
topic: DPO package Section 4 constraint confirmation — C1b, C5, C3a resolutions
phase: todos
tags: [dpo-review, section-4, constraints, d31]
---

# D31 — DPO Package Section 4 Constraint Confirmation

**Date:** 2026-05-15
**Author:** human (founder)
**Status:** APPROVED

---

## D31a — C1b (FP Decay Threshold 20%) — Removed from DPO Package Scope

**Decision:** Correct as HARD physical limit. Out of Section 4 scope.

**Rationale:** The DPO package Section 4 covers what the product cannot do to or with employees. C1b is an internal product health metric — it governs model viability via the participation feedback loop, not employee rights or data processing constraints. A DPA does not need to understand C1b.

**Action:** Remove C1b from Section 4. C1b remains in the LP constraint documentation only.

---

## D31b — C5 (Minimum Team Size n=5) — Fixed, Not Configurable Downward

**Decision:** Fixed at n=5 globally. Configurable upward only.

**Rationale:** Making n=5 configurable per deployment would allow a customer to set it to n=2 or n=3. At n=2 a two-person team produces an aggregate where either person can identify the other — re-identification. This is a GDPR Article 5(1)(c) violation regardless of what the DPA signs off on. A DPA can confirm that n=5 is sufficient for anonymisation in a specific context. A DPA cannot authorise a product to permit re-identification at smaller group sizes.

**Section 4 C5 entry update:**

> Minimum team size is 5. This floor cannot be reduced at deployment. It can be increased if a customer's Data Protection Authority requires a higher threshold for their specific context.

---

## D31c — C3a (Critical Exceeds 5%) — Four-Step Procedure

**Decision:** Deployment pause pending calibration review — following four-step procedure.

**Rationale:** Critical > 5% does not mean the model is wrong (requires investigation) and does not mean the threshold is wrong (also requires investigation). The correct first response is a deployment pause on new assessment cycles while the investigation runs.

**Four-step procedure:**

1. Critical exceeds 5% → product surfaces a model health alert to the Product Owner
2. Individual Critical flags continue to flow through the human review gate (no employee is left without review)
3. New assessment cycles pause pending Product Owner review
4. Product Owner investigates: dataset composition shift / model calibration failure / genuine organisational crisis → then decides: retrain, adjust threshold, or resume with documented note

**Section 4 C3a entry update:** Replace "deployment pauses for calibration review" with the four-step procedure above.

**config.py addition:**

```python
# Critical tier model health gate
# If Critical tier exceeds this fraction in any cycle —
# surface model health alert to Product Owner.
# New assessment cycles pause pending review.
# Current cycle Critical flags continue through human review gate.
CRITICAL_HEALTH_CEILING = 0.05
```

---

## Section 4 Confirmation

With D31a, D31b, D31c resolved, Section 4 is confirmed with three edits:

1. **Remove C1b** — not in DPO package scope
2. **Update C5** — configurable upward only, floor is n=5 globally
3. **Update C3a** — four-step procedure in place of "deployment pauses"

The policy-only section at the bottom of Section 4 (AUP items) remains as specified — those are contractual, not technically enforced, and belong in the AUP not in this table.

---

## For Discussion

No open items. All three resolutions are final.
