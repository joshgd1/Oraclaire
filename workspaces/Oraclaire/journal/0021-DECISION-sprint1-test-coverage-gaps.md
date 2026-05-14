# D21: Sprint 1 Test Coverage Gap Resolution

**Date:** 2026-05-14
**Status:** Approved
**Authority:** Founder directive — Sprint 1 is not done until the integration test is honest

## Context

Session resume found Sprint 1 code complete (9 steps on disk) but integration tests covered only 2 of 9 Step 9 criteria fully, 2 partially, and 4 not at all. Four untested criteria and two partials must be resolved before commit.

## Dispositions

### C1 — Tier boundaries vs Phase 4 prediction table (PARTIAL → FIX)

Boundary test is correct but insufficient. Phase 4 prediction table has 12 known employees with known tiers. Test must verify current 12-row model produces tiers consistent with current artifact, not identity with the 13-row Phase 4 run. fakeEMP_007 divergence is expected and acceptable.

### C2 — Audit trail for all 12 employees (PARTIAL → FIX)

Must extend from 1 employee to all 12. Per-entry checks: employee_id, timestamp parseable, risk_tier in {low,moderate,high,critical}, shap_values has 8 keys matching FEATURES, reviewer_id is None, review_status is None.

### C3 — No individual data in HR view (NOT TESTED → ADD)

Score 12 employees, assign to two teams of 6. Assert HR output contains no employee_id, no individual probability, no individual SHAP values. Only tier counts.

### C4 — Critical tier held in reviewer queue (NOT TESTED → ADD)

Score one employee at 0.90 (Critical). Confirm tier is Critical, audit entry exists, reviewer fields are None. Assert HR view does NOT show unreviewed Critical flags — if it does, test catches the leak.

### C5 — ORT fires above 20% (NOT TESTED → ADD)

Team of 10: 3 High + 1 Critical (approved) = 40% → ORT fires, individual alerts suppressed. Second team: 1 High + 1 Critical = 20% exactly → ORT does NOT fire (D14: "exceeds 20%", boundary inclusive test).

### C6 — Pulse drift triggers reassessment (NOT TESTED → ADD)

Five-week sequence: 4→4→2→2→2. After week 5 (third consecutive drop): reassessment_triggered=True, drift_weeks=3. Week 6 recovery to 4: reset to triggered=False, drift_weeks=0. Recovery reset is as important as trigger.

### C7 — MFS gate halt behaviour (PARTIAL → FIX)

Happy path tested. Halt path not tested. Mock SHAP to return MFS=45%. Assert: train() raises, no artifact written, error message contains "MFS SHAP dominance" and "D16".

## Test Plan

| Test                              | Criterion |
| --------------------------------- | --------- |
| test_phase4_prediction_table      | C1        |
| test_audit_trail_all_12           | C2        |
| test_hr_view_no_individual_data   | C3        |
| test_critical_held_in_queue       | C4        |
| test_ort_fires_above_20_percent   | C5        |
| test_pulse_drift_triggers_flag    | C6        |
| test_mfs_gate_halts_serialisation | C7        |

All seven must pass before Sprint 1 commit.
