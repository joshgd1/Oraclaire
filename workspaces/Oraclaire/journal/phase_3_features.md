# Phase 3 — Feature Framing

# Oraclaire Burnout Risk Scorer

# Sprint 1

Date: 2026-05-13
Dataset: data/processed/train_clean.csv (13 rows)
Status: COMPLETE

## Proxy-Drop Method

Model: logistic regression (sklearn, lbfgs, max_iter=5000)
Label: Burn Rate >= 0.5 (binary: 6 Low / 7 Elevated)
Threshold: 0.5
Imputation: median (RA median=7.0, MFS median=5.5)
Baseline features (all models): Company Type, WFH Setup Available, Resource Allocation (imputed), Mental Fatigue Score (imputed), missing_resource_allocation, missing_mental_fatigue, tenure_days
Test: add/remove candidate feature from baseline, compare predicted class per row
Sample size: 13 rows
Caveat: 13-row sample limits generalisability. Proxy-drop results are sample-specific and must be re-run on the full Kaggle dataset (~22,750 rows) before production decisions.

## TABLE 1 — Feature Classification

| Feature                     | Source citation                                          | Axis 1: Available at prediction time?                                                                                                                           | Axis 2: Leakage?                                                                                  | Axis 3: Sensitive?                                                                               | Axis 4: Raw/Engineered?                                                              | Decision                                                                                                                                                                                                                                                                                                       |
| --------------------------- | -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Employee ID                 | column "Employee ID" in train_sample.csv                 | Yes                                                                                                                                                             | No leakage — unique identifier                                                                    | No                                                                                               | Raw                                                                                  | OUT — identifier, no predictive signal; model would memorise individuals rather than learn burnout patterns                                                                                                                                                                                                    |
| Date of Joining             | column "Date of Joining" in train_sample.csv             | Yes                                                                                                                                                             | No leakage                                                                                        | PDPA / GDPR Article 21 — tenure proxies for age cohort                                           | Raw — replaced by engineered tenure_days                                             | OUT as raw column — replaced by tenure_days (assessment_date minus Date of Joining)                                                                                                                                                                                                                            |
| Gender                      | column "Gender" in train_sample.csv                      | Yes                                                                                                                                                             | No leakage                                                                                        | YES — protected characteristic under ADA, GDPR Article 9, Singapore Employment Act, PDPA         | Raw                                                                                  | OUT — Axis 3 failure. 0% proxy-drop reassignment on sample but 13 rows is pipeline validation not statistical evidence. Including Gender creates disparate impact exposure regardless of reassignment rate. Fairness audit on outputs using Gender as audit variable (not feature) in Phase 5 per D11 Nuance 4 |
| Company Type                | column "Company Type" in train_sample.csv                | Yes                                                                                                                                                             | No leakage                                                                                        | No                                                                                               | Raw — one-hot encode at Phase 4                                                      | IN — organisational context feature. Service vs Product differentiates burnout risk context through workload structures and deadline cultures                                                                                                                                                                  |
| WFH Setup Available         | column "WFH Setup Available" in train_sample.csv         | Yes                                                                                                                                                             | No leakage                                                                                        | Low — not a protected characteristic                                                             | Raw — one-hot encode at Phase 4                                                      | IN with flag — legitimate workload context feature (flexible working is a burnout protective factor). Flagged for Sprint 2 review: post-2023 WFH signal may degrade. If low feature importance on real data, drop at Sprint 2                                                                                  |
| Designation                 | column "Designation" in train_sample.csv                 | Yes                                                                                                                                                             | No label leakage; possible proxy leakage — legitimate predictive signal                           | YES — seniority proxy, correlates with age/tenure/compensation. GDPR Article 21, PDPA            | Raw — categorical in sample; ordinal 0-5 in full Kaggle dataset                      | IN with constraint — workload context indicator (decision authority and autonomy). seniority_tier (D15) serves threshold architecture; Designation serves feature set. If multicollinearity with seniority_tier above 0.8 in Phase 4 — drop Designation, keep seniority_tier                                   |
| Resource Allocation         | column "Resource Allocation" in train_sample.csv         | Yes                                                                                                                                                             | No label leakage; possible proxy leakage — legitimate predictive signal (workload drives burnout) | No                                                                                               | Raw — median imputation per Phase 2 Finding 11                                       | IN — primary workload signal. One of six Maslach worklife areas (workload dimension). 10% NaN rate in sample; median imputation committed                                                                                                                                                                      |
| Mental Fatigue Score        | column "Mental Fatigue Score" in train_sample.csv        | Yes — confirmed by D13 pulse architecture: MFS derived from inter-cycle weekly pulse data preceding quarterly CBI. Production schema enforces temporal ordering | PROXY LEAKAGE — not derived from Burn Rate but the single strongest predictor in this dataset     | YES — PDPA-sensitive (psychological state), GDPR Article 9 (health data), ADA (disability proxy) | Raw — median imputation per Phase 2 Finding 12                                       | IN with proxy leakage flag retained — flag is a Phase 4 instruction: if MFS accounts for more than 40% of total SHAP importance the model is detecting fatigue not burnout. Flag and review before Phase 5. Consider fatigue-change feature instead of fatigue-level feature if threshold exceeded             |
| Burn Rate                   | column "Burn Rate" in train_sample.csv                   | N/A — label                                                                                                                                                     | LABEL LEAKAGE                                                                                     | PDPA-sensitive                                                                                   | Raw                                                                                  | OUT — label, never a feature. Training target only. Confirmed Phase 2 Finding 10                                                                                                                                                                                                                               |
| \_source                    | column "\_source" in train_sample.csv; Phase 2 Finding 4 | Yes                                                                                                                                                             | No leakage                                                                                        | No                                                                                               | Raw                                                                                  | OUT — metadata for train/test split discipline (Finding 4), not a predictive feature                                                                                                                                                                                                                           |
| missing_resource_allocation | Phase 2 Finding 11                                       | Yes                                                                                                                                                             | Possible proxy leakage — weak signal                                                              | No                                                                                               | Engineered — binary (1 where Resource Allocation NaN)                                | IN — missingness may correlate with disengagement; preserves signal                                                                                                                                                                                                                                            |
| missing_mental_fatigue      | Phase 2 Finding 12                                       | Yes                                                                                                                                                             | Possible proxy leakage — weak signal                                                              | Indirect PDPA sensitivity                                                                        | Engineered — binary (1 where Mental Fatigue Score NaN)                               | IN — skipping the fatigue section specifically may indicate avoidance of an uncomfortable answer; that avoidance is itself a potential burnout signal                                                                                                                                                          |
| seniority_tier              | D15-1                                                    | Yes — HRIS-derived or self-reported per D15-1                                                                                                                   | No leakage                                                                                        | YES — PDPA / GDPR Article 21 (proxies for age). Interacts with D4 FN cost tier split             | Engineered — junior/senior from Designation (sample) or HRIS grade/band (production) | IN — drives two-threshold architecture from D11 Nuance 3. Must be in feature set for Phase 5 threshold selection. Binary feature; one-hot encode at Phase 4                                                                                                                                                    |
| tenure_days                 | Engineered from Date of Joining, train_sample.csv        | Yes — assessment_date minus Date of Joining                                                                                                                     | No leakage                                                                                        | PDPA / GDPR Article 21 — tenure proxies for age                                                  | Engineered — assessment_date minus Date of Joining. Source: Date of Joining column   | IN pending engineering — early-career and long-tenure employees show different burnout patterns. If engineering fails raw Date of Joining is excluded; no fallback                                                                                                                                             |

## TABLE 2 — Proxy-Drop Results

| Feature     | Reassignment rate A->B | Rows changed | Decision                                                                                                                                              |
| ----------- | ---------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Gender      | 0.0% (0/13)            | 0            | OUT — Axis 3 failure (protected characteristic) drives decision, not reassignment rate. 0% on 13 rows is pipeline validation not statistical evidence |
| Designation | 0.0% (0/13)            | 0            | IN with constraint — 0% on 13 rows is pipeline validation. Kept as workload context indicator with multicollinearity check in Phase 4                 |

### Proxy-Drop Detail

Both tests produced zero reassignments. On this 13-row sample with logistic regression and a 0.5 threshold, the remaining features (Resource Allocation, Mental Fatigue Score, tenure_days) fully determine the predicted risk tier. Removing Gender or Designation individually changes no row's classification.

This result is sample-specific. The full Kaggle dataset (~22,750 rows) may show non-zero reassignment rates. Re-run proxy-drop on the full dataset before final disposition.

## Confirmed Feature Set — Sprint 1

IN (9 features):

| #   | Feature                     | Encoding                    | Notes                                                                                                                                              |
| --- | --------------------------- | --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Company Type                | One-hot                     | Organisational context                                                                                                                             |
| 2   | WFH Setup Available         | One-hot                     | Flagged for Sprint 2 review                                                                                                                        |
| 3   | Designation                 | Ordinal (0-5)               | ~~Dropped — multicollinearity confirmed: r = 0.8865 > 0.80 threshold per Phase 3 pre-commitment 3. Confirmed in train.py Phase 6 implementation.~~ |
| 4   | Resource Allocation         | Numeric (median imputation) | Primary workload signal                                                                                                                            |
| 5   | Mental Fatigue Score        | Numeric (median imputation) | Proxy leakage flag retained; 40% SHAP threshold check in Phase 4                                                                                   |
| 6   | missing_resource_allocation | Binary                      | Missingness indicator                                                                                                                              |
| 7   | missing_mental_fatigue      | Binary                      | Missingness indicator                                                                                                                              |
| 8   | seniority_tier              | Binary (one-hot)            | Drives threshold architecture                                                                                                                      |
| 9   | tenure_days                 | Numeric (engineered)        | Pending Phase 4 engineering step                                                                                                                   |

OUT (4 columns):

| Column          | Reason                                    |
| --------------- | ----------------------------------------- |
| Employee ID     | Identifier, no predictive signal          |
| Date of Joining | Raw — replaced by tenure_days             |
| Gender          | Axis 3 failure — protected characteristic |
| Burn Rate       | Label — never a feature                   |

## Phase 4 Pre-Commitments

1. tenure_days engineering — assessment_date minus Date of Joining. If engineering fails: raw Date of Joining excluded with no fallback.
2. One-hot encoding — Company Type, WFH Setup Available, seniority_tier
3. Median imputation — Resource Allocation NaN rows
4. Multicollinearity check — Designation vs seniority_tier. If correlation above 0.8: drop Designation, keep seniority_tier.
5. Mental Fatigue Score SHAP importance threshold check — if above 40% of total importance: flag and review before Phase 5. Consider fatigue-change feature instead of fatigue-level feature.
6. Gender fairness audit — Gender used as audit variable in Phase 5, not as model feature. Per D11 Nuance 4.

## New Todos from Phase 3

1. tenure_days added to confirmed feature set pending Phase 4 engineering
2. WFH feature validity review flagged for Sprint 2
3. Designation multicollinearity check added to Phase 4 pipeline
4. Mental Fatigue Score SHAP threshold check added to Phase 4 exit criteria
5. Gender fairness audit added to Phase 5 requirements

## Phase 3 Outcome

Date closed: 2026-05-13
Status: COMPLETE

Features classified: 13 (including 2 indicator columns from Phase 2 and 1 engineered from D15)
Proxy-drop candidates tested: 2 (Gender, Designation)
Features IN: 9
Features OUT: 4
Phase 4 pre-commitments: 6
Phase 4 blockers: none
Phase 5 new requirements: 1 (Gender fairness audit)

Key decisions:

- Mental Fatigue Score Axis 1 resolved: available at prediction time per D13 pulse architecture
- Gender excluded on Axis 3 grounds despite 0% proxy-drop reassignment
- Designation kept with multicollinearity constraint
- MFS proxy leakage flag retained as Phase 4 SHAP threshold check (40%)
- tenure_days replaces raw Date of Joining
