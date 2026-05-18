# Oraclaire — Master Build Plan

**Phase:** /todos (Phase 2)
**Date:** 2026-05-13
**Status:** APPROVED 2026-05-15

M1 (Foundation) + M2 (Nexus backend) — COMPLETED in commit 5e33d85.
**Decisions locked:** D1–D15
**Model:** Autonomous execution (all estimates in sessions, not human-days)
**Red-teamed:** 2026-05-13 — 3 CRITICAL, 6 HIGH, 8 MEDIUM findings incorporated

---

## Decision Register

| Decision | One-line summary                                                                         | Todos depending on it             |
| -------- | ---------------------------------------------------------------------------------------- | --------------------------------- |
| D1       | Product is classification, not prediction                                                | M4-01, M4-06                      |
| D2       | FP ceiling 20% before participation decay                                                | M4-02, M4-06                      |
| D3       | Random Forest + SHAP model family                                                        | M4-01, M4-04                      |
| D4       | Classification framing over prediction                                                   | M2-01, M6-01                      |
| D5       | SHAP for transparency + human review                                                     | M4-04, M5-01                      |
| D6       | Exclusions require HRIS or manual enforcement                                            | M1-08, M8-06                      |
| D7       | 20% Sprint 1 participation target                                                        | M3-07, M3-10                      |
| D8       | Human review gate at Critical tier only                                                  | M5-01, M5-02                      |
| D9       | D14 two-threshold FN architecture                                                        | M4-02, M4-03                      |
| D10      | Kaggle MBI dataset for initial training                                                  | M4-01                             |
| D13      | Four participation mechanisms (pulse, CBI, 24h gate, content library)                    | M3-02 through M3-06, M5-06, M5-08 |
| D14      | 60/40 tier split, $3,698.63 daily constant, auto-flag ceiling 20%                        | M4-02, M5-04, cost-model.md       |
| D15      | Seniority configurable, auto-flag trigger 2 weeks, 48h withdrawal, scoreable denominator | M1-08, M2-01, M3-07, M5-04        |

## Governance Requirements Index

| G#   | Requirement                                             | Todos satisfying it |
| ---- | ------------------------------------------------------- | ------------------- |
| G-1  | Manager sees team aggregates only (min 5)               | M1-07, M6-05, M6-06 |
| G-2  | Consent screen presents three disclosures before opt-in | M2-01               |
| G-3  | Employee data ownership (view/export/delete)            | M2-04, M2-05, M7-02 |
| G-4  | No HRIS/performance-management export                   | M7-03               |
| G-5  | Bias audit before each customer deployment              | M4-07, M9-06        |
| G-6  | Min team size 5 for aggregate display                   | M3-09               |
| G-9  | 12-month data retention, hard delete                    | M7-01               |
| G-10 | Customer acceptable use policy                          | M7-08               |

---

## Milestone 1 — Foundation & Infrastructure

**Value anchor:** Everything else depends on these. No value until they exist.
**Estimated:** 1–2 sessions

| #     | Todo                                                                                                                                                                                                                                                                                                                                                                                       | Specs                               | Build | Wire |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------- | ----- | ---- |
| M1-00 | Build organisation data model — id, name, jurisdiction (SG/EU/US/other), works_council_approved (bool), created_at, updated_at. SQLAlchemy model + Alembic migration. All top-level entities carry organisation_id FK.                                                                                                                                                                     | regulatory-constraints.md §3-4, D14 | B     |      |
| M1-01 | Build employee data model — id, organisation_id (FK), seniority_tier (junior/senior), seniority_source (hris_derived/self_reported, null rejected), consent_status, consent_timestamp, team_id, exclusion_status, exclusion_category, created_at, updated_at. SQLAlchemy model + Alembic migration.                                                                                        | population-and-scoring.md §1, D15-1 | B     |      |
| M1-02 | Build team data model — id, organisation_id (FK), name, department_id, member_count (denormalised), aggregate_score, participation_rate, last_assessment_date. SQLAlchemy model + Alembic migration.                                                                                                                                                                                       | population-and-scoring.md §1        | B     |      |
| M1-03 | Build department data model — id, organisation_id (FK), name, created_at. SQLAlchemy model + Alembic migration.                                                                                                                                                                                                                                                                            | M6-03 aggregation dimension         | B     |      |
| M1-04 | Build assessment cycle model — id, organisation_id (FK), cycle_type (pulse/cbi), started_at, closed_at, status (open/closed). SQLAlchemy model + Alembic migration.                                                                                                                                                                                                                        | product-identity.md §4              | B     |      |
| M1-05 | Build assessment response model — id, cycle_id, employee_id, item_index, response_value, submitted_at. SQLAlchemy model + Alembic migration.                                                                                                                                                                                                                                               | product-identity.md §4              | B     |      |
| M1-06 | Build risk score model — id, employee_id, cycle_id, risk_tier (low/moderate/high/critical), numeric_score, shap_values (JSON with explicit schema: [{feature, impact_value, direction}]), model_version, scored_at, seniority_tier_at_score. SQLAlchemy model + Alembic migration.                                                                                                         | product-identity.md §2, D14-7       | B     |      |
| M1-07 | Build deployment parameter store — key-value config table scoped per organisation: grievance_cooldown_days (default 90), auto_flag_ceiling_pct (default 20), auto_flag_trigger_consecutive_weeks (default 2), participation_target_sprint1 (0.20), participation_target_architecture (0.40), seniority_default_source (hris_derived), retention_months (12). SQLAlchemy model + admin API. | D14, D15-2                          | B     | W    |
| M1-08 | Build access control matrix — role table (employee, manager, hr_admin, system_admin), permission rules: manager sees team aggregates only (min 5 members), hr sees org trends + exclusion counts, employee sees own data only. Enforce at API middleware layer.                                                                                                                            | population-and-scoring.md §1, G-1   | B     | W    |
| M1-09 | Build exclusion engine — service class that checks HRIS data (or manual admin input) against exclusion categories (PIP, ADA, FMLA, workers comp, disciplinary, grievance cooldown). Returns exclusion_status + exclusion_category per employee. Graceful degradation when HRIS absent.                                                                                                     | population-and-scoring.md §2-3, D6  | B     |      |
| M1-10 | Wire exclusion engine to employee model — on each assessment cycle start, run exclusion engine for all employees, update exclusion_status and exclusion_category fields. Excluded employees removed from scoring pipeline.                                                                                                                                                                 | population-and-scoring.md §3        |       | W    |
| M1-11 | Build audit log service — immutable append-only log: actor_id, action, target_entity_type, target_entity_id, timestamp, metadata_json. Wire into every API endpoint that reads or modifies employee/score data. Required for GDPR Art. 30, EU AI Act transparency, and conformity assessment.                                                                                              | regulatory-constraints.md §2, G-5   | B     | W    |

---

## Milestone 2 — Backend Infrastructure (Nexus)

**Value anchor:** Every Wire todo needs a server to wire to. This milestone must land before M3–M7 wiring can proceed.
**Estimated:** 1 session

| #     | Todo                                                                                                                                                                                                                                                                                                                                                                        | Specs                         | Build | Wire |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- | ----- | ---- |
| M2-01 | Build Nexus app with handler pattern — Nexus app instance with authentication middleware (JWT), CORS, rate limiting (per-endpoint: assessment 10/min, auth 5/min, data export 2/hour, general 100/min). Base middleware stack.                                                                                                                                              | product-identity.md §6        | B     |      |
| M2-02 | Build auth plugin — JWT authentication, RBAC (employee/manager/hr_admin/system_admin), tenant isolation (organisation-scoped queries). Employee SSO integration (same provider as HRIS where possible, email magic link fallback).                                                                                                                                          | G-1, M1-08                    | B     |      |
| M2-03 | Build employee authentication flow — SSO or magic-link login, employee record provisioning on first access (HRIS-synced where available, self-registration fallback), initial consent_status = pending, redirect to consent screen on first access.                                                                                                                         | D15-1                         | B     |      |
| M2-04 | Build cycle management API — POST /api/cycle (create new assessment cycle), POST /api/cycle/{id}/close (close cycle, trigger scoring). Admin-only.                                                                                                                                                                                                                          | product-identity.md §4        | B     |      |
| M2-05 | Build scoring trigger — on cycle close, enqueue scoring job that runs exclusion filter → model inference → SHAP → tier classification → store results. Async via task queue.                                                                                                                                                                                                | product-identity.md §2-3      | B     |      |
| M2-06 | Build HRIS adapter interface — abstract adapter with methods: get_exclusion_status(employee_id), get_seniority(employee_id), get_team_membership(employee_id). Concrete implementations: WorkdayAdapter, BambooHRAdapter, ManualInputAdapter. Graceful fallback when adapter unavailable.                                                                                   | product-identity.md §6, D15-1 | B     |      |
| M2-07 | Wire HRIS adapter to exclusion engine — exclusion engine reads from HRIS adapter. If adapter returns error/null, fall back to manual admin input. Circuit breaker pattern, retry with exponential backoff, partial-failure handling (proceed with fetched employees, flag remainder for manual review). Admin alert on sustained adapter failure. Log all adapter failures. | D6, D15-1                     |       | W    |

---

## Milestone 3 — Employee Consent & Onboarding

**Value anchor:** Without consent, no data. Without data, no product.
**Estimated:** 1 session

| #     | Todo                                                                                                                                                                                                                                                                                                                          | Specs                                    | Build | Wire |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- | ----- | ---- |
| M3-01 | Build opt-in consent screen — React page presenting three disclosures (data collected, usage, visibility) before opt-in action is enabled. Consent timestamp stored on employee record. When seniority_source is self_reported, show required seniority_tier selector (junior/senior). One question. No clinical language.    | population-and-scoring.md §1, D15-1, G-2 | B     |      |
| M3-02 | Build withdrawal flow — React page with withdrawal request, 48-hour countdown display, cancel button, confirmation message: "Your withdrawal request has been received. Your individual data will stop being collected in 48 hours. You can cancel this request any time before then." No guilt language. No HR notification. | D15-3                                    | B     |      |
| M3-03 | Wire withdrawal to backend — POST /api/withdrawal creates withdrawal record with effective_at (now + 48h). Scheduled job processes suppression at effective_at. Suppresses all individual scores from all viewers. No notification to HR or managers. Employee appears only in team aggregates if team size >= 5.             | D15-3                                    |       | W    |
| M3-04 | Build employee data ownership controls — React page with view/export/delete actions for individual data. Export as JSON. Delete triggers immediate suppression (no 48h cooling-off for delete — different from withdrawal).                                                                                                   | G-3                                      | B     |      |
| M3-05 | Wire data ownership to backend — GET /api/employee/{id}/data (view), GET /api/employee/{id}/export (JSON export), DELETE /api/employee/{id}/data (immediate suppression). Access control: employee can only access own data. Audit log entry on every access.                                                                 | G-3                                      |       | W    |
| M3-06 | Build onboarding checklist tool — deployment checklist page for admin: (1) measure e (exclusion fraction) as first step, (2) configure jurisdiction, (3) validate HRIS connection, (4) set seniority source, (5) confirm participation targets. Each step required before activation.                                         | D14-5                                    | B     |      |

---

## Milestone 4 — Data Collection

**Value anchor:** CBI + pulse are the model's training data. No data, no model. The primary product loop starts here.
**Estimated:** 1–2 sessions

| #     | Todo                                                                                                                                                                                                                                                                                                       | Specs                             | Build      | Wire       |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- | ---------- | ---------- |
| M4-01 | Build CBI instrument service — 19-item Copenhagen Burnout Inventory scoring engine. Accepts item-level responses, produces subscale scores (personal burnout, work-related burnout, client-related burnout) and composite score. Input validation for all 19 items. Wire into scoring pipeline (M5-08).    | product-identity.md §4, D10       | ~~B~~ DONE | ~~W~~ DONE |
| M4-02 | Build CBI assessment page — React survey form presenting 19 CBI items with validated response scales. Progress indicator. Save-on-each-response for partial completion. Employee sees own previous cycle scores for comparison. Accessible (WCAG 2.1 AA).                                                  | D13 mechanism B                   | B          |            |
| M4-03 | Wire CBI page to backend — POST /api/cycle/{id}/response stores each item response. POST /api/cycle/{id}/submit closes the assessment. Triggers participation tracking update.                                                                                                                             | product-identity.md §4            |            | ~~W~~ DONE |
| M4-04 | Build weekly pulse service — single CBI item selected by rotation schedule, 10-second response. Response stored with cycle_id (pulse type). Aggregation logic at team level (no individual pulse visibility to HR). Wire aggregation into team aggregate computation.                                      | D13 mechanism A                   | ~~B~~ DONE | ~~W~~ DONE |
| M4-05 | Build weekly pulse page — React component: single question, Likert scale, submit. Display: employee's own pulse trend chart (last 12 weeks). Accessible (WCAG 2.1 AA).                                                                                                                                     | D13 mechanism A                   | B          |            |
| M4-06 | Wire pulse page to backend — POST /api/pulse/response. GET /api/employee/{id}/pulse-trend returns last N pulse scores for chart.                                                                                                                                                                           | D13 mechanism A                   |            | ~~W~~ DONE |
| M4-07 | Build participation tracking service — for each cycle, compute: scoreable_population (total employees minus excluded), responded_count, participation_rate (responded/scoreable). Track against 20% sprint1 and 40% architecture targets. Wire: triggered on every response submission and on cycle close. | D7, D13, D15-4                    | ~~B~~ DONE | ~~W~~ DONE |
| M4-08 | Build participation drop alert — automated alert when participation falls below 20% sustained for two consecutive cycles. Wire: scheduled job runs after each cycle close. Alert surfaced on hr_admin dashboard only. No employee-facing notification.                                                     | D7 discussion                     | B          | W          |
| M4-09 | Build minimum team size suppression — suppress team aggregate display and API response if team has fewer than 5 contributing members. Wire: enforced at API middleware layer AND at scoring layer. Historical aggregates from when team was >= 5 remain visible.                                           | G-6, population-and-scoring.md §1 | B          | W          |
| M4-10 | Build notification/reminder service — email or in-app notification when new pulse/CBI cycle opens, reminder at midpoint for non-respondents, notification when employee's score is viewable (post 24h gate). Consent-aware (withdrawn employees excluded). No score content in notifications.              | D7, D13                           | B          | W          |

---

## Milestone 5 — ML Pipeline

**Value anchor:** The scoring engine. This IS the product's core capability — everything else is packaging around it.
**Estimated:** 2–3 sessions (sharded per autonomous-execution budget)

**Dependencies:** M4-01 through M5-07 can proceed in parallel with M4 (Data Collection). M5-08 (end-to-end wire) MUST wait for M4 to complete.

| #     | Todo                                                                                                                                                                                                                                                                                                                                                                                                      | Specs                                                | Build | Wire |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- | ----- | ---- |
| M5-01 | Build Random Forest training pipeline — data loading from Kaggle MBI/burnout dataset, feature engineering (CBI subscale scores as primary features), train/test split (cross-sectional), model training with hyperparameter grid search, model versioning. Output: serialized model artifact with version tag.                                                                                            | product-identity.md §3, D10, cost-model.md §1-2      | B     |      |
| M5-02 | Build two-threshold calibration — model produces raw score, then applies tier-specific thresholds. General population: optimize for FN <= 15%, FP <= 15%. Senior tier: optimize for FN <= 10%, FP <= 20%. Seniority_tier field routes to correct threshold. Cost-model.md §4 defines the economic rationale for the asymmetric targets.                                                                   | D14-9, D15-1, cost-model.md §4                       | B     |      |
| M5-03 | Wire two-threshold calibration to employee model — scoring pipeline reads seniority_tier from employee record, applies correct threshold table. If seniority_tier is null (should not happen per D15-1), fallback to general population threshold + log warning + audit log entry.                                                                                                                        | D14-9, D15-1                                         |       | W    |
| M5-04 | Build SHAP explainability service — for any scored employee, generate SHAP decomposition showing top-N contributing features with relative impact. Output: JSON array of {feature, impact_value, direction} with explicit schema. Must complete in <2s per score for real-time dashboard use.                                                                                                             | product-identity.md §3, regulatory-constraints.md §2 | B     |      |
| M5-05 | Wire SHAP to scoring pipeline — after model produces raw score and tier classification, run SHAP explainer. Store shap_values JSON + model_version on risk_score record. Available for: employee dashboard, HR dashboard, human review context, right-to-explanation API.                                                                                                                                 | product-identity.md §3                               |       | W    |
| M5-06 | Build risk-tier classifier — map model output to four tiers with calibration targets: Critical (<=5% of scorable), High (10-15%), Moderate (20-25%), Low (remainder). These are calibration guides, not hard constraints — thresholds move to match data. Wire: called within end-to-end pipeline (M5-08).                                                                                                | D14-7, cost-model.md §4                              | B     | W    |
| M5-07 | Build trajectory classification service — compare scores across cycles (minimum 2 cycles required). Classify as improved if numeric_score delta exceeds threshold, worsened if delta below negative threshold, held otherwise. First cycle: no trajectory. Wire: called by M6-02 trajectory endpoint.                                                                                                     | product-identity.md §4                               | B     | W    |
| M5-08 | Build bias audit module — automated disparate impact analysis: run model on demographic slices, compute tier distribution per group, flag if any group's Critical+High rate differs from population mean by >10pp. Output: audit report JSON. Must run before each customer deployment. Cost-model.md §2 provides the FP-participation-decay rationale for why precision matters in disadvantaged groups. | G-5, cost-model.md §2                                | B     |      |
| M5-09 | Wire scoring pipeline end-to-end — CBI responses in → exclusion filter → model inference → two-threshold calibration → risk tier → SHAP decomposition → trajectory classification → store risk_score record. Wire as scheduled job triggered on cycle close (M2-05). DEPENDS ON M4 COMPLETION.                                                                                                            | product-identity.md §2-3, cost-model.md §1-4         |       | W    |
| M5-10 | Build model deployment workflow — version promotion (staging to production), rollback mechanism, compatibility check against current feature schema. New model version stored with artifact; risk_score records reference model_version at time of scoring.                                                                                                                                               | cost-model.md §4                                     | B     |      |

---

## Milestone 6 — Alerting & Intervention

**Value anchor:** "Detection-only is decorative." The remediation loop is where commercial value lives.
**Estimated:** 1–2 sessions

| #     | Todo                                                                                                                                                                                                                                                                                                                                                                            | Specs                            | Build | Wire |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------- | ----- | ---- |
| M6-01 | Build Critical-tier human review gate — API endpoint that holds Critical-tier alerts in pending_review state. HR reviewer sees SHAP context, employee history, and must explicitly approve/override before any intervention triggers. Override requires reason text. No auto-escalation from Critical without human action.                                                     | regulatory-constraints.md §2, D8 | B     |      |
| M6-02 | Build human review UI — React page for HR: list of pending Critical reviews, each showing SHAP decomposition, trajectory across cycles, and approve/override buttons. Override requires reason text field.                                                                                                                                                                      | regulatory-constraints.md §2     | B     |      |
| M6-03 | Wire human review UI to backend — GET /api/reviews/pending returns Critical-tier flags awaiting review. POST /api/reviews/{id}/approve releases intervention. POST /api/reviews/{id}/override changes tier + stores reason. Audit log entry on every review action.                                                                                                             | regulatory-constraints.md §2     |       | W    |
| M6-04 | Build Organisational Risk Threshold service — track High+Critical combined rate per team. If rate exceeds deployment parameter auto_flag_ceiling_pct (default 20%) for two consecutive weekly pulses OR single quarterly CBI cycle, suppress individual alerts for that team and generate single organisational risk report. Wire: scheduled job runs after each scoring cycle. | D14-10, D15-2                    | B     | W    |
| M6-05 | Build organisational risk report — structured report for HR: team name, combined High+Critical rate, duration of elevation, recommended actions (not individual employees). Individual alerts for that team remain suppressed until rate drops below ceiling. Wire: surfaced on HR dashboard via GET /api/org/risk-indicators.                                                  | D14-10                           | B     | W    |
| M6-06 | Build SHAP-matched content library service — map top SHAP factors to curated resources. Tiered: Low (self-guided), Moderate (team resources), High (professional pathways), Critical (professional pathways with urgency). Content stored as JSON with factor keywords.                                                                                                         | D13 mechanism D                  | B     |      |
| M6-07 | Wire content library to assessment results — after each scoring cycle, for each employee with a score, generate 2-3 resource recommendations matched to their top SHAP factors. Store on risk_score record. Surface on employee dashboard.                                                                                                                                      | D13 mechanism D                  |       | W    |
| M6-08 | Build employee-first 24-hour visibility gate — after scoring cycle completes, employee data is immediately visible to the employee. HR access to cycle results is delayed by 24 hours (hardcoded, not configurable per D13). Wire: timestamp comparison in API middleware layer.                                                                                                | D13 mechanism C                  | B     | W    |

---

## Milestone 7 — Dashboards

**Value anchor:** The product's visible output. Where HR, managers, and employees see value.
**Estimated:** 2 sessions

| #     | Todo                                                                                                                                                                                                                                                                                                                                            | Specs                             | Build | Wire |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- | ----- | ---- |
| M7-01 | Build employee dashboard page — React: own risk tier with SHAP breakdown, trajectory across cycles (improved/held/worsened), pulse trend chart (last 12 weeks), curated resource recommendations, data ownership controls (view/export/delete). Accessible (WCAG 2.1 AA). Access: own data only.                                                | D13, regulatory-constraints.md §2 | B     |      |
| M7-02 | Wire employee dashboard to backend — GET /api/employee/{id}/scores returns scored cycles with SHAP. GET /api/employee/{id}/trajectory returns trajectory classification (from M5-07). GET /api/employee/{id}/recommendations returns SHAP-matched resources.                                                                                    | D13                               |       | W    |
| M7-03 | Build HR dashboard page — React: org-wide burnout trends (line chart by team/department over cycles), participation rates against 20%/40% targets, exclusion count summary at category level ("47 outside scoring window: 12 on leave, 23 protected process, 12 grievance cooldown"), systemic risk indicators, pending Critical reviews count. | D15-4, G-5, D8                    | B     |      |
| M7-04 | Wire HR dashboard to backend — GET /api/org/trends returns aggregate scores over time. GET /api/org/participation returns rates by team. GET /api/org/exclusions returns category-level counts. GET /api/org/risk-indicators returns teams above auto-flag ceiling (from M6-04).                                                                | D15-4                             |       | W    |
| M7-05 | Build manager dashboard page — React: team aggregate burnout trend (suppressed if team < 5), action recommendations matched to team's top SHAP factors, intervention prompt when team has High-tier concentration. No individual employee names or scores visible. Accessible (WCAG 2.1 AA).                                                    | D13, G-1                          | B     |      |
| M7-06 | Wire manager dashboard to backend — GET /api/team/{id}/aggregate returns team-level scores. GET /api/team/{id}/recommendations returns team-level SHAP-matched actions. Access control: manager can only query teams they manage.                                                                                                               | D13, G-1                          |       | W    |
| M7-07 | Build trajectory display component — shared React component showing employee/team trajectory (improved/held/worsened) across cycles with visual indicator. Used in both employee and manager dashboards.                                                                                                                                        | product-identity.md §4            | B     |      |

---

## Milestone 8 — Compliance & Data Lifecycle

**Value anchor:** Regulatory survival. Enterprise-procurement-blocking if missing. Runs in parallel with M5–M7.
**Estimated:** 1 session

| #     | Todo                                                                                                                                                                                                                                                                                                                                                                  | Specs                              | Build | Wire |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- | ----- | ---- |
| M8-01 | Build data retention engine — scheduled job that deletes individual-level assessment responses and risk scores older than retention_months (default 12, configurable via deployment parameter). Team aggregates retained indefinitely. Delete is hard delete, not soft delete. Audit log entry on every retention sweep.                                              | G-9                                | B     |      |
| M8-02 | Wire data retention engine to cycle close — after each cycle close, check for data exceeding retention_months. Run as scheduled job.                                                                                                                                                                                                                                  | G-9                                |       | W    |
| M8-03 | Build data subject rights API — three endpoints: GET /api/employee/{id}/data (full data access), GET /api/employee/{id}/export (JSON export of all individual data), DELETE /api/employee/{id}/data (immediate hard delete, no cooling-off). Employee can only access own data. Audit log entry on every invocation.                                                  | G-3, regulatory-constraints.md §1  | B     |      |
| M8-04 | Build no-HRIS-export guard — API middleware that blocks any response format or endpoint that would facilitate export to HRIS or performance management systems. Enforce at API layer: no bulk employee score export, no endpoint that returns score + employee_name together.                                                                                         | G-4                                | B     |      |
| M8-05 | Build jurisdictional gating service — deployment parameter for jurisdiction. Singapore: PDPA consent + breach notification (3-day timeline) + data portability. EU: works council approval check (suppress individual scoring if DE/FR/NL without approval). US: state-level considerations. Tier 2 (aggregate only) remains available regardless of jurisdiction.    | regulatory-constraints.md §4, PDPA | B     |      |
| M8-06 | Build right-to-explanation API — GET /api/employee/{id}/explanation returns human-readable SHAP breakdown in plain language: "Your burnout risk score was driven primarily by [factor names]. The top factor was [X] which contributed [Y]% to your score." Available for any employee with a score, required for Critical-tier. Audit log entry on every invocation. | regulatory-constraints.md §2       | B     |      |
| M8-07 | Write conformity assessment document — describe model architecture (Random Forest), features (CBI subscales), training data (Kaggle MBI), scoring process, audit trail structure (reference M1-11 audit log), human oversight at Critical tier. Markdown in docs/compliance/. Required before any EU customer engagement.                                             | regulatory-constraints.md §2       | B     |      |
| M8-08 | Write DPIA template — Data Protection Impact Assessment for EU customers. Template covering: data flows, purpose limitation, retention periods, consent mechanism, cross-border transfer safeguards. Markdown in docs/compliance/.                                                                                                                                    | regulatory-constraints.md §1       | B     |      |
| M8-09 | Write PDPA compliance addendum — Singapore-specific: PDPA consent obligations, 3-day breach notification procedure, data portability implementation (distinct from GDPR export), deemed consent limitations in employment context, cross-border transfer safeguards for Singapore-hosted data. Markdown in docs/compliance/.                                          | regulatory-constraints.md §1       | B     |      |
| M8-10 | Write customer acceptable use policy — template reviewed by employment law counsel (US, EU, works council). Prohibits: using scores for performance reviews, promotions, terminations, insurance decisions. Includes audit rights for Oraclaire.                                                                                                                      | G-10                               | B     |      |
| M8-11 | Write template DPA — Data Processing Agreement covering GDPR Articles 28-30. Template for each customer signing.                                                                                                                                                                                                                                                      | regulatory-constraints.md §1       | B     |      |
| M8-12 | Write positioning language for legal review — "organisational wellbeing analytics" not "employee burnout detection." Document with rationale for counsel review.                                                                                                                                                                                                      | ethical analysis §6.3              | B     |      |
| M8-13 | Write crisis communication plan — before launch. Covers: data breach response, media inquiry handling, customer communication template, internal escalation path.                                                                                                                                                                                                     | ethical analysis §5.3              | B     |      |

---

## Milestone 9 — Testing

**Value anchor:** Production safety. Tier 2/3 tests against real infrastructure validate the whole system.
**Estimated:** 2 sessions

| #     | Todo                                                                                                                                                                                                                                                                                 | Specs                        | Build | Wire |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------- | ----- | ---- |
| M9-01 | Build Tier 1 unit tests — test all service classes in isolation: CBI scoring engine, SHAP explainer (mock model), exclusion engine, participation tracker, retention engine, two-threshold calibration, trajectory classifier. Target: 80% coverage general, 100% security-critical. | testing.md                   | B     |      |
| M9-02 | Build Tier 2 integration tests — test against real PostgreSQL: cycle creation, response storage, scoring pipeline end-to-end, exclusion detection, participation tracking, data retention deletion, audit log completeness. NO mocking.                                              | testing.md                   | B     |      |
| M9-03 | Build Tier 3 E2E tests — full user journey: employee opts in → completes CBI → cycle closes → scoring runs → dashboard shows results → HR sees aggregate → manager sees team trend. Playwright against running app.                                                                  | testing.md                   | B     |      |
| M9-04 | Build regression test for scoring pipeline — test that end-to-end scoring produces expected tier for known input patterns. Lives in tests/regression/.                                                                                                                               | testing.md                   | B     |      |
| M9-05 | Build probe-driven verification — for dashboard recommendations, right-to-explanation output, and SHAP display: structural probes verifying the output contains required fields and correct structure. No regex on semantic claims.                                                  | probe-driven-verification.md | B     |      |
| M9-06 | Build bias audit integration test — run bias audit module against synthetic data with known demographic distributions. Verify that the audit correctly flags disparate impact per cost-model.md §2 FP-decay rationale.                                                               | G-5, cost-model.md §2        | B     |      |

---

## Milestone 10 — Deployment Pipeline

**Value anchor:** A product that cannot be deployed cannot be used.
**Estimated:** 1 session

| #      | Todo                                                                                                                                                                                   | Specs       | Build | Wire |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ----- | ---- |
| M10-01 | Build CI/CD pipeline — GitHub Actions workflow: lint, type check, unit tests on every PR. Integration tests on merge to main. Deploy to staging on main. Promote to production on tag. | git.md      | B     |      |
| M10-02 | Build Docker configuration — backend Dockerfile (Python/Nexus), frontend Dockerfile (React static build + nginx). Docker Compose for local development with PostgreSQL.                | deploy/     | B     |      |
| M10-03 | Build database migration runner — Alembic migration runner in deployment pipeline. Auto-run on deploy. Rollback procedure on migration failure.                                        | M1-x        | B     |      |
| M10-04 | Build environment configuration — dev, staging, production configs. Secrets management (no .env in repo). Environment-specific deployment parameters.                                  | security.md | B     |      |
| M10-05 | Build API documentation — auto-generate OpenAPI spec from Nexus handlers. Published on CI. Available for enterprise security review.                                                   | M2-01       | B     |      |

---

## Milestone 11 — Sprint 2 Prep (Post-Sprint-1 Foundation)

**Value anchor:** Enterprise audit says causal analysis (workload-burnout correlation) is where commercial value lives. Sprint 1 is the foundation; Sprint 2 is the revenue product.
**Estimated:** Deferred — Sprint 2 scope, not Sprint 1

**Value-anchor (per value-prioritization.md MUST-2):** Each item below enables the enterprise audit's "action problem" — the gap between detection and remediation that determines renewal. Sprint 1 builds the detection foundation; Sprint 2 closes the action loop.

| #      | Todo                                                                                                                                                                                                                                                                                                         | Specs               | Build | Wire |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------- | ----- | ---- |
| M11-01 | Build Jira connector adapter — team-aggregate workload data (story points, sprint velocity, backlog size). Read-only at team level.                                                                                                                                                                          | D10 Sprint 2        | B     |      |
| M11-02 | Build Linear connector adapter — same interface as Jira connector.                                                                                                                                                                                                                                           | D10 Sprint 2        | B     |      |
| M11-03 | Build Asana connector adapter — same interface.                                                                                                                                                                                                                                                              | D10 Sprint 2        | B     |      |
| M11-04 | Build workload-capacity gap analysis — combine project management data with burnout signal: "this team has 340 hours committed vs 280 hours capacity. Gap concentrated in two projects." Value-anchor: enterprise audit §4 identifies workload-burnout correlation as the primary commercial differentiator. | enterprise audit §4 | B     |      |
| M11-05 | Build closed-loop remediation tracking — create remediation task, assign ownership, track completion, measure whether burnout signal improved. Value-anchor: enterprise audit §4 — detection-only products churn; closed-loop is renewal driver.                                                             | enterprise audit §4 | B     |      |
| M11-06 | Build manager action templates — curated peer-manager actions with measured outcomes: "three actions peer managers took in similar situations." Value-anchor: enterprise audit §4 — managers need actionable steps, not dashboards.                                                                          | enterprise audit §4 | B     |      |
| M11-07 | Build predictive exit risk correlation — correlate burnout signals with actual departure data from HRIS. Requires longitudinal data from Sprint 1. Value-anchor: enterprise audit §4 — turnover cost is the most compelling ROI metric for buyers.                                                           | enterprise audit §4 | B     |      |
| M11-08 | Build calendar/email analytics integration — Microsoft Graph / Google Workspace for after-hours work, meeting overload. Sprint 2 scope — requires privacy framework for behavioral data. Value-anchor: enterprise audit §4 — behavioral signals upgrade classification to richer model.                      | enterprise audit §4 | B     |      |

---

## Value-Ranked Top 3 (Forest vs Trees Check)

Per `rules/value-prioritization.md` MUST-1, the three highest-value workstreams ranked by user-anchored rationale:

**1. Milestone 4 — Data Collection (HIGHEST VALUE)**
Anchor: D13 participation mechanisms + brief "workplace burnout detection and wellbeing scoring system."
Why: The product's bottleneck is not model accuracy — it is participation. The CBI and pulse are the training data. Without them the model has no input. The participation mechanisms (weekly pulse, monthly CBI, employee-first gate, SHAP content) are the four pillars of the 20%→40% participation ramp.
Shard-fit: Single session for CBI + pulse services, one session for participation tracking + notifications + suppression.

**2. Milestone 5 — ML Pipeline (HIGH VALUE)**
Anchor: product-identity.md §2-3 — "the scoring engine is the core capability."
Why: Everything else is packaging around the model. The two-threshold FN architecture (D14-9) and SHAP explainability are the product's technical moat. The cost-model.md economic rationale (senior FN costs 5x junior FN) drives the asymmetric thresholds.
Shard-fit: Three sessions sharded by autonomous-execution budget (training pipeline, calibration + SHAP + trajectory, bias audit + end-to-end wiring).

**3. Milestone 6 — Alerting & Intervention (HIGH VALUE)**
Anchor: enterprise audit §4 — "the action problem is unsolved. Detection-only is decorative."
Why: The enterprise audit's bottom line. A product that flags burnout without supporting action is a dashboard nobody uses. The human review gate, Organisational Risk Threshold, and SHAP-matched content library are the intervention loop.
Shard-fit: Two sessions (alerting services + content library, then wiring to dashboards).

Milestones 8 and 9 (compliance + testing) run in parallel with Milestones 5–7 — they do not block the build path but they block the launch.

---

## Dependency Graph

```
M1 (Foundation + Infrastructure)
 ├── M2 (Backend Infrastructure — Nexus, Auth, HRIS)
 │    ├── M3 (Consent & Onboarding)
 │    ├── M4 (Data Collection) ←─ independent of M3
 │    ├── M5 (ML Pipeline) ←─ M5-09 depends on M4 completion
 │    │    ├── M6 (Alerting & Intervention)
 │    │    └── M7 (Dashboards) ←─ depends on M5 + M6
 │    ├── M8 (Compliance) ←─ parallel with M5–M7
 │    └── M10 (Deployment) ←─ parallel with M5–M7
 └── M9 (Testing) ←─ after everything else exists
```

Critical path: M1 → M2 → M4 → M5-09 → M6 → M7
