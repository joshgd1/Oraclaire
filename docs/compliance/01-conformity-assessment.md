# Oraclaire — EU AI Act Conformity Assessment

**Document type:** Technical conformity assessment
**Regulation:** EU AI Act (Regulation 2024/1689) — high-risk employment AI system
**Assessment date:** 2026-05-16
**Document owner:** Oraclaire Product Team

---

## 1. System Overview

Oraclaire is an organisational wellbeing analytics system that classifies employee burnout risk into four tiers — low, moderate, high, critical — using a machine learning model trained on Copenhagen Burnout Inventory (CBI) assessment data and weekly pulse surveys.

The system is classified as a **high-risk AI system** under EU AI Act Annex III, §4 (Employment, workplace management, and access to self-employment). The system does **not** make automated decisions with legal or similarly significant effects; a human reviewer must approve or override any Critical-tier classification before intervention.

---

## 2. Model Architecture

### 2.1 Model Family

- **Algorithm:** Random Forest Classifier (Sprint 1)
  - Decision rationale: D16 disqualified XGBoost on SHAP dominance grounds; RF selected as the best-performing alternative with acceptable MFS SHAP contribution (<40% of total SHAP importance)
  - Hyperparameters: `n_estimators=100, max_depth=5, random_state=42`

### 2.2 Feature Set

The model accepts 10 features per employee assessment:

| Feature                | Type              | Description                                          |
| ---------------------- | ----------------- | ---------------------------------------------------- |
| `mental_fatigue_score` | Continuous (0–10) | CBI-derived energy/fatigue indicator                 |
| `resource_allocation`  | Continuous (0–10) | CBI-derived workload demand indicator                |
| `tenure_days`          | Integer           | Days since date of joining                           |
| `seniority_tier`       | Binary (0/1)      | Junior (0) / Senior (1) — HRIS-derived               |
| `company_type`         | Binary (0/1)      | Product (1) / Service (0) company                    |
| `wfh_setup`            | Binary (0/1)      | Work-from-home available (1) / not available (0)     |
| `missing_ra`           | Binary (0/1)      | Indicator that Resource Allocation was not provided  |
| `missing_mfs`          | Binary (0/1)      | Indicator that Mental Fatigue Score was not provided |
| `tenure_fatigue`       | Continuous        | Interaction: tenure_days × mental_fatigue_score      |
| `tenure_workload`      | Continuous        | Interaction: tenure_days × resource_allocation       |

Feature engineering rationale: Interaction terms (`tenure_fatigue`, `tenure_workload`) introduced to reduce Mental Fatigue Score SHAP dominance per D24.

### 2.3 Training Data

- **Source:** Kaggle MBI (Maslach Burnout Inventory) dataset
- **Label:** Burn Rate (CBI composite), binarised at 0.45 threshold
- **Preprocessing:** Median imputation for Resource Allocation and Mental Fatigue Score; missing indicators added before imputation
- **Split:** Stratified 80/20 train/test

### 2.4 Model Versioning

Each model artifact is serialised with a version tag (`model_version` field). Every `RiskScore` record references the `model_version` used at time of scoring. Version promotion from staging to production requires a compatibility check against the current feature schema.

---

## 3. Scoring Process

### 3.1 End-to-End Pipeline

```
Assessment response submitted
         ↓
  Exclusion filter  ← Employee model: consent_status, exclusion_status
         ↓
Feature extraction  ← CBI (19 items → 10 features) or Pulse (1 item)
         ↓
Model inference  ← RandomForest.predict_proba → raw probability
         ↓
Two-threshold calibration
  • General population (seniority_tier=0): THRESHOLD_A = 0.35
  • Senior tier (seniority_tier=1): THRESHOLD_B = 0.30
         ↓
Risk tier classification
  • low:      [0.00, 0.20)
  • moderate: [0.20, 0.30)
  • high:     [0.30, 0.90)
  • critical: [0.90, 1.00]
         ↓
SHAP decomposition  ← TreeExplainer, top-5 features returned
         ↓
RiskScore record written  ← employee_id, cycle_id, numeric_score,
                            risk_tier, shap_values, model_version, scored_at
         ↓
[If Critical tier] Human review gate activated
         ↓
[24h employee-first gate] Employee can view own score
         ↓
[Post gate] HR/Manager aggregates visible
```

### 3.2 Two-Threshold Architecture

Asymmetric thresholds reflect the differential false-negative cost per D14:

| Threshold | Population | FN Target | FP Ceiling | FN Ceiling |
| --------- | ---------- | --------- | ---------- | ---------- |
| A (0.35)  | General    | 15%       | 15%        | —          |
| B (0.30)  | Senior     | 10%       | 20%        | —          |

Senior-tier FN is more costly (higher probability of missed severe burnout in senior roles). FP is more tolerable in the senior tier (higher false-alarm burden is acceptable given seniority).

### 3.3 Calibration Floor

If model Brier score exceeds 0.15, Platt scaling is applied before threshold selection to recalibrate probabilities.

---

## 4. SHAP Explainability

### 4.1 Implementation

SHAP values are generated using `shap.TreeExplainer` (TreeSHAP algorithm, O(TL2) per prediction) against the Random Forest model. Top-5 features by absolute impact are returned in the RiskScore record.

### 4.2 MFS Dominance Gate

Before each model is promoted to production, SHAP analysis is performed on the test set. If Mental Fatigue Score accounts for ≥40% of mean absolute SHAP importance, the model is rejected (D16 gate). Sprint 1 RF model passes this gate.

### 4.3 Right-to-Explanation (Article 13)

Employees can request a human-readable explanation via `GET /api/employee/me/explanation`. The endpoint returns:

- A plain-language summary sentence
- A ranked list of top contributing factors with directional labels ("increases risk" / "decreases risk") and percentage contributions
- Audit log entry on every invocation

---

## 5. Human Oversight

### 5.1 Critical-Tier Review Gate

Every Critical-tier classification is placed in a `pending_review` state. No intervention workflow is triggered for that employee until an HR reviewer:

1. Reviews the SHAP decomposition, employee trajectory, and scoring context
2. **Approves** the classification (releases the intervention gate), or
3. **Overrides** the tier with a written reason (changes the stored risk_tier)

Override decisions are logged in the AuditLog with reviewer identity, original tier, new tier, and reason text.

### 5.2 Review Timeout

If no review action is taken within 48 hours of scoring, an escalation signal is generated. The 48-hour window is a deployment parameter configurable per organisation.

---

## 6. Audit Trail

All scoring events are written to structured log files and the `AuditLog` database table.

### 6.1 Prediction Log

Each model prediction writes a JSON line to `data/audit/predictions.jsonl`:

```json
{
  "timestamp": "2026-05-16T10:00:00Z",
  "correlation_id": "uuid-v4",
  "employee_id": "EID_001",
  "burnout_probability": 0.72,
  "risk_tier": "critical",
  "threshold_used": "A (general)",
  "seniority_tier": "junior",
  "top_shap_feature": "mental_fatigue_score",
  "top_shap_value": 0.31,
  "shap_values": {"mental_fatigue_score": 0.31, ...},
  "model_version": "sprint-1-rf"
}
```

### 6.2 AuditLog Table

The `AuditLog` table records all data access and modification events:

| Field                | Type       | Description                                              |
| -------------------- | ---------- | -------------------------------------------------------- |
| `id`                 | Integer PK | Auto-increment                                           |
| `actor_id`           | String     | User/system component performing the action              |
| `action`             | String     | e.g. `review.approved`, `employee.explanation_requested` |
| `target_entity_type` | String     | e.g. `human_review`, `risk_score`, `employee`            |
| `target_entity_id`   | String     | ID of the affected entity                                |
| `timestamp`          | DateTime   | UTC timestamp of the action                              |
| `metadata_json`      | JSON       | Additional context (cycle_id, old/new tier, etc.)        |

All API endpoints that read or modify employee or score data write an AuditLog entry.

### 6.3 Pulse Log

Weekly pulse responses are written to `data/audit/pulse.jsonl` with employee_id, cycle_id, response value, and timestamp.

---

## 7. Data Governance

### 7.1 Retention

Individual-level assessment responses and risk scores are retained for a configurable period (default: 12 months) per organisation, then hard-deleted. Team aggregates are retained indefinitely.

### 7.2 Exclusion

Employees may withdraw consent at any time. Withdrawn employees are excluded from scoring and aggregate computation within 48 hours of withdrawal request.

### 7.3 No HRIS / Performance Management Export

The API blocks any response format or endpoint that would facilitate export of individual scores to HRIS or performance management systems. Aggregate team data is available only when the team has ≥5 contributing members.

---

## 8. Participation Mechanisms

Four mechanisms drive the 20% → 40% participation target:

1. **Weekly pulse:** Single CBI item, 10-second response, aggregated at team level only
2. **Monthly CBI:** Full 19-item Copenhagen Burnout Inventory, individual scores
3. **24-hour employee-first gate:** HR and manager aggregate visibility delayed 24h after cycle close to give employees first access to their own scores
4. **Content library:** Curated resources matched to top SHAP factors, surfaced to employees post-assessment

---

## 9. Bias Audit

Before each customer deployment, an automated disparate impact analysis is run comparing Critical+High tier rates across demographic slices:

- Seniority tier (junior / senior)
- Company type (Product / Service)
- WFH setup (available / not available)

A slice is flagged if its Critical+High rate differs from the overall population rate by more than 10 percentage points. Flagged slices are surfaced to the HR administrator with detail per group.

---

## 10. Future Model Updates

Model retraining is triggered by:

- Participation rate falling below the participation target for two consecutive cycles
- Threshold drift exceeding ±0.05 from the current threshold
- Annual scheduled retraining

New model versions are stored with a version tag and are not automatically promoted to production. Staging-to-production promotion requires a compatibility check against the current feature schema.
