# Oraclaire — Crisis Communication Plan

**Document type:** Crisis communication plan
**Classification:** Internal — for Oraclaire team and designated customer incident contacts
**Activation trigger:** Any crisis-level event involving Oraclaire or customer data

---

## 1. Crisis Severity Classification

| Level             | Definition                                                             | Examples                                                                         | Response Timeline              |
| ----------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------------- | ------------------------------ |
| **P1 — Critical** | Active data breach or systemic service failure affecting all customers | Full database exfiltration; all customers' data exposed; complete service outage | Immediate — 15 minute response |
| **P2 — Major**    | Significant breach or failure affecting multiple customers             | Partial data exposure; individual customer data leaked; extended outage          | 1 hour response                |
| **P3 — Moderate** | Limited incident with contained impact                                 | Single customer affected; isolated data access anomaly; degraded performance     | 4 hour response                |
| **P4 — Minor**    | Issue with no immediate data or service impact                         | Internal monitoring alert; potential vulnerability identified                    | Next business day              |

---

## 2. Response Team

### 2.1 Core Team

| Role                  | Responsibilities                                                        | Contact                 |
| --------------------- | ----------------------------------------------------------------------- | ----------------------- |
| Incident Commander    | Coordinates response; makes decisions; interfaces with external parties | `incident@oraclaire.io` |
| Engineering Lead      | Technical response; root cause analysis; remediation                    | PagerDuty escalation    |
| Data Protection Lead  | GDPR/PDPA notification obligations; regulator communication             | `privacy@oraclaire.io`  |
| Customer Success Lead | Customer communication; status page updates                             | `support@oraclaire.io`  |
| Legal Counsel         | Liability assessment; contract review; regulatory contact               | `legal@oraclaire.io`    |

### 2.2 Escalation Path

```
P4/P3: Engineering Lead → Data Protection Lead → Incident Commander
P2:      Engineering Lead → Data Protection Lead → Incident Commander → CEO
P1:      All core team → CEO → External counsel → Regulator notification
```

---

## 3. Internal Communication

### 3.1 Incident Channel

Upon activation:

1. Create a dedicated Slack channel: `#incident-YYYY-MM-DD-[short-description]`
2. Post initial notice using the template in §3.3
3. Update every **30 minutes** for P1/P2; every **2 hours** for P3
4. Transition to summary mode (hourly) once root cause identified and mitigation in progress

### 3.2 Status Page

Maintain `status.oraclaire.io` throughout the incident:

| Status                   | Meaning                                                     |
| ------------------------ | ----------------------------------------------------------- |
| **Operational**          | All systems functioning normally                            |
| **Degraded Performance** | Elevated latency or reduced throughput; no data impact      |
| **Partial Outage**       | Some functionality unavailable; no data impact              |
| **Major Outage**         | Significant functionality unavailable; no data impact       |
| **Data Breach**          | Confirmed or suspected unauthorised access to customer data |

### 3.3 Initial Notice Template

```
INCIDENT DECLARED — [SEVERITY]
Time: [HH:MM UTC]
Detected: [source of detection]
Affected: [customers / systems / data]
Current status: [what is known]
Immediate actions: [steps taken]
Next update: [HH:MM UTC]

@incident-team: join #incident-YYYY-MM-DD-[short-description]
```

### 3.4 Stakeholder Communication Cadence

| Audience                   | Cadence                                    | Channel                     |
| -------------------------- | ------------------------------------------ | --------------------------- |
| Internal team              | Every 30 min (P1/P2) / 2 hours (P3)        | Slack #incident channel     |
| All customers              | Per incident severity below                | Email + status page         |
| Affected customers only    | Per incident severity below                | Direct email                |
| Regulators (if applicable) | As required by law                         | Formal written notification |
| Public (if required)       | Only for P1 with confirmed public exposure | Press release + social      |

---

## 4. Customer Communication

### 4.1 Notification Thresholds

| Severity | Customer notification                     | Regulator notification                                                             | Timeline                                |
| -------- | ----------------------------------------- | ---------------------------------------------------------------------------------- | --------------------------------------- |
| P1       | All customers (service impact)            | PDPC within 72h if Singapore data affected; supervisory authority per GDPR Art. 33 | Within 2 hours of incident confirmation |
| P2       | Affected customers only                   | If Singapore data: PDPC within 72h; if EU data: supervisory authority within 72h   | Within 4 hours of incident confirmation |
| P3       | Affected customer only (if data involved) | Only if breach confirmed                                                           | Within 24 hours of confirmation         |
| P4       | Not required                              | Not required                                                                       | Not applicable                          |

### 4.2 Customer Notification Template

```
SUBJECT: [Oraclaire] Security Incident — [DATE] — Action Required

Dear [Customer Name],

Oraclaire is writing to notify you of a security incident that may have affected your organisation's data.

What happened:
[Plain-language description of the incident — what, when, how discovered]

What data may be affected:
[Specific data categories and approximate records if known]

What we are doing:
[Steps taken to contain the incident and protect data]

What you need to do:
[Recommended actions for the customer and their employees]

Timeline:
- [Date/time]: Incident detected
- [Date/time]: Incident contained
- [Date/time]: Investigation began
- [Date/time]: Customers notified (this communication)

We will provide updates as our investigation continues. The next update will be sent by [DATE/TIME].

If you have questions, please contact:
- Technical support: support@oraclaire.io
- Privacy inquiries: privacy@oraclaire.io

We sincerely apologise for this incident.

Oraclaire Security Team
```

---

## 5. Regulatory Notification

### 5.1 GDPR — Supervisory Authority (Article 33)

**When:** Within **72 hours** of becoming aware of a personal data breach (unless the breach is unlikely to result in a risk to the rights and freedoms of natural persons).

**Content requirements:**

1. Nature of the breach including categories and approximate number of data subjects concerned
2. DPO contact point
3. Likely consequences of the breach
4. Measures taken or proposed to address the breach

**Where to report:** The supervisory authority of the EU member state where the data controller is established.

### 5.2 Singapore PDPA — PDPC (Section 26C)

**When:** As soon as practicable, but no later than **3 calendar days** after the breach.

**When breach notification is required:** If the breach has or is likely to have a significant impact on the affected individuals.

**Content requirements:**

1. Nature of the breach
2. Data affected
3. Steps taken to address the breach
4. Recommendations for affected individuals

### 5.3 Notification Contacts

| Jurisdiction                           | Authority                               | URL                                                       |
| -------------------------------------- | --------------------------------------- | --------------------------------------------------------- |
| EU (lead authority varies by customer) | Relevant national supervisory authority | `https://edpb.europa.eu/about-edpb/about-edpb/members_en` |
| Singapore                              | Personal Data Protection Commission     | `https://www.pdpc.gov.sg`                                 |

---

## 6. Incident Phases

### Phase 1 — Detection and Assessment (0–30 minutes)

| Action                                    | Owner              |
| ----------------------------------------- | ------------------ |
| Confirm incident and classify severity    | Engineering Lead   |
| Declare incident and create Slack channel | Incident Commander |
| Post initial status to status page        | Engineering Lead   |
| Notify core team                          | Incident Commander |

### Phase 2 — Containment (30 minutes–2 hours)

| Action                                    | Owner                 |
| ----------------------------------------- | --------------------- |
| Isolate affected systems                  | Engineering Lead      |
| Preserve evidence (logs, database state)  | Engineering Lead      |
| Assess scope of data exposure             | Data Protection Lead  |
| Prepare customer notification if required | Customer Success Lead |

### Phase 3 — Investigation (2–24 hours)

| Action                                     | Owner                        |
| ------------------------------------------ | ---------------------------- |
| Root cause analysis                        | Engineering Lead             |
| Identify all affected customers and data   | Data Protection Lead         |
| Draft customer and regulator notifications | Data Protection Lead + Legal |
| Implement remediation                      | Engineering Lead             |

### Phase 4 — Notification (as required)

| Action                                    | Owner                 |
| ----------------------------------------- | --------------------- |
| Send customer notifications               | Customer Success Lead |
| File regulator notification (if required) | Data Protection Lead  |
| Update status page                        | Engineering Lead      |
| Brief internal team                       | Incident Commander    |

### Phase 5 — Post-Incident Review (5 business days)

| Action                                                 | Owner                 |
| ------------------------------------------------------ | --------------------- |
| Complete incident report                               | Engineering Lead      |
| Identify preventive measures                           | All                   |
| Implement process improvements                         | Engineering Lead      |
| Update crisis plan if needed                           | Incident Commander    |
| Notify customers of resolution and preventive measures | Customer Success Lead |

---

## 7. Post-Incident Report Template

```
INCIDENT REPORT — [INCIDENT ID]
Date: [YYYY-MM-DD]
Severity: [P1/P2/P3/P4]
Status: CLOSED

SUMMARY:
[2-3 sentence description of what happened]

TIMELINE:
- HH:MM — Event detected
- HH:MM — Incident declared
- HH:MM — Root cause identified
- HH:MM — Incident contained
- HH:MM — Customers notified
- HH:MM — Incident closed

ROOT CAUSE:
[Technical root cause analysis]

DATA AFFECTED:
[Categories of data, number of records, number of customers affected]

RESPONSE:
[What was done to respond to the incident]

REMEDIATION:
[Steps taken to fix the underlying issue]

PREVENTIVE MEASURES:
[Process and technical improvements to prevent recurrence]

CUSTOMER IMPACT:
[Which customers were affected and what they were told]

REGULATORY IMPACT:
[Whether regulators were notified and what was reported]

LESSONS LEARNED:
[What went well, what didn't, what to improve next time]
```

---

## 8. Crisis Contact List

| Contact                 | Role                      | Contact Details               |
| ----------------------- | ------------------------- | ----------------------------- |
| Oraclaire Incident Team | All incidents             | `incident@oraclaire.io`       |
| Oraclaire Privacy Team  | GDPR/PDPA questions       | `privacy@oraclaire.io`        |
| Oraclaire Security      | Security concerns         | `security@oraclaire.io`       |
| Oraclaire Support       | Customer technical issues | `support@oraclaire.io`        |
| AWS Security            | Cloud infrastructure      | `aws-security@amazon.com`     |
| External Legal Counsel  | Legal escalation          | [ON FILE — do not distribute] |

---

_Plan version: 1.0 — Oraclaire Sprint 1 — For Internal Use Only_
