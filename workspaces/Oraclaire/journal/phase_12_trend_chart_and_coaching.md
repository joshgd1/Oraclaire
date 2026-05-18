# Phase 12 — Longitudinal Trend Chart, Peer Benchmark & Manager Coaching Network

## What

Completed three related features that together give employees and managers richer, more actionable dashboards.

### 1. Longitudinal Trend Chart Upgrade

**File:** `src/views/employee_ux.py`

- Replaced sparkline with Plotly-powered trend chart with tier-colored data points
- Each pulse point is colored by its tier: green (low), amber (moderate), orange (high), red (critical)
- Added richer trajectory summary showing direction icon, point delta, and tier-shift comparison
- Added `_save_pulse()` — appends completed pulse/check-in to `data/audit/pulse.jsonl` for longitudinal tracking
- Upgraded `_load_pulse_history()` to 12 weeks (was 5), deduplicates by date
- Redesigned privacy banner with gradient background, lock icon, and flex layout

### 2. Peer Benchmark Card

**File:** `src/views/employee_ux.py` + `src/model/services/peer_benchmark.py`

- Added `get_peer_benchmark()` integration to employee dashboard
- Shows employee how their wellbeing dimensions (Workload, Energy, Recovery, Burnout) compare to peers with similar seniority, tenure, WFH setup, and company type
- Peer averages computed from Kaggle MBI training dataset, cached in `_PEER_AVG_CACHE`
- Falls back to population mean (50.0) when bucket has <5 peers or CSV unavailable
- Displays as collapsible card with bucket label (Seniority · Tenure · WFH · Company)

### 3. Manager Coaching Network

**File:** `src/views/manager.py` + `src/model/services/coach_feedback.py`

- Built `coach_feedback.py` service: in-memory store of manager intervention ratings
- `submit_feedback()` — manager rates whether an intervention helped/neutral/didn't help
- `get_worked_recommendations()` — returns top-rated interventions for teams with similar ORT and size profile (peer matching by ORT bucket ±1 team-size bucket)
- `get_my_feedback()` — returns manager's own prior ratings
- Manager dashboard `render_recommendations()` updated with "did these help?" feedback buttons on each resource
- New `render_worked_panel()` shows "what worked for similar teams" with star ratings and helpful % bars
- Data is in-memory only — resets on app restart (no persistence layer yet)

## Commits

`src/views/employee_ux.py` — trend chart upgrade + peer benchmark card
`src/views/manager.py` — coaching feedback integration
`src/model/services/coach_feedback.py` — new service
`src/model/services/peer_benchmark.py` — new service (already existed from prior session)

## Known Gaps

- `coach_feedback` is in-memory only — resets on app restart. No persistence layer yet.
- `peer_benchmark` falls back to population mean if Kaggle dataset is relocated.
- `team_size` hardcoded to 8 in coaching feedback submit calls — should come from real team data.
