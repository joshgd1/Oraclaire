# Oraclaire — Singapore PDPA Compliance Addendum

**Document type:** Jurisdictional compliance addendum
**Regulation:** Personal Data Protection Act 2012 (Act 26 of 2012) as amended by the 2020 amendments
**Applies to:** Singapore-based customers and customers processing Singapore residents' data
**Relationship to main assessment:** Supplements `01-conformity-assessment.md`; this addendum addresses PDPA-specific obligations not covered by the EU AI Act framework

---

## 1. Overview

The Personal Data Protection Act (PDPA) governs the collection, use, and disclosure of personal data in Singapore. Oraclaire processes employee burnout assessment data which constitutes personal data under the PDPA (specifically, data concerning the mental health of identifiable individuals).

This addendum addresses the PDPA-specific obligations that supplement Oraclaire's baseline EU AI Act conformity assessment.

---

## 2. Data Classification

| Category                  | PDPA Classification            | Oraclaire Handling                                                         |
| ------------------------- | ------------------------------ | -------------------------------------------------------------------------- |
| Employee survey responses | Personal data (health-related) | Collected with explicit consent; used only for burnout risk classification |
| Risk tier classifications | Personal data (health-related) | Stored with 12-month retention; employee-accessible                        |
| Aggregated team data      | De-identified when team ≥5     | Published only when team has ≥5 contributing members                       |
| SHAP decomposition        | Personal data (health-related) | Employee-accessible via right-to-explanation endpoint                      |
| Audit logs                | Personal data                  | Retained 36 months; access restricted to HR administrators                 |

---

## 3. Consent and Notification

### 3.1 Consent Mechanism

Under the PDPA, the **legitimate purpose** exception (Second Schedule, §1) applies to employee data processed for organisational wellbeing purposes. However, for health-related data (which burnout assessment constitutes), the **consent obligation is heightened**.

| Obligation                  | Implementation                                                                                   |
| --------------------------- | ------------------------------------------------------------------------------------------------ |
| Notify employees of purpose | Privacy notice delivered at first assessment login; visible before any survey is shown           |
| Consent must be voluntary   | Employee may decline individual assessments; participation rate tracked but not enforced         |
| Withdrawal of consent       | `PATCH /api/employee/me` with `consent_status=withdrawn`; exclusion takes effect within 48 hours |
| Minimize collection         | Only CBI/pulse responses and HRIS fields required for scoring are collected                      |

### 3.2 Employee Notification Content

At first assessment, employees receive:

- Identity of the organisation collecting the data
- Purpose: burnout risk assessment for organisational wellbeing
- Types of data collected: survey responses, tenure, seniority, company type, WFH setup
- How data is used: ML classification into risk tiers
- Who has access: HR administrators, own manager (aggregate only), employee themselves
- Retention period: 12 months for individual data; 36 months for audit logs
- Right to access and correct: via employee self-service portal
- Right to withdraw consent: via consent management UI

---

## 4. Access and Correction Rights

### 4.1 Access Right (Section 21)

Employees may request access to their personal data via:

- **Self-service**: `GET /api/employee/me/scores` — returns all risk scores
- **Self-service**: `GET /api/employee/me/explanation` — returns SHAP decomposition
- **Self-service**: `GET /api/employee/me/trajectory` — returns trend classification

The system responds to access requests within **3 business days** (PDPA requirement).

### 4.2 Correction Right (Section 22)

Employees may request correction of inaccurate personal data. For Oraclaire:

- Survey responses are historical facts and **cannot be corrected** (the score reflects the response at the time)
- Demographic data (seniority_tier, team_id) may be updated via `PATCH /api/employee/me`
- Incorrect risk classifications are corrected by the system when underlying data is corrected

---

## 5. Data Retention

| Data Category                   | PDPA Retention Rule                        | Oraclaire Implementation             |
| ------------------------------- | ------------------------------------------ | ------------------------------------ |
| Individual assessment responses | Retain only as long as purpose requires    | 12 months; hard deleted thereafter   |
| Risk scores                     | Retain only as long as purpose requires    | 12 months; hard deleted thereafter   |
| Audit logs                      | Retain for 36 months minimum               | AuditLog table; 36-month hard delete |
| Team aggregates                 | Not personal data when team ≥5             | Retained indefinitely                |
| Withdrawal records              | Retain record of withdrawal (not the data) | Consent timestamp retained for audit |

---

## 6. Data Protection Obligations

### 6.1 Reasonable Purpose

Oraclaire is deployed only for **organisational wellbeing purposes** — identifying employees at risk of burnout to enable timely intervention. Use for any other purpose (performance management, promotion decisions, termination) constitutes a **contractual violation** and is technically blocked by the API (see §6.2).

### 6.2 Technical Blocks on Prohibited Use

The Oraclaire API enforces purpose limitation technically:

| Prohibited Use                             | Technical Block                                                       |
| ------------------------------------------ | --------------------------------------------------------------------- |
| Export individual scores to HRIS           | API returns 403 with `BLOCKED_HRIS_EXPORT` code                       |
| Bulk download of employee scores           | API enforces team-size suppression (≥5) on all aggregate endpoints    |
| Score data linked to performance metrics   | No `employee_id` field on any performance-related table               |
| Intervention decision without human review | Critical-tier scores held in `pending_review` state until HR approval |

### 6.3 Data Leak Prevention

| Threat                                                   | Mitigation                                                                                                       |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Employee sees peer's individual score                    | Individual scores visible only to the employee themselves                                                        |
| Manager sees individual score for performance discussion | Manager aggregate endpoint returns team-level data only; individual scores delayed 24h after employee-first gate |
| HR administrator shares individual data externally       | AuditLog tracks every data access; data residency locked to Singapore/Singapore-region infrastructure            |
| Accidental exposure via logs                             | Raw survey responses never written to logs; only feature names and SHAP values logged                            |

---

## 7. Data Breach Response

### 7.1 Breach Classification

| Severity | Definition                                       | Response Timeline                                               |
| -------- | ------------------------------------------------ | --------------------------------------------------------------- |
| Minor    | ≤10 employees affected; no health data disclosed | Notify DPO within 3 calendar days                               |
| Major    | >10 employees affected OR health data disclosed  | Notify PDPC within 3 calendar days; notify affected individuals |
| Critical | Systemic breach affecting all employees          | Notify PDPC immediately; public disclosure                      |

### 7.2 Breach Notification Content (PDPA Section 26C)

In the event of a breach affecting ≥500 individuals, Oraclaire will provide:

- Description of the breach
- Types of personal data involved
- Steps taken to contain the breach
- Recommended actions for affected individuals
- Contact details for further information

---

## 8. Third-Party Disclosures

Oraclaire does not disclose employee personal data to third parties except:

| Recipient                                             | Purpose                  | Safeguard                                   |
| ----------------------------------------------------- | ------------------------ | ------------------------------------------- |
| AWS Singapore (or customer's designated cloud region) | Data hosting             | DPA between Oraclaire and cloud provider    |
| Customer HR administrators                            | Organisational oversight | Role-based access within Oraclaire platform |
| No other third parties                                | Not applicable           | Oraclaire does not sell or share data       |

Oraclaire's ML model training uses the **Kaggle MBI dataset** (synthetic/public), not customer data. Customer employee data is **never transmitted to model training infrastructure**.

---

## 9. Cross-Border Transfers

Singapore PDPA requires that personal data transferred outside Singapore receives **at least the same level of protection** as under the PDPA.

| Destination                        | Safeguard                           | Basis                        |
| ---------------------------------- | ----------------------------------- | ---------------------------- |
| Singapore / Singapore-region cloud | No transfer — local processing      | Adequate protection          |
| EU (if customer multi-region)      | Standard Contractual Clauses (SCCs) | PDPA Third Transfer guidance |
| Other jurisdictions                | Case-by-case DPA assessment         | Requires customer DPO review |

---

## 10. PDPA-Specific Governance

### 10.1 Data Protection Officer (DPO)

| Role          | Requirement                                                                         | Oraclaire Implementation                                         |
| ------------- | ----------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Customer DPO  | Required for organisations with ≥50 employees or handling significant personal data | Customer appoints their own DPO                                  |
| Oraclaire DPO | Required as data processor                                                          | Oraclaire designates a DPO contactable at `privacy@oraclaire.io` |

### 10.2 Data Protection by Design

Oraclaire implements data protection by design by:

- Collecting only data necessary for burnout risk classification
- Enforcing purpose limitation through technical access controls
- Providing employees with access, explanation, and withdrawal rights
- Retaining data only for the minimum period necessary
- Maintaining comprehensive audit logs

### 10.3 Assessment Review

This addendum is reviewed:

- Annually
- Upon material change to Oraclaire's data processing
- Upon change to PDPA regulations or guidance from the PDPC

---

## 11. Relationship to EU AI Act Framework

Where Oraclaire is deployed for an EU-based customer who also has Singapore operations (or vice versa), both addenda apply simultaneously. In case of conflict:

| Scenario                                     | Resolution                                                |
| -------------------------------------------- | --------------------------------------------------------- |
| EU AI Act requires more stringent protection | EU AI Act standard prevails                               |
| PDPA requires more stringent protection      | PDPA standard prevails                                    |
| Conflict cannot be resolved                  | Contact `privacy@oraclaire.io` for case-specific guidance |

The EU AI Act conformity assessment (`01-conformity-assessment.md`) and this PDPA addendum are **complementary**, not mutually exclusive.

---

_Addendum version: 1.0 — Oraclaire Sprint 1 — Singapore PDPA Compliance Addendum_
