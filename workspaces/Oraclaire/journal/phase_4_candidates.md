# Phase 4 — Candidates

# Oraclaire Burnout Risk Scorer

# Sprint 1

Date: 2026-05-14
Dataset: data/processed/train_clean.csv (13 rows)
Status: COMPLETE — D16 RECORDED, AWAITING PHASE 5 SELECTION

## Sweep Configuration

Seed: 42 (all candidates)
Label: Burn Rate binarised at 0.45 (8 elevated / 5 low)
Evaluation: Leave-One-Out Cross-Validation (LOOCV) — 13 rows
Cost model: FP = $15, FN junior = $21,000, FN senior = $4,000 (D4)

## Implementation Citations

| Component           | Library              | Function                                                        | Version                          |
| ------------------- | -------------------- | --------------------------------------------------------------- | -------------------------------- |
| Logistic Regression | sklearn.linear_model | LogisticRegression(solver='lbfgs', C=1.0, max_iter=10000)       | sklearn 1.8.0                    |
| Random Forest       | sklearn.ensemble     | RandomForestClassifier(n_estimators=100, max_depth=5)           | sklearn 1.8.0                    |
| XGBoost             | xgboost              | XGBClassifier(learning_rate=0.1, max_depth=3, n_estimators=100) | xgboost 3.2.0                    |
| SHAP (linear)       | shap                 | LinearExplainer(feature_perturbation='interventional')          | shap 0.51.0                      |
| SHAP (tree)         | shap                 | TreeExplainer()                                                 | shap 0.51.0                      |
| AUC                 | sklearn.metrics      | roc_auc_score                                                   | sklearn 1.8.0                    |
| PR-AUC              | sklearn.metrics      | average_precision_score                                         | sklearn 1.8.0                    |
| Brier               | sklearn.metrics      | brier_score_loss                                                | sklearn 1.8.0                    |
| Pearson r           | scipy.stats          | pearsonr                                                        | scipy (bundled with numpy 2.4.4) |

## Exit Check Results

| #   | Check                   | Result                     | Detail                                                                                                                                 |
| --- | ----------------------- | -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Multicollinearity       | PASS — Designation dropped | Designation vs seniority_tier Pearson r = 0.8865 (p=0.0001). r > 0.8 — Designation removed from all candidate runs. 8 features remain. |
| 2   | NaN in feature matrix   | PASS                       | 0 NaN after preprocessing                                                                                                              |
| 3   | Binarisation at 0.45    | PASS                       | 8 elevated / 5 low                                                                                                                     |
| 4   | Feature count           | PASS                       | 8 features (9 minus dropped Designation)                                                                                               |
| 5   | Seed consistency        | PASS                       | 42 across all candidates                                                                                                               |
| 6   | Naive baseline included | PASS                       | Majority-class predictor included                                                                                                      |

## Feature Set After Multicollinearity Drop

| #   | Feature              | Encoding                                  | Status                          |
| --- | -------------------- | ----------------------------------------- | ------------------------------- |
| 1   | company_type         | Binary (0=Service, 1=Product)             | Active                          |
| 2   | wfh_setup            | Binary (0=No, 1=Yes)                      | Active, flagged Sprint 2 review |
| 3   | resource_allocation  | Numeric (median imputed at 6.5)           | Active                          |
| 4   | mental_fatigue_score | Numeric (median imputed at 4.85)          | Active, proxy leakage flag      |
| 5   | missing_ra           | Binary indicator                          | Active                          |
| 6   | missing_mfs          | Binary indicator                          | Active                          |
| 7   | seniority_tier       | Binary (0=junior, 1=senior)               | Active                          |
| 8   | tenure_days          | Numeric (engineered from Date of Joining) | Active                          |

Designation dropped: Pearson r = 0.8865 with seniority_tier exceeds 0.8 threshold. Per Phase 3 pre-commitment 4: keep seniority_tier, drop Designation.

## MFS SHAP Lines (Phase 3 Pre-Commitment Check)

| Model               | MFS SHAP % | Status                                                 |
| ------------------- | ---------- | ------------------------------------------------------ |
| Logistic Regression | 0.0%       | PASS                                                   |
| Random Forest       | 25.3%      | PASS                                                   |
| XGBoost             | 97.4%      | FLAG — exceeds 40% threshold by 57.4 percentage points |
| Naive Baseline      | N/A        | —                                                      |

XGBoost is the only flagged model. At 97.4% MFS importance, the model is almost entirely a fatigue detector, not a burnout classifier.

## Decision D16 Applied (2026-05-14)

D16a: XGBoost disqualified from Sprint 1 candidate pool. MFS SHAP 97.4% — fatigue detector not burnout detector.
D16b: XGBoost re-enters Sprint 2 candidate pool on expanded feature set. MFS SHAP must be below 40% before Phase 5 entry.
D16c: Logistic Regression perfect separation flagged as 13-row artifact. Remains in candidate pool with flag.
D16d: Phase 1 XGBoost pre-selection revoked. Pre-selections made without data are hypotheses. This one did not survive contact with the dataset.

Full decision: `journal/0015-DECISION-d16-xgboost-disqualification.md`

## Leaderboard (with D16 Status)

| Model               | AUC   | PR-AUC | Brier  | Precision | Recall | F1 (0.45) | MFS%  | Stability | Status                                                                             |
| ------------------- | ----- | ------ | ------ | --------- | ------ | --------- | ----- | --------- | ---------------------------------------------------------------------------------- |
| Random Forest       | 0.975 | 0.986  | 0.0712 | 0.875     | 0.875  | 0.875     | 25.3% | 0.361     | CANDIDATE                                                                          |
| Logistic Regression | 1.000 | 1.000  | 0.0006 | 1.000     | 1.000  | 1.000     | 0.0%  | 0.000     | CANDIDATE (artifact flag: perfect separation on 13 rows, real performance unknown) |
| XGBoost             | 0.700 | 0.843  | 0.1795 | 0.778     | 0.875  | 0.824     | 97.4% | 0.421     | DISQUALIFIED — MFS 97.4%, fatigue detector not burnout detector (D16a)             |
| Naive Baseline      | 0.500 | 0.615  | 0.2367 | 0.615     | 1.000  | 0.762     | 0.0%  | 0.487     | BASELINE                                                                           |

### Leaderboard Notes

Logistic Regression achieves AUC=1.000 on 13 rows — perfect separation, a known artifact on very small datasets. The model puts 100% of SHAP importance on tenure_days. This will not generalise to the full Kaggle dataset. Flag recorded per D16c.

Random Forest shows the most balanced SHAP profile (top 3: tenure_days 28.5%, MFS 25.3%, resource_allocation 24.5%) and the best calibration among genuine candidates (Brier 0.0712). The only candidate that is neither disqualified nor flagged for artifact.

XGBoost has the worst calibration (Brier 0.1795) and highest instability (0.421). Disqualified per D16a — results retained on leaderboard to preserve what the data found.

### Top-3 SHAP per Model

| Rank | Logistic Regression         | Random Forest                | XGBoost                      |
| ---- | --------------------------- | ---------------------------- | ---------------------------- |
| 1    | tenure_days (100.0%)        | tenure_days (28.5%)          | mental_fatigue_score (97.4%) |
| 2    | resource_allocation (0.0%)  | mental_fatigue_score (25.3%) | resource_allocation (2.6%)   |
| 3    | mental_fatigue_score (0.0%) | resource_allocation (24.5%)  | company_type (0.0%)          |

### Full SHAP Importance (% of total)

| Feature              | LR     | RF    | XGB   |
| -------------------- | ------ | ----- | ----- |
| company_type         | 0.0%   | 0.7%  | 0.0%  |
| wfh_setup            | 0.0%   | 3.4%  | 0.0%  |
| resource_allocation  | 0.0%   | 24.5% | 2.6%  |
| mental_fatigue_score | 0.0%   | 25.3% | 97.4% |
| missing_ra           | 0.0%   | 1.9%  | 0.0%  |
| missing_mfs          | 0.0%   | 0.9%  | 0.0%  |
| seniority_tier       | 0.0%   | 14.9% | 0.0%  |
| tenure_days          | 100.0% | 28.5% | 0.0%  |

## Raw Probabilities (all 13 rows, LOOCV)

| Employee    | Burn Rate | Label | LR     | RF     | XGB    |
| ----------- | --------- | ----- | ------ | ------ | ------ |
| EID_001     | 0.45      | 1     | 0.9148 | 0.3100 | 0.2634 |
| EID_002     | 0.72      | 1     | 1.0000 | 0.9000 | 0.8119 |
| EID_003     | 0.30      | 0     | 0.0000 | 0.1500 | 0.5419 |
| EID_004     | 0.85      | 1     | 1.0000 | 1.0000 | 0.8119 |
| EID_005     | 0.38      | 0     | 0.0154 | 0.1900 | 0.3934 |
| EID_006     | 0.91      | 1     | 1.0000 | 0.9900 | 0.8119 |
| fakeEMP_007 | 0.60      | 1     | 1.0000 | 0.8500 | 0.8119 |
| EID_008     | 0.25      | 0     | 0.0000 | 0.0600 | 0.3934 |
| EID_010     | 0.74      | 1     | 1.0000 | 0.9900 | 0.8119 |
| EID_012     | 0.42      | 0     | 0.0000 | 0.5700 | 0.8863 |
| EID_014     | 0.68      | 1     | 1.0000 | 0.8400 | 0.8119 |
| EID_017     | 0.22      | 0     | 0.0000 | 0.0600 | 0.3934 |
| EID_018     | 0.95      | 1     | 1.0000 | 0.9900 | 0.8119 |

### Notable Predictions

- EID_001 (BR=0.45, borderline): LR correctly elevates (0.91). RF places at 0.31 (below 0.45 — misclassified as low). XGBoost places at 0.26 (well below — misclassified).
- EID_003 (BR=0.30, low): XGBoost predicts 0.54 (above 0.45 — false positive).
- EID_012 (BR=0.42, low): XGBoost predicts 0.89 (false positive). RF predicts 0.57 (also FP at 0.45 threshold).

## Cost Comparison Table — CANDIDATES ONLY (per D16)

Thresholds evaluated: [0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
Cost model: FP x $15, FN junior x $21,000, FN senior x $4,000 (D4)
XGBoost excluded per D16a (DISQUALIFIED). Full cost table including XGBoost retained in commit history.

| Model               | Threshold | FP  | FN  | FP cost | FN junior cost | FN senior cost | Total cost |
| ------------------- | --------- | --- | --- | ------- | -------------- | -------------- | ---------- |
| Random Forest       | 0.25      | 1   | 0   | $15     | $0             | $0             | $15        |
| Random Forest       | 0.30      | 1   | 0   | $15     | $0             | $0             | $15        |
| Random Forest       | 0.35      | 1   | 1   | $15     | $21,000        | $0             | $21,015    |
| Random Forest       | 0.40      | 1   | 1   | $15     | $21,000        | $0             | $21,015    |
| Random Forest       | 0.45      | 1   | 1   | $15     | $21,000        | $0             | $21,015    |
| Random Forest       | 0.50      | 1   | 1   | $15     | $21,000        | $0             | $21,015    |
| Logistic Regression | 0.25      | 0   | 0   | $0      | $0             | $0             | $0         |
| Logistic Regression | 0.30      | 0   | 0   | $0      | $0             | $0             | $0         |
| Logistic Regression | 0.35      | 0   | 0   | $0      | $0             | $0             | $0         |
| Logistic Regression | 0.40      | 0   | 0   | $0      | $0             | $0             | $0         |
| Logistic Regression | 0.45      | 0   | 0   | $0      | $0             | $0             | $0         |
| Logistic Regression | 0.50      | 0   | 0   | $0      | $0             | $0             | $0         |
| Naive Baseline      | 0.25      | 5   | 0   | $75     | $0             | $0             | $75        |
| Naive Baseline      | 0.30      | 5   | 0   | $75     | $0             | $0             | $75        |
| Naive Baseline      | 0.35      | 5   | 0   | $75     | $0             | $0             | $75        |
| Naive Baseline      | 0.40      | 5   | 0   | $75     | $0             | $0             | $75        |
| Naive Baseline      | 0.45      | 5   | 0   | $75     | $0             | $0             | $75        |
| Naive Baseline      | 0.50      | 5   | 0   | $75     | $0             | $0             | $75        |

### Cost Table Notes

Logistic Regression achieves $0 total cost across all thresholds — a consequence of perfect separation on 13 rows. This is a small-sample artifact, not a real cost profile (D16c flag).

Random Forest at thresholds 0.25-0.30: $15 (1 FP only, zero FN). At 0.35-0.50: $21,015 (1 FP + 1 FN junior at $21,000).

The FN in Random Forest at 0.35+ is EID_001 (BR=0.45, borderline elevated) — RF predicts 0.31 which is correctly below threshold. The cost jump from $15 to $21,015 between threshold 0.30 and 0.35 is driven entirely by one borderline junior employee.

## Phase 4 Outcome

Date closed: 2026-05-14
Status: COMPLETE — D16 RECORDED

Candidates evaluated: 4 (3 families + naive baseline)
Features used: 8 (Designation dropped per multicollinearity check r=0.8865)
MFS SHAP flags: 1 (XGBoost at 97.4%, disqualified per D16a)

Decisions recorded:

- D16a: XGBoost disqualified — fatigue detector, not burnout detector
- D16b: XGBoost re-enters Sprint 2 on expanded features
- D16c: Logistic Regression perfect separation flagged as artifact
- D16d: Phase 1 XGBoost pre-selection revoked

Honest state: Random Forest recommended by elimination as much as by merit. The real Phase 5 decision happens on the full Kaggle dataset. What we validated here is the pipeline and what the data is telling us.
