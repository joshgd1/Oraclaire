---
type: DECISION
date: 2026-05-14
created_at: 2026-05-14T19:00:00+10:00
author: human
session_id: resume-post-clear
session_turn: 6
project: Oraclaire
topic: Sprint 1 cleared for first customer deployment with four named conditions
phase: deploy
tags:
  [
    D27,
    GO-decision,
    deployment-gate,
    pilot-deployment,
    DPO-sign-off,
    performance-claims,
    sprint2-commitments,
  ]
---

# Decision D27 — Phase 8 GO/NO-GO

**Title:** GO — Sprint 1 cleared for first customer deployment with four named conditions

---

## THE GO DECISION

GO signed on the Phase 8 gate document (`workspaces/Oraclaire/journal/phase_8_gate.md`).

The PASS/FAIL table is honest. The two FAILs are documented with accepted overrides and written rationale. The overrides were made before the gate — not invented to pass the gate.

No unresolved MITIGATE findings. No unresolved RE-DO findings. Seven monitoring signals with variance-grounded thresholds. Rollback trigger is specific. Rollback target is honest about what Oraclaire replaces.

---

## CONDITION 1: DPO SIGN-OFF BEFORE FIRST EMPLOYEE SEES A SCORE

Pre-committed in D17 as a hard gate. Not resolved by the Phase 8 gate document.

No employee sees their burnout risk tier or SHAP waterfall until a qualified legal or data protection professional has reviewed and approved the SHAP output format.

This condition gates the employee dashboard — not the model deployment. The model can be deployed to a staging environment. The employee-facing UI cannot be activated until DPO sign-off is obtained.

**Named:** "Employee dashboard activation blocked pending DPO sign-off on SHAP output format (D17). Model deployment to staging: permitted. Employee UI activation: blocked until sign-off obtained."

---

## CONDITION 2: FIRST CUSTOMER DEPLOYMENT IS A PILOT — NOT A PRODUCTION ROLLOUT

Sprint 1 ships to one customer. One customer. Not a product launch.

Pilot customer criteria before deployment:

- Minimum 100 scoreable employees (above the 5-person team minimum for aggregate reporting)
- Willing to share e value (exclusion fraction) data — the first metric measured at every deployment per D15
- HR Director engaged and briefed on the monitoring plan from Phase 8
- Legal team has reviewed the customer acceptable use policy (D6 G-10)

**Named:** "Sprint 1 deployment is a controlled pilot — one customer, minimum 100 scoreable employees, e value measurement required, HR Director briefed on monitoring plan, AUP signed."

---

## CONDITION 3: PERFORMANCE CLAIMS ARE GATED UNTIL FULL DATASET VALIDATION ON REAL DEPLOYMENT DATA

The model was selected and validated on the Kaggle dataset. The Kaggle dataset is not a representative workplace population.

Until the pilot produces one full quarterly cycle of real employee data:

- No AUC or accuracy claims in customer-facing materials
- No "catches X% of burnout cases" language in any documentation
- No comparative claims against other products

What CAN be claimed:

- The methodology (CBI validated instrument)
- The architecture (employee-first, SHAP-transparent, consent-gated)
- The governance (PDPA, GDPR Article 9, EU AI Act high-risk compliance design)

**Named:** "No model performance claims in customer-facing materials until one full quarterly cycle of real deployment data validates the pre-registered floors on a representative workforce population."

---

## CONDITION 4: SPRINT 2 BACKLOG ITEMS ARE TRACKED AS LIVE COMMITMENTS

The two MITIGATE findings from Phase 7 were deferred to Sprint 2 — not dismissed.

S1-F1 (seed instability — ensemble averaging) and S2-F2 (resource_allocation fragility — missingness monitor) are live commitments to the pilot customer — not optional improvements.

If the pilot customer experiences either of these failure modes before Sprint 2 ships — the appropriate response is manual intervention, not silence.

**Named:** "Sprint 2 backlog items S1-F1 and S2-F2 are communicated to the pilot customer as known limitations with defined mitigations in Sprint 2. They are not withheld."

---

## Post-GO Sequence

1. Commit Phase 8 gate document (this commit)
2. Tag model artifact as sprint1-pilot-candidate
3. Create customer deployment checklist
4. Prepare DPO review package for SHAP output format

---

GO signed. Four conditions named. Sprint 1 cleared for pilot deployment.
