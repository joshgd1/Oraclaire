# Oraclaire — Positioning Language for Legal Review

**Document type:** Internal positioning and talking-point reference
**Audience:** Oraclaire sales, legal, and customer success teams
**Classification:** Internal — not for distribution to customers without legal review
**Note:** All language below is draft. Do not share externally without legal sign-off.

---

## 1. Product Positioning

### 1.1 One-Line Description

> Oraclaire is an organisational wellbeing analytics platform that helps HR teams identify employees at risk of burnout — before burnout becomes a crisis.

### 1.2 Three-Line Description

> Oraclaire is a workplace wellbeing analytics SaaS that classifies employee burnout risk using a machine learning model trained on validated psychological research (Copenhagen Burnout Inventory).

> Unlike performance management tools, Oraclaire is designed exclusively for wellbeing and early intervention — not evaluation, rating, or employment decisions. Every Critical-tier classification requires human HR review before any action is taken.

> Oraclaire provides employees with full transparency into their own scores and the factors driving them, meeting the EU AI Act's right-to-explanation requirement for high-risk employment AI systems.

### 1.3 Full Positioning Statement

Oraclaire occupies the **employee wellbeing** category — distinct from both **performance management** (which evaluates output and behavior) and **HR analytics** (which tracks engagement and productivity metrics).

The EU AI Act classifies Oraclaire as a **high-risk employment AI system** under Annex III, §4. We do not minimize this classification — we lean into it. Our EU AI Act conformity assessment (available under NDA) demonstrates full compliance with the technical requirements for high-risk systems, including:

- SHAP-based explainability for every score (Article 13)
- Human review gate for Critical-tier classifications (Article 14)
- Bias audit before each deployment (Article 10)
- Comprehensive audit trail for all predictions (Article 12)

---

## 2. Legal Talking Points

### 2.1 On the EU AI Act Classification

**Q: Why is Oraclaire classified as high-risk?**

> The EU AI Act classifies AI systems used in employment and workplace management as high-risk. Oraclaire processes employee health-related data to generate burnout risk scores — this falls squarely within Annex III, §4 (Employment, workplace management, and access to self-employment).

**Q: Does high-risk mean Oraclaire is unsafe?**

> No. High-risk classification means the system is subject to the most stringent requirements under the AI Act — and Oraclaire meets all of them. High-risk classification is a regulatory categorisation, not a judgement on safety. It reflects the fact that employment decisions have significant consequences, so the standards for transparency, human oversight, and accuracy are set high.

**Q: What guarantees do customers have that the system is compliant?**

> Every customer receives a completed EU AI Act conformity assessment (technical document) and a DPIA template (legal document) before deployment. Both are available under NDA. We also conduct a pre-deployment bias audit of their specific employee population.

### 2.2 On Human Review Gate

**Q: What does "human review gate" mean in practice?**

> When an employee's burnout risk is classified as Critical, that classification is held in a pending state. No HR administrator, manager, or anyone else can see it or act on it until an HR reviewer has explicitly approved the classification. The reviewer sees the score, the contributing factors (SHAP decomposition), and the employee's risk trajectory. They can approve the classification or override it to a lower tier with a written reason.

**Q: What happens if the HR reviewer doesn't act within 48 hours?**

> The system generates an escalation signal — a notification to the HR administrator that a review is overdue. The customer can configure the timeout window. No automated action is taken without human approval.

**Q: Can the HR reviewer override a classification without reason?**

> No. Override decisions require a written reason. All decisions — approval and override — are logged in the audit trail with the reviewer's identity, the original tier, the new tier (if overridden), and the reason.

### 2.3 On Data Privacy

**Q: What employee data does Oraclaire collect?**

> We collect: (1) responses to validated wellbeing surveys (Copenhagen Burnout Inventory and weekly pulse surveys), and (2) basic HRIS fields required for scoring — tenure, seniority level, company type, and work-from-home setup. We do not collect performance data, communications content, location data, or biometric data.

**Q: How is employee consent handled?**

> Employees must provide consent before participating. They can withdraw consent at any time, and their data is removed from scoring within 48 hours. We do not retain individual assessment data beyond 12 months (configurable).

**Q: Can employees see their own scores?**

> Yes. After a 24-hour employee-first visibility delay (designed to give employees first access to their own data before HR and managers see aggregates), employees can view their own score, risk tier, contributing factors, and a plain-language explanation.

**Q: Who can see individual employee scores?**

> Only the employee themselves. HR administrators see aggregate team data (never individual scores). Managers see team aggregates (never individual scores). Individual scores require HR reviewer approval before any organisational action is taken.

**Q: Can scores be exported to our HRIS?**

> Technically, Oraclaire blocks all API responses that would facilitate export of individual scores to HRIS or performance management systems. This is enforced at the API level — not just policy.

### 2.4 On Bias and Fairness

**Q: How does Oraclaire prevent bias in scoring?**

> Three layers: (1) We conduct a pre-deployment bias audit comparing Critical+High tier rates across demographic slices (seniority, company type, WFH setup). Any slice where the HC rate differs from the overall population by more than 10 percentage points is flagged for human review. (2) Our model was audited for SHAP dominance — Mental Fatigue Score accounts for less than 40% of total SHAP importance, preventing any single factor from dominating the score. (3) Our two-threshold architecture applies different calibration thresholds for junior and senior employees, reflecting the different false-negative costs in each group.

**Q: What happens if bias is detected?**

> The bias audit flags the affected slice and surfaces it to the HR administrator with detail per group. The deployment does not proceed until the HR administrator has reviewed and acknowledged the finding. We do not automatically block deployments, but we ensure full transparency.

---

## 3. Objection Handling

### 3.1 "This feels like surveillance"

> Oraclaire is designed to do the opposite of surveillance. We give employees insight into their own wellbeing — something most organisations never do. The 24-hour employee-first gate means employees see their own scores before anyone else does. The right-to-explanation means every score comes with a plain-language breakdown of what drove it. We believe transparency is the antidote to surveillance concerns.

### 3.2 "Our employees won't trust this"

> Trust is earned through transparency. We provide employees with full visibility into how their scores are calculated, what factors contributed, and what they can do to improve their wellbeing. Employees who feel their employer is investing in their wellbeing — not just monitoring them — respond differently. Our participation mechanism design (24h employee-first, content library, single-item weekly pulses) is specifically designed to increase voluntary participation.

### 3.3 "What if a manager misuses the data?"

> We have technical blocks that prevent managers from seeing individual employee scores — they only see team-level aggregates when the team has 5 or more members. Individual scores are never visible to managers. And the API blocks any response format that would facilitate exporting scores to HRIS or performance systems. The Acceptable Use Policy makes misuse grounds for contract termination.

### 3.4 "Our works council will never approve this"

> We understand. In Germany, France, and other EU jurisdictions, works council consultation is a legal requirement. We recommend engaging the works council early — we provide a complete DPIA template, a conformity assessment, and a works-council-ready summary document. Our experience is that transparency about what the system does AND doesn't do goes a long way toward building trust.

### 3.5 "We're not an EU company — does this apply to us?"

> If you have employees in the EU, the EU AI Act applies to you. The question isn't whether it applies — it's whether you're ready. We can walk you through the specific obligations based on your situation.

---

## 4. Competitive Differentiation

### 4.1 vs. Employee Engagement Platforms (Culture Amp, Lattice, Peakon)

| Dimension         | Oraclaire                          | Engagement Platforms                   |
| ----------------- | ---------------------------------- | -------------------------------------- |
| Focus             | Burnout risk (clinical basis)      | General engagement                     |
| ML model          | RandomForest + SHAP explainability | Often simple NPS or survey aggregation |
| Explainability    | Per-employee SHAP decomposition    | Aggregate themes only                  |
| EU AI Act         | Full high-risk compliance package  | Often not applicable                   |
| Human review gate | Critical-tier requires HR approval | No equivalent                          |
| Bias audit        | Pre-deployment demographic audit   | No equivalent                          |

### 4.2 vs. Generic HR Analytics

| Dimension        | Oraclaire                        | Generic HR Analytics                                 |
| ---------------- | -------------------------------- | ---------------------------------------------------- |
| Purpose          | Wellbeing and early intervention | Broader workforce analytics                          |
| Data type        | Wellbeing surveys only           | Often includes performance, communications, log data |
| Explainability   | Full SHAP decomposition          | Often black-box                                      |
| HRIS integration | Blocked by design                | Often encouraged                                     |
| EU AI Act        | Designed for compliance          | Often not designed for high-risk classification      |

---

## 5. Disclaimers

The following language MUST appear in all customer contracts:

> **EU AI Act Notice:** Oraclaire is a high-risk AI system under EU AI Act Regulation (EU) 2024/1689 Annex III, §4. Customer acknowledges that deployment of Oraclaire triggers obligations under the EU AI Act, including the provision of notices to employees, completion of a Data Protection Impact Assessment where required, and compliance with the human review gate requirements. Oraclaire provides the technical infrastructure to support compliance but does not provide legal advice. Customer is responsible for its own legal compliance.

> **No Employment Decisions:** Oraclaire is designed for organisational wellbeing purposes only. Oraclaire scores must not be used as the sole or primary basis for any employment decision, including hiring, termination, promotion, demotion, or disciplinary action. Use for prohibited purposes constitutes a breach of the Acceptable Use Policy and grounds for immediate termination of service.

> **Medical Disclaimer:** Oraclaire provides organisational wellbeing analytics and is not a medical device, diagnostic tool, or clinical instrument. Oraclaire scores are not a substitute for professional medical advice, diagnosis, or treatment.

---

_Document version: 1.0 DRAFT — Oraclaire Sprint 1 — Internal Use Only — Not for External Distribution_
