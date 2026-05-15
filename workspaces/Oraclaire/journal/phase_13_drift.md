# Phase 13 — Drift Monitoring

Date: 2026-05-15
Status: Rules drafted. Threshold values are [FOUNDER SETS] throughout. Waiting for founder threshold values per rule.

---

## 1. Drift Reference Status

| Component                                 | Reference registered | Gap                                                                                                                                                                                                                            | Unblocking action                                                                                  |
| ----------------------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| Component 1 — Burnout risk scorer         | NO                   | No formal baseline distribution file exists. `data/processed/train_clean.csv` is a 12-row sample used for training — it has NOT been snapshotted as a drift reference distribution with per-feature bin counts and statistics. | Create baseline reference file from full Kaggle dataset when available. Sprint 2 build item.       |
| Component 2 — Weekly pulse drift detector | NO                   | Sprint 1 pilot has not completed a full quarterly cycle (90 days). `data/audit/pulse.jsonl` does not exist — no pulse records have been written.                                                                               | Reference registration is a Sprint 2 activation — requires one full quarterly cycle of pilot data. |
| Component 3 — ORT detector                | NO                   | Same gap as Component 2. `compute_ort_status()` exists but has never been called against real pilot data. No ORT trigger history exists.                                                                                       | Reference registration is a Sprint 2 activation — requires one full quarterly cycle of pilot data. |

**Component 1 detail:** The training data at `data/processed/train_clean.csv` contains 12 rows with 10 features in `config.FEATURES`. This is a sample, not a baseline distribution artifact. A drift reference requires a persisted snapshot of per-feature bin counts (for categorical features) or distribution statistics (mean, std, percentiles for continuous features) that the PSI computation can compare against. The full Kaggle dataset (~22,000 rows) would serve as the reference once available.

**Component 2 detail:** Sprint 1 is pre-pilot. The pulse audit trail (`data/audit/pulse.jsonl` at `config.PULSE_LOG`) will be created on first write via `src/audit/logger.py::_append()`. False trigger rate requires at least one complete quarterly CBI cycle with pulse entries that have `reassessment_triggered = True` AND subsequent CBI ground truth to determine if the reassessment was a false trigger. Neither exists.

**Component 3 detail:** `src/views/hr_data.py::compute_ort_status()` is a pure function that accepts a list of team dicts and returns `{alerts, ok_teams, excluded_teams}`. It does NOT write to any audit trail. ORT firing rate requires this function to be called per cycle AND the result logged. Neither has happened.

---

## 2. Observed Variance

### Component 1 — Burnout risk scorer (PSI)

**PSI computation function: NOT FOUND in `src/`.**

Searched: `src/model/`, `src/views/`, `src/audit/`, `src/config.py`. No function named `psi`, `population_stability_index`, `compute_psi`, or any equivalent exists.

**Variance table against 12-row sample:**

Cannot compute meaningful PSI. The 12-row `train_clean.csv` is both the training data and the only available "current" distribution. PSI of a distribution against itself produces zero variance — this is a sample artifact, not a real drift measurement.

| Feature         | PSI                         | 50th pct variance     | 95th pct variance     | 99th pct variance     |
| --------------- | --------------------------- | --------------------- | --------------------- | --------------------- |
| All 10 features | 0.000 (sample-against-self) | N/A — sample artifact | N/A — sample artifact | N/A — sample artifact |

**PSI computation requires:**

1. A PSI function implementation in `src/`
2. A baseline reference distribution (full Kaggle dataset preferred)
3. At least one post-deployment CBI cycle of current data

All three are Sprint 2 build items.

### Component 2 — Weekly pulse drift detector (false trigger rate)

**Observed false trigger rate: N/A — no pulse history exists.**

`data/audit/pulse.jsonl` does not exist. No pulse records have been written. The false trigger rate denominator (total `reassessment_triggered = True` entries) is zero. The numerator (entries where subsequent CBI scored Low tier) is also zero.

| Signal                              | 50th pct               | 95th pct | 99th pct |
| ----------------------------------- | ---------------------- | -------- | -------- |
| False trigger rate (rolling 4-week) | N/A — no pulse history | N/A      | N/A      |

### Component 3 — ORT detector (ORT firing rate)

**Observed ORT firing rate: N/A — no pilot data exists.**

`compute_ort_status()` has never been called against real data. No ORT trigger history exists in any audit trail.

| Signal                    | 50th pct               | 95th pct | 99th pct |
| ------------------------- | ---------------------- | -------- | -------- |
| ORT firing rate per cycle | N/A — no pilot history | N/A      | N/A      |

---

## 3. Three Rule Shapes

---

### RULE 1 — Burnout risk scorer

**Signal(s):**

1. PSI per feature — specifically `resource_allocation` and `mental_fatigue_score` (the two features where missingness matters per S2-F2, tracked via `missing_ra` and `missing_mfs` indicator features).
2. MFS SHAP percentage — the D16 40% gate is the hard stop. The drift rule monitors approach toward the gate before it fires. Monitor MFS SHAP trend across cycles — not just binary gate pass/fail.
3. FP rate per cycle — monitors approach toward the 20% participation decay hard limit (C1b).

**Cadence:** Quarterly — each CBI cycle produces one data point.

**Threshold:** [FOUNDER SETS] — at 95th percentile of observed variance from Step 2 table. Cannot be grounded until full dataset PSI baseline is computed (Sprint 2).

**Duration window:** TWO consecutive quarterly cycles above threshold before retrain signal fires.

Rationale: One cycle above threshold may be a cohort composition anomaly (new team joined, seasonal crunch period). Two consecutive cycles indicates genuine distribution shift.

**HITL disposition:**

"Signal fires -> operator reviews MFS SHAP trend and feature PSI. Operator decides: retrain, adjust threshold, or hold and monitor third cycle. After three consecutive clean quarterly cycles with stable PSI — operator may opt into automated drift alert (not automated retrain). Default disposition is HITL for every retrain decision."

**Seasonal exclusion:**

"No seasonal reference in Oraclaire cost model. Customer must specify at deployment configuration: known high-stress seasonal windows (e.g. annual performance review period, financial year-end, product launch crunch). Drift signals during declared seasonal windows are flagged but the duration window clock does not start until the seasonal window closes."

---

### RULE 2 — Weekly pulse drift detector

**Signal:** False trigger rate — fraction of `reassessment_triggered = True` entries where subsequent CBI scores Low tier. A high false trigger rate means the 3-consecutive-week drop algorithm (D13 Mechanism A, `PULSE_DRIFT_THRESHOLD = 2`, `PULSE_DRIFT_CONSECUTIVE_WEEKS = 3`) is firing on noise rather than genuine deterioration.

**Cadence:** Weekly — pulse runs weekly, false trigger rate computed rolling 4-week window.

**Threshold:** [FOUNDER SETS] — at 95th percentile of observed variance. Cannot be grounded until Sprint 1 pilot produces pulse history (Sprint 2 activation).

**Duration window:** FOUR consecutive weeks above threshold before rule fires.

Rationale: A single week of high false triggers may be caused by one unusual team event. Four consecutive weeks indicates the pulse baseline has shifted and `config.py::PULSE_DRIFT_THRESHOLD` or `PULSE_DRIFT_CONSECUTIVE_WEEKS` may need recalibration.

**HITL disposition:**

"Signal fires -> operator reviews false trigger distribution by team and tenure cohort. Operator decides: recalibrate PULSE_DRIFT_THRESHOLD, recalibrate PULSE_DRIFT_CONSECUTIVE_WEEKS, or hold and monitor. This is a config change not a model retrain — distinguish the two. Default disposition is HITL."

**Seasonal exclusion:**

"Same as Rule 1 — customer declares seasonal windows at deployment. During declared windows the false trigger rate is expected to rise (genuine 3-week drops are real during crunch periods). Duration window clock pauses during declared seasonal windows. Operator reviews trigger context before deciding whether seasonal triggers indicate real employee need."

**Seasonal asymmetry (named explicitly):**

The seasonal exclusion for Rule 2 is opposite in direction from Rule 1. For Rule 1, seasonal spikes in PSI are NOISE to be excluded from drift detection — the distribution shift is temporary and should not trigger retrain. For Rule 2, seasonal spikes in false triggers may be REAL SIGNALS (employees genuinely deteriorating during crunch) — the HITL disposition is specifically to distinguish the two. This asymmetry exists because Rule 1 monitors the model's input distribution (noise during seasonal periods), while Rule 2 monitors the intervention algorithm's accuracy (which may genuinely decline during seasonal periods because real deterioration is harder to distinguish from normal variation).

---

### RULE 3 — ORT detector

**Signal:** ORT firing rate per cycle — fraction of quarterly cycles where `compute_ort_status()` returns `ort_triggered = True` for at least one team. Secondary signal: which teams trigger ORT repeatedly vs which trigger once. Repeated ORT on the same team is a structural problem, not a model problem.

**Cadence:** Quarterly — ORT fires per CBI cycle.

**Threshold:** [FOUNDER SETS] — at 95th percentile of observed variance. Cannot be grounded until Sprint 1 pilot produces ORT history (Sprint 2 activation).

**Duration window:** THREE consecutive quarterly cycles with ORT triggered on the same team before rule fires.

Rationale: One ORT trigger is an acute event (project crunch, restructure). Two is concerning. Three consecutive cycles on the same team indicates a structural condition that the ORT threshold may need recalibration for — or an organisational problem that HR must address independent of the model.

**HITL disposition:**

"Signal fires -> operator reviews the specific team(s) triggering repeated ORT. Two pathways:
(A) Organisational pathway — HR escalates structural issue (understaffing, toxic management). ORT threshold unchanged.
(B) Calibration pathway — if the team's baseline burnout rate is genuinely elevated relative to the deployment population (e.g. an on-call engineering team) operator may recalibrate `config.py::ORT_CEILING` for that team specifically (per-team ORT ceiling is a Sprint 2 feature — add to Sprint 2 backlog).
Default disposition is HITL with explicit pathway selection."

**Seasonal exclusion:**

"Same customer-declared window as Rules 1 and 2. Additionally: organisational events (restructures, layoffs, rapid headcount changes) are NOT seasonal — they are acute structural events. If an organisational event is declared by the customer, the ORT duration window resets. The event is logged in the audit trail but does not count toward the three-cycle threshold."

---

## 4. Function Citation Table

| Signal                       | Function                      | File                         | Status                                                                                                                                                                                                                                                                                                                                                              |
| ---------------------------- | ----------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PSI per feature              | N/A                           | N/A                          | **NOT IMPLEMENTED.** No PSI function found in `src/`. Phase 13 variance table requires implementation. Sprint 2 build item.                                                                                                                                                                                                                                         |
| MFS SHAP per prediction      | `_shap_explain()`             | `src/model/serve.py:51-85`   | **IMPLEMENTED.** Computes per-prediction SHAP decomposition. Full SHAP values logged to `predictions.jsonl` via `shap_values` field in `PredictionRecord`.                                                                                                                                                                                                          |
| MFS SHAP trend across cycles | N/A                           | N/A                          | **NOT IMPLEMENTED.** Cross-cycle SHAP trend requires reading `predictions.jsonl` across multiple CBI cycles and computing per-feature SHAP percentage over time. Sprint 2 build item.                                                                                                                                                                               |
| FP rate per cycle            | `compute_tier_distribution()` | `src/views/hr_data.py:22-45` | **PARTIALLY IMPLEMENTED.** Produces tier counts from scored results. FP rate requires ground truth labels (`Burn Rate`) at the following assessment cycle — this data dependency does not exist yet. "FP rate computation requires Burn Rate ground truth at the following assessment cycle. Sprint 1 cannot compute retrospective FP rate without a second cycle." |
| Pulse false trigger rate     | `log_pulse()`                 | `src/audit/logger.py:88-127` | **PARTIALLY IMPLEMENTED.** Sets `reassessment_triggered` field in `PulseRecord`. Subsequent CBI result must be joined to pulse records to compute false trigger rate — join logic NOT IMPLEMENTED. Sprint 2 build item.                                                                                                                                             |
| ORT firing rate              | `compute_ort_status()`        | `src/views/hr_data.py:48-82` | **PARTIALLY IMPLEMENTED.** Returns `{alerts, ok_teams, excluded_teams}` as a pure function. ORT trigger history must be logged to audit trail — NOT IMPLEMENTED. `compute_ort_status()` does not write to any audit trail. Sprint 2 build item.                                                                                                                     |
| Threshold drift validation   | `validate_threshold_drift()`  | `src/model/thresholds.py`    | **IMPLEMENTED.** Checks threshold against `DRIFT_ACCEPTABLE_RANGE = (0.30, 0.40)`. This is a deployment-time check, not a cycle-over-cycle drift monitor.                                                                                                                                                                                                           |

---

## 5. Sprint 2 Build Items

1. **PSI computation function** — required for Rule 1 activation — Sprint 2 build item. Must accept two distributions (reference + current) and return per-feature PSI. Register in `src/` with a callable API.

2. **Baseline reference distribution file** — required for Rule 1 activation — Sprint 2 build item. Snapshot full Kaggle dataset per-feature bin counts and statistics as the PSI reference. Persist to `data/processed/drift_reference.json` or equivalent.

3. **MFS SHAP trend computation** — required for Rule 1 activation — Sprint 2 build item. Read `predictions.jsonl` across cycles, compute per-feature SHAP percentage over time, surface MFS trend toward the 40% gate.

4. **FP rate per cycle computation** — required for Rule 1 activation — Sprint 2 build item. Join prediction records to subsequent CBI ground truth, compute per-cycle FP rate against the 20% participation decay hard limit (C1b).

5. **Pulse-to-CBI join logic** — required for Rule 2 activation — Sprint 2 build item. Join `pulse.jsonl` records with `reassessment_triggered = True` to subsequent CBI results in `predictions.jsonl` to determine false trigger rate.

6. **ORT audit trail logging** — required for Rule 3 activation — Sprint 2 build item. `compute_ort_status()` must write its result (which teams triggered, cycle timestamp) to `data/audit/ort.jsonl` or equivalent. Currently a pure function with no side effects.

7. **Per-team ORT ceiling** — required for Rule 3 calibration pathway — Sprint 2 backlog item. `config.py::ORT_CEILING` is currently global. Rule 3's calibration pathway requires per-team ORT ceiling configuration.

---

## 6. Closing

Phase 13 drift rules drafted. Threshold values are [FOUNDER SETS] throughout. All three rules are structurally defined but cannot activate until:

- Rule 1: PSI function + baseline reference + full dataset available
- Rule 2: Sprint 1 pilot completes one full quarterly cycle (90 days)
- Rule 3: Sprint 1 pilot completes one full quarterly cycle + ORT audit trail logging

Seven Sprint 2 build items identified. Waiting for founder's threshold values per rule.
