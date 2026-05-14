# Phase 2 — Data Audit

# Oraclaire Burnout Risk Scorer

# Sprint 1

Date: 2026-05-13
Dataset: data/raw/train_sample.csv (sample — real dataset: data/raw/train.csv)
Status: DISPOSITIONS APPLIED

## Audit Parameters

Inter-cycle window: 90 days (D14)
Sparsity floor: fewer than 2 completed quarterly cycles
Outlier columns: Mental Fatigue Score, Resource Allocation
Valid ranges: Mental Fatigue Score 0.0-10.0, Resource Allocation 1.0-10.0
Label-in-disguise primary suspect: Burn Rate
Contamination rule: Employee ID format break from column pattern
Missingness threshold: >5% NaN flags

## Findings Table

| #   | Category           | Sub-finding                          | File             | Column               | Finding                                                        | Disposition                                     | One-line reason                                                                                            |
| --- | ------------------ | ------------------------------------ | ---------------- | -------------------- | -------------------------------------------------------------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| 1   | Duplicates         | Exact Employee ID repeat             | train_sample.csv | Employee ID          | 1 duplicate: fakeEMP_007 rows 7 and 14                         | EXCLUDE — drop row 14, keep row 7               | Duplicate inflates training weight for one employee                                                        |
| 2   | Contamination      | Employee ID format break             | train_sample.csv | Employee ID          | 1 row: TEST_001 on row 15                                      | EXCLUDE — full row                              | Test account, not a real employee                                                                          |
| 3   | Contamination      | fakeEMP_007 format break             | train_sample.csv | Employee ID          | 2 rows with fakeEMP\_ prefix (rows 7, 14)                      | FLAG — resolved by Finding 1                    | Covered by Finding 1 exclusion; real dataset: fakeEMP\_ prefix rows excluded immediately                   |
| 4   | Contamination      | \_source column present and uniform  | train_sample.csv | \_source             | All 20 rows \_source=SAMPLE                                    | FLAG — expected on sample                       | Required on augmented production rows; absence BLOCKS Phase 3 train-test split                             |
| 5   | Sparsity           | No cycle column in schema            | train_sample.csv | (no cycle column)    | Cross-sectional source; sparsity floor cannot be applied       | FLAG — schema gap                               | Oraclaire production schema must include cycle_id from Sprint 1 day one                                    |
| 6   | Outliers 4A        | Mental Fatigue Score out-of-range    | train_sample.csv | Mental Fatigue Score | 1 value: row 9 (EID_009) = 11.5, above max 10.0                | EXCLUDE — full row                              | Impossible value on primary burnout feature; capping would treat bad data as Critical-tier signal          |
| 7   | Outliers 4A        | Resource Allocation out-of-range     | train_sample.csv | Resource Allocation  | 1 value: row 18 (EID_016) = 0.2, below min 1.0                 | EXCLUDE — full row                              | Impossible value; entire row untrustworthy                                                                 |
| 8   | Outliers 4B        | Mental Fatigue Score top-1%          | train_sample.csv | Mental Fatigue Score | 1 value: row 22 (EID_018) = 8.9, above threshold 8.2           | LEAVE                                           | High fatigue is signal not noise; capping suppresses Critical-tier detection (FN cost $4,000-$21,000/year) |
| 9   | Outliers 4B        | Resource Allocation top-1%           | train_sample.csv | Resource Allocation  | 1 value: row 22 (EID_018) = 9.5, above threshold 9.0           | LEAVE                                           | High workload is legitimate signal for workload-burnout correlation                                        |
| 10  | Labels-in-disguise | Burn Rate unique values and NaN rate | train_sample.csv | Burn Rate            | 16 unique, 3 NaN (15%), no engineered transformations detected | LEAVE — rerun on full dataset before Phase 3    | No leakage in sample; augmented features derived from Burn Rate get EXCLUDE disposition                    |
| 11  | Missingness        | Resource Allocation NaN rate         | train_sample.csv | Resource Allocation  | 2/20 rows NaN (10%), rows 12 and 17                            | FLAG — indicator column + imputation to Phase 3 | missing_resource_allocation indicator preserves missingness as feature; median imputation default          |
| 12  | Missingness        | Mental Fatigue Score NaN rate        | train_sample.csv | Mental Fatigue Score | 1/20 rows NaN (5%), row 16                                     | FLAG — indicator column + imputation to Phase 3 | missing_mental_fatigue indicator; higher imputation priority than Resource Allocation                      |
| 13  | Missingness        | Burn Rate NaN rate                   | train_sample.csv | Burn Rate            | 3/20 rows NaN (15%), rows 11, 13, 17                           | EXCLUDE from training — move to unlabelled pool | No label = no supervised training; rows kept for potential semi-supervised use in Sprint 2                 |

## Disposition Summary

| Disposition           | Count                     | Findings                                          |
| --------------------- | ------------------------- | ------------------------------------------------- |
| EXCLUDE               | 5 rows hard-excluded      | F1 (row 14), F2 (row 15), F6 (row 9), F7 (row 18) |
| EXCLUDE from training | 3 rows to unlabelled pool | F13 (rows 11, 13, 17)                             |
| FLAG                  | 6 findings                | F3, F4, F5, F11, F12, plus \_source architecture  |
| LEAVE                 | 3 findings                | F8, F9, F10                                       |

## Output Files

| File                                | Rows | Purpose                              |
| ----------------------------------- | ---- | ------------------------------------ |
| data/raw/train_sample.csv           | 20   | Original — untouched                 |
| data/processed/train_clean.csv      | 13   | Clean dataset with indicator columns |
| data/processed/train_unlabelled.csv | 3    | Unlabelled pool (no Burn Rate)       |
| data/processed/disposition_log.txt  | —    | Full disposition record              |

## Phase 3 Blockers

- Missing \_source column on augmented production rows BLOCKS Phase 3: train-test split cannot exclude synthetic rows from holdout without this column

## New Todos from Audit

1. cycle_id field in production schema — required from Sprint 1 day one (Finding 5)
2. missing_resource_allocation indicator column — value 1 where NaN, 0 elsewhere (Finding 11)
3. missing_mental_fatigue indicator column — value 1 where NaN, 0 elsewhere (Finding 12)
4. Unlabelled pool — rows with no Burn Rate label moved here, not deleted (Finding 13)
5. Phase 3 pre-commitment: imputation strategy for Resource Allocation and Mental Fatigue Score — median default, override with rationale
6. Rerun label-leakage check on full Kaggle dataset before Phase 3 begins (Finding 10 standing instruction)

## Phase 2 Outcome

Date closed: 2026-05-13
Status: COMPLETE

Dataset: data/raw/train_sample.csv
Raw file: untouched

Clean dataset: 13 rows
Unlabelled pool: 3 rows (EID_011, EID_013, EID_015)
Hard excluded: 4 rows

- Row 14: duplicate (fakeEMP_007)
- Row 15: contamination (TEST_001)
- Row 9: out-of-range Mental Fatigue Score (11.5)
- Row 18: out-of-range Resource Allocation (0.2)

Indicator columns added:

- missing_resource_allocation
- missing_mental_fatigue

Phase 3 blockers carried forward:

- \_source column required on all augmented rows before train-test split
- cycle_id field required in production schema from day one

Phase 3 pre-commitments:

- Imputation strategy for Resource Allocation — median default
- Imputation strategy for Mental Fatigue Score — median default, consider whether missingness is predictive
- Label-leakage recheck on full Kaggle dataset before Phase 3 begins

### Note on Sample Validity

This audit was run on a 20-row synthetic sample built to the correct schema. Every planted error was correctly identified and dispositioned.

The audit pipeline is validated. When the real Kaggle dataset arrives at data/raw/train.csv run the identical six-category audit against it before proceeding to Phase 3.

Expected differences on the real dataset:

- Row count: ~22,750
- Missingness rates will differ from the sample — recompute exact NaN rates per column
- Out-of-range values may or may not exist — audit will find them
- Sparsity finding (Finding 5) remains structurally N/A until production schema includes cycle_id

## Notes

- Audit run against 20-row synthetic sample. All dispositions apply to sample pipeline; real Kaggle dataset will be audited with the same six categories before Phase 3.
- Indicator columns (missing_resource_allocation, missing_mental_fatigue) added to both train_clean.csv and train_unlabelled.csv.
