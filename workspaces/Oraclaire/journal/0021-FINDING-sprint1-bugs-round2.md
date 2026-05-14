# Finding F2 — Sprint 1 Bugs Round 2

**Date:** 2026-05-14
**Type:** FINDING
**Session:** Resume after /clear

Six bugs found and fixed during Sprint 1 integration test verification. Four are production code fixes; two are test infrastructure.

Round 1 bugs (F1) were documented in journal/0020. This entry covers the six discovered during `/clear` resume session.

---

## BUG 4: autouse syntax error

**File:** `tests/test_sprint1_criteria.py:66`
**Severity:** Test infrastructure — would have blocked all testing

**What it caused:** `@pytest.fixture(autouse)` — bare `autouse` treated as a variable name, not a keyword argument. `NameError: name 'autouse' is not defined` at collection time. Entire test file uncollectable.

**Fix:** Corrected to `@pytest.fixture(autouse=True)`.

**Origin:** Previous session left the decorator incomplete.

---

## BUG 5: SHAP audit trail incomplete in serve.py

**File:** `src/model/serve.py` — `score_employee()` function
**Severity:** HIGH — DPO audit trail integrity

**What it caused:** The `score_employee` function built `shap_values_dict` from only the top-3 labeled SHAP features returned by `_shap_explain()`. Features with `FEATURE_LABELS[f] = None` (missing_ra, missing_mfs) and features outside the top-3 were excluded from every prediction record written to `predictions.jsonl`.

**DPO impact:** The audit trail the DPO must sign off on was incomplete. Every prediction logged before this fix has an incomplete SHAP record — only 3 of 8 features.

**Fix:** `serve.py` now computes full SHAP decomposition (all 8 features) separately from the display-oriented `_shap_explain()`. The audit trail receives all 8 features; the employee-facing SHAP waterfall still shows top-3 labeled only.

**Before:**

```python
shap_values_dict = {
    s["feature"]: s["impact_value"] for s in shap_decomposition
}
```

**After:** Full `shap.TreeExplainer` computation with all features, stored in `full_shap_dict`.

---

## BUG 6: PulseRecord score range wrong

**File:** `src/audit/schema.py` — `PulseRecord.pulse_score`
**Severity:** HIGH — would have rejected all real pulse entries

**What it caused:** `pulse_score: float = Field(..., ge=0.0, le=1.0)` constrained the field to [0, 1]. The weekly pulse interface uses a broader scale (CBI single-item, typically 0-6). Any real pulse entry with score > 1.0 would raise `ValidationError`.

**Config mismatch:** `PULSE_DRIFT_THRESHOLD = 2` (points decline per week) — a 2-point threshold is impossible if scores are constrained to [0, 1].

**Fix:** Widened to `le=10.0` to accommodate CBI-scale scores.

**Before:** `pulse_score: float = Field(..., ge=0.0, le=1.0)`
**After:** `pulse_score: float = Field(..., ge=0.0, le=10.0)`

---

## BUG 7: ORT test used wrong constant

**File:** `tests/test_sprint1_criteria.py` — `test_ort_fires_above_20_percent`
**Severity:** Test only — production ORT logic unaffected

**What it caused:** Test checked ORT trigger condition against `PULSE_DRIFT_CONSECUTIVE_WEEKS = 3` instead of `ORT_TRIGGER_WEEKS = 2`. The ORT fires on 2 consecutive weeks exceeding ceiling (D15-2), not the pulse drift's 3 consecutive weeks (D13 Mechanism A). These are different mechanisms with different thresholds.

**Fix:** Imported `ORT_TRIGGER_WEEKS` and replaced all references in the ORT test.

**Note:** Production ORT logic in `hr_aggregate.py` was already correct — only the test had the wrong constant.

---

## BUG 8: Critical tier test needed mocked model

**File:** `tests/test_sprint1_criteria.py` — `test_critical_held_in_queue`
**Severity:** Test infrastructure — production scoring unaffected

**What it caused:** The 12-row dataset with `max_depth=5` produces a maximum probability of ~0.74 — below the Critical threshold of 0.75 (D20). The test's feature values (9.0 workload, 9.0 fatigue, 2000 days tenure) produced 0.74 (High), not Critical.

**Fix:** Mocked `load_model` and `shap.TreeExplainer` to force a 0.90 probability. The test verifies the reviewer queue logic (review_status='pending', reviewer_id=None), not the model's ability to produce Critical scores.

**Caveat:** Criterion 4 is tested against a mocked probability, not a real one. Full dataset re-run will produce real Critical cases for end-to-end validation.

---

## BUG 9: Pulse drift algorithm incorrect

**File:** `src/audit/logger.py` — `log_pulse()` drift detection block
**Severity:** HIGH — early warning mechanism was producing wrong flags

**What it caused:** The drift detection algorithm counted drops within a sliding window of the most recent N entries, but did not properly track a consecutive streak ending at the current score. It could:

1. **Miss triggers:** When the N most recent entries contained non-consecutive drops, the algorithm checked `all_dropping AND drop_count >= threshold`, but `all_dropping` was set False by any non-qualifying transition in the window — even if the most recent transitions were all qualifying.

2. **Fire incorrectly:** When `all_dropping` happened to be True for a window that didn't represent consecutive drops from the current point.

**Fix:** Rewrote to track consecutive-drop streak ending at the current score:

- Build all-scores list (current first, then prior newest-first)
- Walk backwards from current, incrementing counter on each qualifying drop
- Break on first non-qualifying transition
- Reassessment triggers when counter >= PULSE_DRIFT_CONSECUTIVE_WEEKS

**Before:** Window-based counting with `all_dropping` flag
**After:** Streak-based counting from current score backwards

---

## Summary

| Bug   | File                | Severity   | Production fix?        |
| ----- | ------------------- | ---------- | ---------------------- |
| BUG 4 | tests/              | Test infra | No — test syntax       |
| BUG 5 | src/model/serve.py  | HIGH       | Yes — audit trail      |
| BUG 6 | src/audit/schema.py | HIGH       | Yes — pulse validation |
| BUG 7 | tests/              | Test only  | No — test constant     |
| BUG 8 | tests/              | Test infra | No — test mock         |
| BUG 9 | src/audit/logger.py | HIGH       | Yes — drift algorithm  |

Three production fixes (BUG 5, 6, 9). Three test infrastructure fixes (BUG 4, 7, 8).
