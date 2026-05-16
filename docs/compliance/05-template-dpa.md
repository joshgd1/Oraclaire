# Oraclaire — Template Data Processing Agreement

**Document type:** Data Processing Agreement (DPA)
**Regulation:** GDPR Articles 28–30
**Applies to:** EU-based customers and customers processing EU residents' personal data
**Purpose:** Governs the processing of personal data on behalf of the customer (data controller)

---

## 1. Definitions

| Term                      | Definition                                                                                         |
| ------------------------- | -------------------------------------------------------------------------------------------------- |
| **Personal Data**         | Any information relating to an identified or identifiable natural person (Article 4(1) GDPR)       |
| **Processing**            | Any operation performed on Personal Data (Article 4(2) GDPR)                                       |
| **Data Controller**       | The customer — determines the purposes and means of processing                                     |
| **Data Processor**        | Oraclaire — processes Personal Data on behalf of and under the instructions of the Data Controller |
| **Sub-processor**         | Any third party engaged by Oraclaire to process Personal Data                                      |
| **Supervisory Authority** | The relevant EU data protection authority                                                          |

---

## 2. Subject Matter and Nature of Processing

### 2.1 Subject Matter

Oraclaire provides a workplace wellbeing analytics service that processes employee burnout assessment data using machine learning. The processing involves:

- Collection of Copenhagen Burnout Inventory (CBI) survey responses and weekly pulse surveys
- Feature extraction and transformation of survey data into burnout risk indicators
- Machine learning inference to classify burnout risk into four tiers
- SHAP-based explanation generation for individual risk scores
- Aggregate reporting for HR administrators and managers

### 2.2 Nature of Processing

The processing is **automated**, with one exception: Critical-tier classifications require review and approval by an HR reviewer before any organisational action is taken. The processing does **not** involve profiling within the meaning of Article 22(1) that would produce legal effects or similarly significant effects.

---

## 3. Purpose Limitation

Oraclaire processes Personal Data **only** for the following purposes:

1. Classifying employee burnout risk using validated machine learning models
2. Generating plain-language explanations of risk classifications for employees
3. Producing aggregate team-level wellbeing indicators for HR planning
4. Supporting HR reviewers in identifying employees requiring wellbeing interventions
5. Compliance with applicable workplace health and safety obligations

Oraclaire will not process Personal Data for any purpose other than those listed above.

---

## 4. Duration of Processing

### 4.1 Contract Duration

Processing under this DPA continues for the duration of the service agreement.

### 4.2 Post-Termination

Upon termination of the service agreement:

- Oraclaire will, at the Data Controller's election, return or securely delete all Personal Data
- Oraclaire will provide written confirmation of deletion within 30 calendar days
- Audit logs will be retained for 36 months from the date of creation, then securely deleted
- The foregoing obligations apply except to the extent that EU law or the law of an EU member state requires longer retention

---

## 5. Types of Personal Data and Data Subjects

### 5.1 Categories of Data Subjects

| Category          | Description                                                             |
| ----------------- | ----------------------------------------------------------------------- |
| Employees         | Employees of the Data Controller participating in Oraclaire assessments |
| Managers          | Employees of the Data Controller with team oversight responsibilities   |
| HR Administrators | Employees of the Data Controller with HR system administration access   |

### 5.2 Categories of Personal Data

| Data Category        | Examples                                | Special Category           |
| -------------------- | --------------------------------------- | -------------------------- |
| Assessment responses | CBI items, pulse survey responses       | Health-related (Article 9) |
| HRIS identifiers     | Employee ID, team ID, tenure days       | Not special category       |
| HRIS attributes      | Seniority tier, company type, WFH setup | Not special category       |
| Risk classifications | Numeric score, risk tier, SHAP values   | Health-related (Article 9) |
| Audit records        | Access logs, modification records       | Not special category       |

### 5.3 Special Category Data

Oraclaire processes **health-related Personal Data** (Article 9 GDPR) as part of the burnout risk classification. The legal basis for this processing is **Article 9(2)(b) GDPR** — processing necessary for the purposes of carrying out the obligations and exercising specific rights of the controller or of the data subject in the field of employment.

---

## 6. Rights and Obligations of Oraclaire (Data Processor)

### 6.1 Oraclaire Will:

| Obligation                                                                           | Implementation                                                       |
| ------------------------------------------------------------------------------------ | -------------------------------------------------------------------- |
| Process Personal Data only on documented instructions from the Data Controller       | This DPA constitutes documented instructions                         |
| Ensure persons authorised to process Personal Data have committed to confidentiality | All Oraclaire personnel sign confidentiality agreements              |
| Implement appropriate technical and organisational measures                          | TLS 1.3, AES-256, role-based access, audit logging                   |
| Not engage sub-processors without prior written authorisation                        | See §8 (Sub-processors)                                              |
| Assist the Data Controller in ensuring compliance with Articles 32–36                | Technical and organisational measures in place; audit logs available |
| Delete or return all Personal Data on termination                                    | See §4.2 (Post-Termination)                                          |
| Make available all information necessary to demonstrate compliance                   | Audit logs, DPIA template, conformity assessment available           |
| Notify the Data Controller of any Personal Data breach within 72 hours               | Notification to the contact designated in §12                        |

### 6.2 Oraclaire Will Not:

| Prohibition                                                         | Implementation                                                              |
| ------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Transfer Personal Data outside the EU without authorisation         | Data residency locked to EU regions                                         |
| Sell or monetise Personal Data                                      | Not applicable — Oraclaire does not trade in customer data                  |
| Use Personal Data for any purpose other than the contracted service | Technical blocks prevent HRIS export and performance management integration |
| Engage sub-processors outside the approved list                     | All sub-processors must be pre-approved per §8                              |

---

## 7. Rights and Obligations of the Customer (Data Controller)

### 7.1 The Customer Will:

| Obligation                                                                       | Implementation                                                             |
| -------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Be responsible for compliance with GDPR obligations as Data Controller           | Customer is the Data Controller under GDPR                                 |
| Ensure there is a lawful basis for processing before sharing data with Oraclaire | Legitimate interests assessment or employment law basis documented         |
| Ensure data subjects are provided with required notices                          | Privacy notice template provided in Oraclaire onboarding                   |
| Ensure consent mechanisms meet GDPR requirements where consent is used           | Consent management UI provided; withdrawal within 48 hours                 |
| Notify Oraclaire of any Personal Data breach without undue delay                 | Notification to `security@oraclaire.io`                                    |
| Ensure that Oraclaire is only used for lawful, permitted purposes                | Acceptable Use Policy (04-acceptable-use-policy.md) governs permitted uses |

---

## 8. Sub-Processors

### 8.1 Authorised Sub-Processors

Oraclaire uses the following sub-processors (as of the effective date):

| Sub-processor               | Purpose                               | Country   | Safeguard                |
| --------------------------- | ------------------------------------- | --------- | ------------------------ |
| AWS EU (Ireland/Frankfurt)  | Cloud infrastructure and data hosting | EU        | DPA + encryption at rest |
| [ADDITIONAL SUB-PROCESSORS] | [PURPOSE]                             | [COUNTRY] | [SAFEGUARD]              |

### 8.2 Approval Process

The Data Controller grants **general written authorisation** for the engagement of sub-processors listed in §8.1. Oraclaire will notify the Data Controller of any intended changes to sub-processors at least 30 days before the change takes effect. The Data Controller may object to a new sub-processor within 15 days; if objection cannot be resolved, either party may terminate the service agreement.

### 8.3 Sub-processor Obligations

Sub-processors engaged by Oraclaire are required to:

- Process Personal Data only for the purposes of providing the contracted service
- Implement the same technical and organisational measures as Oraclaire
- Notify Oraclaire immediately if they cannot meet their obligations
- Be liable to Oraclaire for any failure to meet their obligations

---

## 9. Technical and Organisational Measures

Oraclaire implements the following technical and organisational measures (Article 32 GDPR):

| Measure               | Implementation                                                                        |
| --------------------- | ------------------------------------------------------------------------------------- |
| Pseudonymisation      | Employee IDs are pseudonymised; raw survey responses are not stored                   |
| Encryption at rest    | AES-256 for all stored data                                                           |
| Encryption in transit | TLS 1.3 for all API and frontend traffic                                              |
| Confidentiality       | Role-based access control; JWT authentication; principle of least privilege           |
| Integrity             | Audit logs for all data access and modification; cryptographic integrity verification |
| Availability          | Automated backups; disaster recovery plan; 99.9% uptime SLA                           |
| Resilience            | Redundant infrastructure across EU availability zones                                 |
| Assessment            | Regular security testing and vulnerability assessments                                |

---

## 10. International Transfers

Oraclaire does not transfer Personal Data outside the European Economic Area (EEA). If future functionality requires transfers, Oraclaire will implement appropriate safeguards (Standard Contractual Clauses, adequacy decision, or binding corporate rules) before any transfer.

---

## 11. Data Protection Impact Assessment

Where the Data Controller is required to conduct a Data Protection Impact Assessment (DPIA) under Article 35 GDPR, Oraclaire will provide:

- The DPIA template (02-dpia-template.md) completed with Oraclaire-specific information
- Information about the logic involved in the processing
- Information about the safeguards and protection measures in place

The Data Controller remains responsible for conducting the DPIA and consulting the supervisory authority where required.

---

## 12. Contact Points

| Role                           | Contact                                  |
| ------------------------------ | ---------------------------------------- |
| Oraclaire Data Protection Lead | `privacy@oraclaire.io`                   |
| Oraclaire Security             | `security@oraclaire.io`                  |
| Customer Data Controller       | [CUSTOMER CONTACT — TO BE COMPLETED]     |
| Customer DPO                   | [CUSTOMER DPO CONTACT — TO BE COMPLETED] |

---

## 13. Audit Rights

The Data Controller has the right to audit Oraclaire's compliance with this DPA. Oraclaire will make available:

- Copies of its most recent security audit report (SOC 2 Type II — [PENDING])
- Information necessary to demonstrate compliance with this DPA
- The results of any relevant assessments or certifications

On-site audits will be scheduled with at least 30 days' notice and conducted in a manner that minimises disruption to operations.

---

## 14. Liability

Oraclaire's liability for breaches of this DPA is governed by the service agreement. Nothing in this DPA limits Oraclaire's liability for:

- Death or personal injury caused by negligence
- Fraud or fraudulent misrepresentation
- Breach of obligations under applicable data protection law

---

## 15. Governing Law and Jurisdiction

This DPA is governed by the law of the EU member state in which the Data Controller is established. Any dispute arising under this DPA will be subject to the exclusive jurisdiction of the courts of that member state.

---

_Template version: 1.0 — Oraclaire Sprint 1 — GDPR Articles 28-30 Data Processing Agreement Template_
