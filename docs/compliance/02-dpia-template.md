# Oraclaire — Data Protection Impact Assessment Template

**Document type:** Data Protection Impact Assessment (DPIA) template
**Regulation:** EU AI Act (Article 35) + GDPR Articles 35–36
**Applies to:** EU-based customers and any customer processing EU residents' data
**Note:** This is a template. Customer-specific values MUST be filled in before deployment.

---

## 1. Template Metadata (Customer-Fill)

| Field                       | Value                      |
| --------------------------- | -------------------------- |
| Organisation name           | **[CUSTOMER NAME]**        |
| DPO contact                 | **[DPO EMAIL / NAME]**     |
| Assessment prepared by      | **[PREPARER NAME + ROLE]** |
| Assessment date             | **[DATE]**                 |
| Oraclaire system version    | **[MODEL VERSION TAG]**    |
| Previous DPIA date (if any) | **[PRIOR DATE / N/A]**     |

---

## 2. System Description

### 2.1 Nature of Processing

Oraclaire is a **workplace wellbeing analytics SaaS** that classifies employee burnout risk using machine learning on survey data. The system:

- Collects Copenhagen Burnout Inventory (CBI) assessments and weekly pulse surveys from employees
- Classifies employees into four burnout risk tiers: low, moderate, high, critical
- Provides HR administrators and managers with aggregate team-level risk dashboards
- Delivers individual-level scores to employees themselves after a 24-hour visibility delay
- Requires human HR reviewer approval before any intervention for Critical-tier employees

### 2.2 Scope of Processing

| Dimension          | Detail                                                                                                              |
| ------------------ | ------------------------------------------------------------------------------------------------------------------- |
| Data subjects      | Employees of the contracting organisation                                                                           |
| Data categories    | CBI responses (19 items), pulse survey responses (1 item), HRIS fields (tenure, seniority, company type, WFH setup) |
| Processing purpose | Burnout risk classification for organisational wellbeing                                                            |
| Legal basis        | GDPR Article 9(2)(b) — employment, occupational medicine                                                            |
| Retention          | Individual scores/responses: 12 months (configurable); aggregates: indefinite                                       |
| Volume             | [NUMBER] employees, [NUMBER] assessment cycles per year                                                             |

### 2.3 Human Review Requirements

No automated employment decisions are made. Every Critical-tier classification requires explicit HR reviewer approval. Override decisions are logged with reviewer identity, original tier, new tier, and written reason.

---

## 3. Necessity and Proportionality

### 3.1 Why This Processing Cannot Be Carried Out Without AI

- Burnout risk is a multi-dimensional construct not reducible to a single survey score
- The interaction between tenure and fatigue scores (tenure × fatigue, tenure × workload) requires statistical modelling to detect
- Manual HR review of all employees at the frequency required (monthly cycles) is operationally infeasible at scale
- Aggregate team-level risk indicators require standardised scoring across the workforce

### 3.2 Why the Specific Model Was Chosen

| Alternative Considered       | Reason for Rejection / Acceptance                                                                    |
| ---------------------------- | ---------------------------------------------------------------------------------------------------- |
| XGBoost                      | SHAP dominance by Mental Fatigue Score ≥65% — fails MFS gate (≥40% max) — rejected per D16           |
| Logistic Regression          | Lower predictive performance on training data; acceptable MFS contribution but insufficient accuracy |
| **Random Forest (Sprint 1)** | **Passes MFS dominance gate (<40%); acceptable accuracy; interpretable via SHAP**                    |

### 3.3 Data Minimisation

The system collects only:

- CBI and pulse survey responses (employee self-reported, minimised to validated scales)
- HRIS fields strictly required for scoring: tenure_days, seniority_tier, company_type, wfh_setup
- No precise location tracking, no biometric data, no performance metrics, no communications content

---

## 4. Risk Assessment

### 4.1 Inherent Risks

| Risk ID | Description                                                                                  | Likelihood | Impact   | Inherent Risk |
| ------- | -------------------------------------------------------------------------------------------- | ---------- | -------- | ------------- |
| R-01    | Inaccurate classification leads to unnecessary employee stress or inappropriate intervention | Medium     | High     | **High**      |
| R-02    | Bias in training data leads to disparate impact across demographic slices                    | Medium     | High     | **High**      |
| R-03    | Employee data breach exposes health-related survey responses                                 | Low        | Critical | **High**      |
| R-04    | Function creep — scores used for performance management or termination                       | Medium     | Critical | **Critical**  |
| R-05    | Inadequate notice to employees of monitoring and scoring                                     | Low        | High     | **Medium**    |
| R-06    | Third-party model provider receives training data                                            | Low        | High     | **Medium**    |
| R-07    | Cross-border transfer to non-adequate jurisdiction                                           | Low        | High     | **Medium**    |

### 4.2 Mitigations and Residual Risks

| Risk ID | Mitigation                                                                                                                 | Residual Likelihood | Residual Impact | Residual Risk |
| ------- | -------------------------------------------------------------------------------------------------------------------------- | ------------------- | --------------- | ------------- |
| R-01    | Two-threshold calibration (FN ceiling controls); human review gate for Critical tier                                       | Low                 | Medium          | **Low**       |
| R-02    | Pre-deployment bias audit (≥10pp HC-rate gap = flag); annual bias audit                                                    | Low                 | Medium          | **Low**       |
| R-03    | AES-256 encryption at rest; TLS 1.3 in transit; no raw PII in logs; SOC 2 Type II [PENDING]                                | Low                 | High            | **Medium**    |
| R-04    | API blocks HRIS export; score data schema divorced from HRIS fields; governance notice in contract                         | Very Low            | Critical        | **Low**       |
| R-05    | 24h employee-first visibility gate; plain-language explanation right; consent management UI                                | Very Low            | Low             | **Low**       |
| R-06    | No training data transmitted to third-party; Kaggle dataset is synthetic / public; no real employee data in model training | Very Low            | Medium          | **Low**       |
| R-07    | Data residency: EU-based deployment only; no transfer to non-adequate jurisdictions without SCC                            | Very Low            | Medium          | **Low**       |

### 4.3 Bias Audit Results

Per-deployment automated bias audit compares Critical+High tier rates across:

- Seniority tier (junior / senior)
- Company type (Product / Service)
- WFH setup (available / not available)

A slice is **flagged** if its HC rate differs from the overall population rate by more than **10 percentage points**.

Results from most recent audit: **[POPULATE WITH ACTUAL AUDIT OUTPUT]**

---

## 5. Data Flows

### 5.1 Assessment Collection Flow

```
Employee (browser)
    ↓ HTTPS (TLS 1.3)
Streamlit Frontend — [ORGANISATION-SPECIFIC DOMAIN]
    ↓ HTTPS
Nexus API (FastAPI backend) — [EU REGION / CUSTOMER TENANT]
    ↓ Internal
PostgreSQL (SQLAlchemy ORM)
    ↓ (model inference)
Python process — [SCORING ENGINE]
    ↓
RiskScore record → AuditLog → AuditLog table
```

### 5.2 Data Categories in Flow

| Step           | Data In Scope                                                                                 | Encrypted      |
| -------------- | --------------------------------------------------------------------------------------------- | -------------- |
| Browser → API  | Employee ID (pseudonymised), survey responses                                                 | TLS 1.3        |
| API → Database | All fields below                                                                              | TLS + at-rest  |
| Scoring engine | Feature vector (10 features, no raw survey content)                                           | In-memory only |
| Logs           | Employee ID, score, tier, SHAP top feature — **no** raw survey responses                      | TLS            |
| HR Dashboard   | Aggregate team data only (≥5 members); individual scores only after 24h gate + employee-first | TLS            |

### 5.3 No Raw Survey Content in Logs

Raw CBI item responses are **never** written to log files or audit logs. Only:

- Numeric burnout probability
- Risk tier
- Top-5 SHAP feature names and values
- Employee ID (pseudonymised)

---

## 6. Cross-Border Transfer Safeguards

Oraclaire is deployed on EU-based infrastructure only. No data is transferred to non-adequate jurisdictions without Standard Contractual Clauses (SCCs) per GDPR Article 46.

| Destination           | Safeguard                            | Basis        |
| --------------------- | ------------------------------------ | ------------ |
| EU / EEA              | No transfer — local processing       | Adequacy     |
| [NON-EU JURISDICTION] | **[POPULATE: SCC / BCR / ADEQUACY]** | GDPR Art. 46 |

---

## 7. Retention and Deletion

| Data Category            | Retention Period                          | Deletion Method                    |
| ------------------------ | ----------------------------------------- | ---------------------------------- |
| Individual CBI responses | 12 months (configurable per org)          | Hard delete after retention period |
| Pulse responses          | 12 months (configurable per org)          | Hard delete after retention period |
| Risk scores              | 12 months (configurable per org)          | Hard delete after retention period |
| Audit logs               | 36 months (minimum for AI Act compliance) | Hard delete                        |
| Team aggregates          | Indefinite                                | Not applicable                     |

Withdrawal of consent triggers exclusion within **48 hours**. Withdrawn employees are excluded from scoring and aggregates.

---

## 8. Data Subject Rights

| Right                                  | Mechanism                                                                |
| -------------------------------------- | ------------------------------------------------------------------------ |
| Right of access (Art. 15)              | Employee can view own scores via `/api/employee/me/scores`               |
| Right to explanation (Art. 13(2)(f))   | Plain-language SHAP breakdown via `/api/employee/me/explanation`         |
| Right to rectification (Art. 16)       | Not applicable — survey responses are historical facts                   |
| Right to erasure (Art. 17)             | Withdrawal of consent triggers 48h exclusion + 12-month hard delete      |
| Right to restrict processing (Art. 18) | Consent management UI — employee can pause participation                 |
| Right to data portability (Art. 20)    | Not applicable — legitimate interest / employment law basis, not consent |
| Right to object (Art. 21)              | Withdrawal of consent = objection to processing; processed within 48h    |

---

## 9. Consultation

### 9.1 DPO Consultation

| Item                | Detail               |
| ------------------- | -------------------- |
| DPO was consulted   | [YES / DATE]         |
| DPO recommendations | [POPULATE OR "NONE"] |

### 9.2 Works Council / Employee Representative

| Jurisdiction | Requirement                                                | Status           |
| ------------ | ---------------------------------------------------------- | ---------------- |
| Germany      | Betriebsrat consultation if performance monitoring         | [REQUIRED / N/A] |
| France       | Comité social et économique (CSE) information/consultation | [REQUIRED / N/A] |
| EU (general) | Information/consultation under national transpositions     | [REQUIRED / N/A] |

_Jurisdictional gating service (`JurisdictionalGatingService`) MUST be consulted before deployment to any EU jurisdiction to determine applicable requirements._

### 9.3 AI Ethics Board

| Item                             | Detail                       |
| -------------------------------- | ---------------------------- |
| Internal ethics review conducted | [YES / DATE / N/A]           |
| External audit conducted         | [YES / AUDITOR / DATE / N/A] |

---

## 10. Technical and Organisational Measures

### 10.1 Security Measures

| Measure                  | Implementation                                                            |
| ------------------------ | ------------------------------------------------------------------------- |
| Encryption at rest       | AES-256 for database and file storage                                     |
| Encryption in transit    | TLS 1.3 for all API and frontend traffic                                  |
| Access control           | Role-based (HR_ADMIN, MANAGER, EMPLOYEE, SYSTEM_ADMIN); JWT Bearer tokens |
| Audit logging            | All data access and modification events written to AuditLog table         |
| Vulnerability management | [PENDING: penetration test schedule]                                      |
| Incident response        | [PENDING: incident response plan]                                         |

### 10.2 Organisational Measures

| Measure             | Implementation                                                                   |
| ------------------- | -------------------------------------------------------------------------------- |
| Employee notice     | Privacy notice delivered at first assessment; consent management UI              |
| Manager access      | Aggregate team data only; individual scores only after 24h employee-first gate   |
| No HRIS export      | API blocks all responses that would facilitate score export to HRIS or PMS       |
| Governance training | HR administrators receive training on AI Act obligations before first deployment |

---

## 11. Review and Monitoring

| Item                       | Frequency                      | Responsible              |
| -------------------------- | ------------------------------ | ------------------------ |
| Bias audit                 | Per deployment + annual        | Oraclaire / Customer DPO |
| Model SHAP dominance check | Per model version promotion    | Oraclaire                |
| Participation rate review  | Per cycle                      | Customer HR              |
| DPIA review                | Annual or upon material change | Customer DPO + Oraclaire |
| Threshold drift check      | Per cycle                      | Oraclaire automated      |

---

## 12. Sign-Off

| Role                           | Name | Date | Signature |
| ------------------------------ | ---- | ---- | --------- |
| Customer DPO                   |      |      |           |
| Customer HR Administrator      |      |      |           |
| Oraclaire Product Owner        |      |      |           |
| Oraclaire Data Protection Lead |      |      |           |

---

_Template version: 1.0 — Oraclaire Sprint 1 — EU AI Act DPIA Template_
