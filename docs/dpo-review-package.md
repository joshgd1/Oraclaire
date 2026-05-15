# DPO Review Package — Oraclaire Sprint 1

**Version:** 1.0 — Draft for review
**Date:** 2026-05-15
**Prepared for:** Data Protection Officer / Legal Counsel
**Re:** Oraclaire burnout risk scorer — SHAP explainability and tier labels

---

## Section 1 — What This Document Is And Why It Exists

### What Oraclaire Is

Oraclaire is an employee burnout risk scorer. It runs quarterly — each cycle, employees complete a CBI (Burnout Assessment Tool) instrument, the model produces a burnout risk tier, and the employee receives their result with an explanation of which factors contributed to their score.

The four-tier escalation path:

| Tier         | Employee sees             | HR sees                | Manager sees    | Action required                                         |
| ------------ | ------------------------- | ---------------------- | --------------- | ------------------------------------------------------- |
| **LOW**      | Own trend line            | Nothing                | Nothing         | None                                                    |
| **MODERATE** | Score + matched resources | Nothing                | Nothing         | Resources surfaced to employee only                     |
| **HIGH**     | Score + resources         | Team aggregate         | Check-in prompt | Employee identity protected unless they choose to share |
| **CRITICAL** | Score + resources         | Escalation to reviewer | Escalation      | Human review mandatory before any action                |

**What Oraclaire cannot do by design — regardless of what a manager or HR Director requests:**

- Share an individual score with a manager or HR without the employee's explicit consent
- Export any individual score to a performance management or HRIS system
- Auto-approve a Critical tier flag without human reviewer sign-off
- Retain individual data beyond the configured retention period
- Score an employee who has not consented or who is in an excluded category

These are architectural constraints, not policy choices. They are enforced in code. Technical citations are in Section 4.

The product's design principle is **employee-first**: employees own their data, HR sees only team-level aggregates at minimum n=5, and individual scores are never shared without explicit employee consent.

### Why A DPO Review Is Required

This review is a hard gate — not a suggestion. It was committed in two places:

**D17 (2026-05-14):** "Sprint 1 does not deploy to a real customer until the SHAP output format has been reviewed and approved by a qualified legal or data protection professional. This is the product's primary defence against the most likely litigation scenario: an employee whose score influences an employment decision they did not consent to."

**D27 (2026-05-14):** "No employee sees their burnout risk tier or SHAP waterfall until a qualified legal or data protection professional has reviewed and approved the SHAP output format."

No employee dashboard activates at any customer until this review is complete and signed off.

### What This Review Covers — Expanded Scope

D16 originally named the SHAP output format as the subject of this review. One sub-question arose: does the review also cover the risk tier labels (Low, Moderate, High, Critical) that appear alongside the SHAP waterfall on the employee screen?

**Decision (D30, 2026-05-15): Both are in scope.**

The SHAP waterfall explains WHY the employee received their score. The tier label explains WHAT the score is. A DPO who approves the SHAP format without seeing the tier labels is approving the explanation without approving the conclusion it attaches to.

The specific risk: if "Critical" tier attaches to a fatigue-weighted SHAP explanation, the combination may raise questions about whether the tier label implies a clinical diagnosis — which it must not. This review covers the complete employee-facing screen, not its components in isolation.

### Document Structure

| Section                                               | Content                                                                |
| ----------------------------------------------------- | ---------------------------------------------------------------------- |
| **1 — This section**                                  | What Oraclaire is, why this review exists, what it covers              |
| **2 — The SHAP waterfall**                            | How the explanation is generated, what the employee sees               |
| **3 — Tier labels and definitions**                   | What each tier means in plain language                                 |
| **4 — Technical constraints the DPO must understand** | Human review gate for Critical tier, EU AI Act Article 14, audit trail |
| **5 — The specific ask**                              | One question covering SHAP + tier + their combination                  |
| **Appendix A**                                        | Data flows and retention                                               |
| **Appendix B**                                        | Open legal questions requiring DPA resolution                          |

### Who Should Review This

This document should be reviewed by:

- A Data Protection Officer or legal counsel with GDPR/PDPA expertise
- A legal counsel with EU AI Act experience (the Critical tier human review gate is an EU AI Act Article 14 matter — see Section 4)
- If the customer is in a jurisdiction with additional automated decision-making requirements (CPRA, ADA, ADEA), counsel qualified in those regimes

---

_Section 1 review complete. Awaiting confirmation before proceeding to Section 2._

---

## Section 2 — The SHAP Waterfall

### How The Explanation Is Generated

Each quarter, an employee's CBI assessment responses are fed into a Random Forest model. The model outputs a burnout probability between 0 and 1. The SHAP (SHapley Additive exPlanations) decomposition then runs against that prediction to identify which features contributed most to that specific employee's score — and in which direction.

The path is:

1. Employee completes CBI instrument → raw feature vector (10 features)
2. Random Forest model → burnout probability
3. SHAP TreeExplainer → per-feature contribution values for all 10 features
4. All 8 features with employee-facing labels shown; the 3 with largest absolute contributions receive directional indicators ("increases risk" / "decreases risk"); the remaining 5 receive a neutral indicator ("no significant contribution")
5. Direction label assigned to top contributors ("increases" if contribution is positive, "decreases" if negative); neutral label assigned to the rest
6. Plain language label substituted for raw feature name
7. Result returned to employee dashboard — all 8 features visible, no raw numbers, no probability, no SHAP float values

This is a one-way path. The model does not store the explanation until after it is delivered. The employee sees the explanation before anyone else.

---

### What The Employee Sees

Below is the exact format as it appears on the employee dashboard — all 8 features that have employee-facing labels. No features are truncated.

---

**Your burnout risk explanation**

All eight factors from your assessment are shown below. Three are the main contributors to your current score. Five are within normal range for your role.

1. **Your recent energy levels** — increases your risk
2. **Your current workload demands** — increases your risk
3. **Your time in this role** — increases your risk
4. **Your working arrangement** — no significant contribution
5. **Your role level** — no significant contribution
6. **Your organisation type** — no significant contribution

_Three factors are elevated. Five are within normal range. Your score reflects the balance across all factors._

---

The employee sees:

- Plain language labels — no raw feature names (no "mental_fatigue_score", no "tenure_days")
- Direction only — "increases risk" or "decreases risk" — no probability numbers
- No SHAP float values — no "0.23", no "−0.15", nothing a mathematician could reconstruct
- No probability score — no "0.67" burnout probability
- No threshold — the employee does not know whether they are above or below any classification boundary
- No other employees' scores — the comparison is to the employee's own prior cycles only

---

### What Is Not Shown To The Employee

The following exists in the audit trail and is deliberately withheld from the employee view:

| What is stored                                                                                                        | What the employee sees                     | Why it is withheld                                                                                                                                                                                                                                                                   |
| --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Raw feature values (e.g. mental_fatigue_score = 7.2)                                                                  | Nothing                                    | Raw values could reconstruct scores or enable comparison between employees                                                                                                                                                                                                           |
| SHAP float values (e.g. +0.2314, −0.0892)                                                                             | Direction only ("increases" / "decreases") | Float values enable reconstruction of the probability and cross-employee comparison                                                                                                                                                                                                  |
| Burnout probability (e.g. 0.67)                                                                                       | Nothing                                    | Probability is a number that could be used to rank employees                                                                                                                                                                                                                         |
| Threshold used (Threshold A = 0.35)                                                                                   | Nothing                                    | Knowing the threshold allows inference of whether any employee is above or below it                                                                                                                                                                                                  |
| Whether the employee is above or below the threshold                                                                  | Nothing                                    | Binary above/below is a classification, not an explanation                                                                                                                                                                                                                           |
| Binary indicator: missing_resource_allocation — records whether the employee skipped the resource_allocation question | Nothing                                    | These binary indicators record whether a survey response was missing. They are used by the model as signals but are not shown to the employee because "you skipped a question" is not an actionable insight and may create anxiety about incomplete responses affecting their score. |
| Binary indicator: missing_mental_fatigue — records whether the employee skipped the mental_fatigue_score question     | Nothing                                    | Same rationale as above.                                                                                                                                                                                                                                                             |
| The two tenure interaction features (tenure_fatigue, tenure_workload) — used by the model, no employee-facing label   | Nothing                                    | Model features with no plain-language explanation; held back rather than shown as raw technical field names                                                                                                                                                                          |
| Reviewer status (whether a Critical flag has been reviewed)                                                           | Nothing                                    | Reviewer workflow is internal; the employee does not know their flag is pending review until review is complete                                                                                                                                                                      |
| HR or manager visibility status                                                                                       | Nothing                                    | The employee does not know who has seen their data — they only know what they have consented to                                                                                                                                                                                      |

The gap between what is stored and what is shown is the privacy boundary the DPO is being asked to approve. Section 4 covers the technical implementation of that boundary.

---

_Section 2 review complete. Awaiting confirmation before proceeding to Section 3._

---

## Section 3 — Tier Labels And What Each One Means

### The Four Tier Labels In Plain English

The risk tiers are not clinical diagnoses. They are indicators of where an employee's burnout probability falls relative to the scorable population and the thresholds set by their organisation. The labels are designed to be understandable without a technical background.

---

**LOW — "Your score is in the lower range"**

Your burnout probability is below 20%. This means your survey responses suggest a low level of burnout risk compared to the norm for your role. This is not a guarantee that you are not experiencing difficulty — it means the model did not detect the patterns associated with elevated burnout risk in your current responses.

**MODERATE — "Your score is above average but not yet high"**

Your responses show early patterns associated with burnout. Nothing is flagged to anyone else. You will see some suggested resources based on what your responses indicated.

**HIGH — "Your score is elevated"**

Your burnout probability is above the general population threshold. This means the model detected meaningful elevation in burnout-related patterns. At this tier, your manager receives a check-in prompt (not your individual score — a prompt to check in), and HR receives a team-level aggregate that does not identify you.

**CRITICAL — "Your score indicates significant elevated risk"**

Your burnout probability is in the highest band (above 90%). This is the model's signal that burnout patterns are pronounced. This tier does not mean you are in crisis — it means the model has high confidence that your responses show strong alignment with the burnout risk profile. A human reviewer must assess every Critical flag before any action is taken. You are never automatically escalated.

---

### What Each Tier Triggers

| Tier         | Employee sees                                                     | HR sees                                             | Manager sees      | What must happen                                                                                              |
| ------------ | ----------------------------------------------------------------- | --------------------------------------------------- | ----------------- | ------------------------------------------------------------------------------------------------------------- |
| **LOW**      | Their own trend line over time                                    | Nothing                                             | Nothing           | Nothing — routine monitoring continues                                                                        |
| **MODERATE** | Their score + curated resources matched to their top SHAP factors | Nothing                                             | Nothing           | Resources offered to the employee; no one else is notified                                                    |
| **HIGH**     | Their score + resources + explanation                             | Team aggregate (minimum n=5) — no individual scores | A check-in prompt | Manager is encouraged to check in; employee identity is not shared unless the employee chooses to share it    |
| **CRITICAL** | Their score + resources + explanation                             | Escalation to a human reviewer                      | Escalation alert  | A human reviewer must assess the flag before any action is taken. The employee is not automatically acted on. |

### The Clinical Disclaimer

The following statement appears on the employee dashboard alongside every tier result:

---

**Oraclaire does not diagnose burnout or any other medical or psychological condition.**

The risk tier is an indicator based on your survey responses — it is not a clinical assessment and should not be treated as one. It does not mean you are in crisis or that you need immediate intervention.

If you are experiencing a mental health crisis, please contact your organisation's employee assistance programme or a qualified mental health professional.

---

This disclaimer is part of what the DPO is being asked to approve — the tier labels and the disclaimer together.

---

_Section 3 review complete. Awaiting confirmation before proceeding to Section 4._

---

## Section 4 — Technical Constraints The DPO Must Understand

This section lists what the product cannot do. Some of these are enforced in code — they are impossible regardless of what anyone instructs. Others are enforced by contract — they depend on the customer honouring the Acceptable Use Policy. The distinction matters and is called out explicitly for each item.

| #   | Constraint                                | Enforced by                 | What this means in practice                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| --- | ----------------------------------------- | --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C3a | Critical tier model health ceiling — 5%   | Code                        | If more than 5% of employees in any cycle receive a Critical tier flag, the model health alert fires. The procedure is: (1) product surfaces alert to Product Owner; (2) individual Critical flags continue through the human review gate — no employee is left without review; (3) new assessment cycles pause pending Product Owner's investigation; (4) Product Owner determines whether this is a dataset composition shift, a model calibration failure, or a genuine organisational crisis, then decides: retrain, adjust threshold, or resume with a documented note. |
| C4  | Human review gate — every Critical flag   | Code + EU AI Act Article 14 | Every Critical flag goes to a human reviewer before HR sees anything. EU AI Act Article 14(4)(e) requires the ability to override the output. Non-compliance: Article 71 — fines up to EUR 20M or 4% global turnover. This constraint cannot be relaxed, lowered, or bypassed for any EU deployment.                                                                                                                                                                                                                                                                         |
| C5  | Minimum team size for any aggregate — n=5 | Code + GDPR Article 5(1)(c) | No aggregate HR visibility is produced for any team smaller than five people. This floor cannot be reduced at deployment. It can be increased if a customer's Data Protection Authority requires a higher threshold for their specific context. At n=5 the group is large enough that no individual can be re-identified from the aggregate — implementing k-anonymity as a product-level floor.                                                                                                                                                                             |
| C6a | Explicit consent — EU/GDPR                | Code + GDPR Article 9       | Burnout risk scores are health-adjacent data under GDPR Article 9. Processing requires Article 9(2)(a) explicit consent. Employees must actively opt in. Withdrawal triggers a 48-hour cooling-off period before any score is suppressed. Consent records are retained for audit.                                                                                                                                                                                                                                                                                            |
| C6b | Consent — Singapore/PDPA                  | Code + PDPA Part IV         | PDPA Part IV (Sections 13–14) requires consent for collection, use, and disclosure. Deemed-consent pathways under Section 15 are broader than GDPR but consent remains mandatory before any scoring.                                                                                                                                                                                                                                                                                                                                                                         |
| C6c | Consent — US (California)                 | Contractual                 | California CPRA treats health-adjacent data as sensitive personal information requiring opt-in. For California-based customers: deploy-time check required. No other US state has a comparable requirement at time of Sprint 1 launch.                                                                                                                                                                                                                                                                                                                                       |
| C7a | Retention — data minimisation principle   | Code + GDPR Article 5(1)(e) | Personal data cannot be retained beyond what is necessary for the assessment purpose. The principle is hard. When the retention period expires, data is deleted — no exceptions without explicit legal basis.                                                                                                                                                                                                                                                                                                                                                                |
| C7b | Retention — 12-month default              | Contractual + DPA review    | 12 months is the current operational default for quarterly trend tracking. This is a conservative starting point pending DPA confirmation of what "necessary" means for this specific purpose. DPA review required before any deployment goes live.                                                                                                                                                                                                                                                                                                                          |
| C8a | No HRIS write integration                 | Contractual (AUP)           | Scores cannot be exported to any HR system, performance tool, or external database. The product has no capability to do this — it is not just a policy restriction.                                                                                                                                                                                                                                                                                                                                                                                                          |

---

## Section 5 — The Specific Ask

Does the employee-facing presentation of **(a)** the SHAP waterfall format, **(b)** the risk tier labels, and **(c)** their combination on the dashboard together meet your organisation's standard for explainability of automated decision-making affecting employees under [applicable regulatory regime]?

---

**Reviewer details**

| Field                       |          |
| --------------------------- | -------- |
| Name                        |          |
| Organisation                |          |
| Date reviewed               |          |
| **Format approved**         | Yes / No |
| Conditions or modifications |          |
| Signature                   |          |

---

## Appendix A — Regulatory Mapping

| Regime         | Relevant article      | Oraclaire design response                                                                                                                                                             | Decision reference  |
| -------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- |
| GDPR           | Article 9(1)          | Special category (health) data is processed only with explicit consent; employees choose to complete the assessment and can withdraw consent at any time                              | D1, D27 Condition 1 |
| GDPR           | Article 5(1)(c)       | No team aggregate is shown if the team has fewer than five members. The floor is five and cannot be lowered.                                                                          | D28, D31b           |
| GDPR           | Article 7(4)          | Consent must be freely given — the product is designed so that opting out has no negative consequence; HR and managers cannot see individual scores without consent                   | D1, D6              |
| GDPR           | Article 22            | Employees see a plain-language explanation of how their score was generated; no solely automated decision with legal or significant effect without human review for Critical tier     | D8, D17             |
| GDPR           | Article 17            | Employees can exercise erasure rights; individual prediction records are retained only for the configured period and deleted on request                                               | D1, C7a/C7b         |
| PDPA Singapore | Part IV               | Consent and access rights implemented under Singapore law; employee data is not used for purposes beyond the assessment without separate consent                                      | D1                  |
| EU AI Act      | Annex III (high-risk) | Employee burnout scoring is a high-risk automated decision system under Annex III; the product is designed to meet Annex III requirements including human oversight for Critical tier | D8, D27             |
| EU AI Act      | Article 14            | Critical tier flags require human review before any action is taken; employees can request human review of any tier result                                                            | D8                  |

---

## Appendix B — Open Questions For The DPO

**Question 1 — Consent Freeness**

The product's consent architecture requires that employees complete a burnout assessment to receive their score. Does this constitute coercion — where the employee must consent to assessment to access workplace support resources, and the refusal to assess may itself carry implicit consequences? Under GDPR Article 7(4), consent is not free where there is a clear imbalance of power. How does your organisation assess whether consent obtained in this context is valid?

**Question 2 — Retention Period**

GDPR Article 5(1)(e) requires that personal data be kept only for as long as necessary. Oraclaire uses a 12-month default retention period for longitudinal trend tracking. What period does your DPA consider necessary for quarterly burnout assessment? Is 12 months appropriate, or does the longitudinal tracking purpose require a different justification?

**Question 3 — Right to Explanation**

The SHAP waterfall names which factors contributed to the score and in which direction. Is this enough for your organisation, or do you require disclosure of the model family, the threshold values, or the probability scores?

**Question 4 — DPA Notification**

This must be confirmed before the first employee sees their score. The pilot customer's legal team should identify the supervisory authority, confirm whether a DPIA under Article 35 has been completed, and confirm whether prior consultation under Article 36 applies. Oraclaire cannot make this determination on the customer's behalf.

**Question 5 — Critical Tier Health Data Inference**

Does the "Critical" tier label — as defined in Section 3 — constitute a health data inference under this deployment's jurisdiction that requires additional safeguards beyond what this package describes? This question was raised in Section 3 in the context of whether the tier label implies a clinical diagnosis. The answer depends on how the applicable DPA or regulator classifies a categorical burnout risk label that is inferred from survey responses but does not contain a medical diagnosis.
