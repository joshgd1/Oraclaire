# Decision D22 — Code Review of Three Production Fixes

**Date:** 2026-05-14
**Type:** DECISION
**Context:** Finding F2 code review (BUG 5, 6, 9)

---

## BUG 5 — SHAP audit trail: CONFIRMED

serve.py now computes SHAP values for all 8 features and logs the full dict to the audit trail. The SHAP dict in predictions.jsonl uses raw feature names from config.FEATURES (tenure_days, mental_fatigue_score, resource_allocation, etc.) — not plain language labels. The employee dashboard uses FEATURE_LABELS separately.

## BUG 6 — PulseRecord range: CONFIRMED

pulse_score le=10.0 is correct.

**Note (not a change):** The weekly pulse uses a 1-5 scale per D13 Mechanism A. le=10.0 accommodates CBI compatibility. The pulse interface in employee.py must enforce 1-5 at the Streamlit slider level — not rely on schema validation.

**Todo added:** "employee.py pulse input — enforce 1-5 range at the Streamlit slider level. Schema allows up to 10 for CBI compatibility — UI must enforce 1-5 for weekly pulse."

## BUG 9 — Pulse drift algorithm: CONFIRMED

Algorithm correctly tracks consecutive-drop streak ending at current score, breaks on first non-qualifying transition. Recovery resets to 0. First-entry edge case (no prior entries) returns consecutive=0 and reassessment_triggered=False.

---

## Pre-commitments (carried forward + D22 addition)

- Full Kaggle dataset re-run
- DPO sign-off on SHAP format
- FP rate re-check on full dataset
- Threshold B senior validation
- Critical tier real probability validation on full dataset
- Pulse input UI validation enforce 1-5 range in employee.py (D22 note)
