# Oraclaire Customer Deployment Checklist

Complete once per customer before employee UI activation.

Customer name: **_
Deployment date: _**
Completed by: **_ (role)
Reviewed by: _** (role)

---

## GATE 1: LEGAL AND COMPLIANCE

- [ ] Customer legal team has reviewed and signed the Acceptable Use Policy (AUP)
  - AUP prohibits: use of scores in performance reviews, promotions, terminations, or any adverse employment decision
  - Signed by: **_ Date: _**

- [ ] Data Processing Agreement (DPA) executed covering:
  - PDPA compliance (Singapore customers)
  - GDPR Article 9 compliance (EU customers)
  - Data residency confirmation
  - Signed by: **_ Date: _**

- [ ] Jurisdiction confirmed:
  - [ ] Singapore — PDPA applies
  - [ ] EU/EEA — GDPR Article 9 applies
  - [ ] Other: **_ — applicable law confirmed: _**

- [ ] Works council / union notification completed (Germany, France, Netherlands — mandatory before deployment)
  - Applicable: Y / N
  - If Y — confirmation document: \_\_\_

---

## GATE 2: DPO SIGN-OFF (HARD GATE — employee UI cannot activate without this)

- [ ] DPO or qualified legal professional has reviewed the SHAP output format as shown in predictions.jsonl sample output
- [ ] DPO has confirmed the SHAP explanation format meets their interpretability standard for this jurisdiction
- [ ] DPO sign-off documented:
  - Name: \_\_\_
  - Role: \_\_\_
  - Date: \_\_\_
  - Format approved: \_\_\_

**EMPLOYEE UI STATUS:**

- [ ] LOCKED — pending DPO sign-off
- [ ] UNLOCKED — DPO sign-off obtained
  - Date unlocked: \_\_\_

---

## GATE 3: CUSTOMER CONFIGURATION

- [ ] Minimum scoreable employee count confirmed: \_\_\_ (minimum required: 100)

- [ ] Seniority identification method selected (D15):
  - [ ] HRIS-derived — field mapped: \_\_\_
  - [ ] Self-reported at opt-in

- [ ] Grievance cooldown period confirmed: \_\_\_ days (default 90 — EU customers may require longer)

- [ ] Organisational Risk Threshold configured: \_\_\_% (default 20%)

- [ ] Auto-flag ceiling configured: \_\_\_% (default 20%)

- [ ] Exclusion categories confirmed with HR and Legal:
  - [ ] PIP employees excluded
  - [ ] ADA accommodation excluded
  - [ ] FMLA leave excluded
  - [ ] Workers compensation excluded
  - [ ] Disciplinary review excluded
  - [ ] Grievance window excluded

---

## GATE 4: FIRST DEPLOYMENT MEASUREMENT COMMITMENT

- [ ] e value measurement confirmed as the FIRST metric collected at deployment (D15 — exclusion fraction determines what the model can see)
  - e measurement method: \_\_\_
  - Expected e value range: \_\_\_

- [ ] HR Director has been briefed on the monitoring plan:
  - MFS SHAP drift (quarterly)
  - FP rate per cycle (quarterly)
  - Participation rate (quarterly)
  - Pulse drift false trigger rate (weekly)
  - Critical tier review completion (weekly)
  - Brier score per cycle (quarterly)
  - resource_allocation missingness (quarterly)
  - HR Director name: \_\_\_
  - Briefing date: \_\_\_

- [ ] Rollback process confirmed with customer:
  - Rollback target (pre-Oraclaire process): \_\_\_
  - Rollback trigger: FP rate exceeds 25% for two consecutive quarterly cycles
  - Rollback owner: \_\_\_

---

## GATE 5: KNOWN LIMITATIONS DISCLOSED TO CUSTOMER

The following Sprint 2 backlog items have been disclosed to the customer as known limitations with defined mitigations:

- [ ] **S1-F1: Seed instability** — individual employees near tier boundaries may shift tier across model retrains. Mitigation in Sprint 2: ensemble averaging across 3 seeds.
  - Customer acknowledged: Y / N
  - Date: \_\_\_

- [ ] **S2-F2: resource_allocation fragility** — if workload survey response rate drops below 85%, MFS may approach the 40% dominance gate. Mitigation in Sprint 2: missingness monitor with SHAP quality flag.
  - Customer acknowledged: Y / N
  - Date: \_\_\_

- [ ] **Threshold B (senior tier) not validated** — senior-tier detection performance cannot be claimed until HRIS data is available and Threshold B is calibrated on real seniority-labelled data.
  - Customer acknowledged: Y / N
  - Date: \_\_\_

- [ ] **No model performance claims** — the product cannot claim "catches X% of burnout cases" until one full quarterly cycle of real deployment data validates the pre-registered floors on this customer's workforce population.
  - Customer acknowledged: Y / N
  - Date: \_\_\_

---

## GATE 6: EMPLOYEE COMMUNICATION

- [ ] Employee communication plan reviewed and approved by HR Director

- [ ] Communication confirms:
  - [ ] Participation is voluntary
  - [ ] Individual scores visible only to the employee
  - [ ] HR sees team aggregates only
  - [ ] Data is not used in performance reviews or employment decisions
  - [ ] Employee can withdraw consent at any time (48-hour cooling-off period)
  - [ ] Employee owns their data (access, export, delete rights)

- [ ] Launch communication sent to employees before first assessment cycle opens

---

## DEPLOYMENT AUTHORISATION

All six gates must be checked before employee UI is activated.

- Gates 1-3 and 5-6: completed by HR Director and Legal team
- Gate 4: completed by HR Director with Oraclaire support
- Gate 2 (DPO sign-off): HARD GATE — employee UI cannot activate without this checkbox complete

Authorised by: **_
Role: _**
Date: \_\_\_

Oraclaire deployment confirmed: \_\_\_
