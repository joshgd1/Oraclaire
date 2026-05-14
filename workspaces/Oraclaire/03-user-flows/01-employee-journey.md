# Employee Journey — From Opt-In Through Next Cycle

**Purpose:** Maps the complete employee experience from first contact through ongoing participation. Every screen, data flow, and decision point.

---

## Journey Overview

```
Onboarding → Opt-In → Weekly Pulse → Monthly CBI → Score Generated →
Employee Sees Results (24h before HR) → SHAP Recommendations →
Next Pulse/CBI → Trajectory Tracking
```

---

## Phase 1: Onboarding & Opt-In

### Entry Point

Employee receives invitation link (email or Slack/Teams integration from HR admin).

### Screen 1: Welcome & Disclosure

- **What they see:** Plain-language introduction to Oraclaire
  - "Oraclaire helps your organisation understand team wellbeing. It is NOT a performance tool."
  - Three disclosures presented sequentially before any action is available:
    1. **Data collected:** "We collect burnout survey responses (19 questions monthly, 1 question weekly). No calendar, email, or browsing data."
    2. **How it's used:** "Responses are analysed by an AI model that classifies burnout risk into four levels: Low, Moderate, High, Critical. Your manager sees team averages only (never your individual score). HR may see your individual score only if you opt in."
    3. **Who can see what:** "You always see your own results. Your manager sees team trends only (minimum 5 people). HR sees aggregated trends. No data is ever exported to performance management systems."
- **Controls:** "Learn more" expands each disclosure into detail. All three must be expanded before opt-in button activates.

### Screen 2: Seniority Selection (if self-reported)

- **When shown:** Only when HRIS integration is absent and seniority_source is `self_reported` (per D15-1).
- **What they see:** Single question: "Which best describes your role?"
  - Options: "Individual Contributor / Junior" | "Senior / Lead / Manager"
  - Plain-language explanation: "This helps us calibrate the model appropriately for your career stage. Your selection is not visible to your manager."
- **One question. No clinical language.**

### Screen 3: Opt-In Confirmation

- **What they see:** Confirmation screen with timestamp.
- **What happens:** `consent_status` → `opted_in`, `consent_timestamp` recorded, `seniority_tier` recorded.
- **Data stored:** Employee record updated. Employee is now Tier 1 (individually scorable).

### If Employee Declines

- No opt-in button pressed → employee remains Tier 2 (team aggregate only).
- They see nothing further. No reminders. No nudges. No guilt language.
- They can opt in later through settings.

---

## Phase 2: Weekly Pulse (Ongoing)

### Trigger

Once per week, employee receives a single notification (email/push/in-app).

### Screen: Pulse Question

- **What they see:** One CBI item, selected by rotation schedule (D13 mechanism A). Example: "How often do you feel emotionally drained by your work?"
- **Response:** 5-point Likert scale (Always / Often / Sometimes / Seldom / Never). One tap to respond.
- **Time:** ~10 seconds.
- **Save-on-response:** Each response is stored immediately (partial completion not applicable — single item).
- **Visibility:** Employee sees own pulse trend chart (last 12 weeks). No team/HR visibility for pulse responses.

### What Happens Behind the Scenes

- Response stored with `cycle_id` (pulse type).
- Aggregated at team level for population-level signal.
- No individual pulse score visible to HR or managers.

---

## Phase 3: Monthly CBI (Full Assessment)

### Trigger

Once per 30 days, employee receives notification for full CBI assessment.

### Screen: CBI Assessment

- **What they see:** 19-item Copenhagen Burnout Inventory, presented one screen at a time or in groups.
- **Progress indicator:** "Question 5 of 19" with visual progress bar.
- **Save-on-each-response:** Partial progress preserved. Employee can resume if they close the browser.
- **Previous scores:** Employee sees own previous cycle scores for comparison (if they have prior cycles).
- **Time:** ~5–8 minutes.

### Submission

- Employee submits completed assessment.
- `cycle_id` links to the current monthly cycle.
- Scoring pipeline is triggered when the cycle closes (not on individual submission).

---

## Phase 4: Scoring & Results

### Cycle Close

- Admin (or scheduled job) closes the assessment cycle.
- Scoring pipeline runs: exclusion filter → model inference → two-threshold calibration → SHAP decomposition → risk tier classification.

### Employee-First 24-Hour Gate (D13 mechanism C)

- After scoring completes, employee data is immediately visible to the employee.
- HR access to cycle results is delayed by 24 hours (hardcoded, not configurable).
- **Why:** Employee sees their own data before anyone else can act on it. No surprises.

### Screen: My Results

- **What they see:**
  - Current risk tier with colour-coded indicator (Low = green, Moderate = amber, High = orange, Critical = red).
  - SHAP breakdown: "Your score was primarily influenced by [exhaustion level] and [cynicism level]." Plain language, no ML jargon.
  - Trajectory: improved / held / worsened compared to last cycle.
  - Pulse trend chart (last 12 weeks).
- **What they do NOT see:** Other employees' scores. Team aggregates (unless they're also a manager). Any HR-facing data.

### Screen: SHAP-Matched Recommendations

- **What they see:** 2–3 curated resources matched to their top SHAP factors.
  - Low tier: self-guided resources (articles, exercises, self-assessment tools).
  - Moderate tier: team resources (workload rebalancing guides, team wellness activities).
  - High tier: professional pathways (EAP, counselling options, manager conversation guides).
  - Critical tier: professional pathways with urgency (immediate support resources, crisis contacts).
- **What they do NOT see:** "Your manager has been notified" or any HR action language.

---

## Phase 5: Ongoing Participation

### Weekly Pulse Continues

- Single-question pulse every week. Employee sees their own trend building over time.

### Next Monthly CBI

- After 30 days, next full assessment. Employee sees trajectory (improved/held/worsened).

### Participation Tracking (Invisible to Employee)

- System tracks participation rate against 20% Sprint 1 target and 40% architectural target.
- If participation drops below 20% for two consecutive cycles, HR dashboard shows alert — employee never sees this.

---

## Phase 6: Withdrawal (At Any Time)

### Entry Point

Employee navigates to Settings → Data & Privacy → Withdraw Consent.

### Screen: Withdrawal Request

- **What they see:**
  - Clear statement: "You are requesting to withdraw from individual burnout risk scoring."
  - 48-hour countdown display.
  - Cancel button prominently displayed.
  - Confirmation message: "Your withdrawal request has been received. Your individual data will stop being collected in 48 hours. You can cancel this request any time before then."
- **No guilt language.** No "are you sure?" No "your team needs you." No HR notification.

### After 48 Hours

- All individual scores suppressed from all viewers (employee, HR, managers).
- Employee appears only in team aggregates (if team size ≥ 5).
- Re-opting-in starts fresh — no access to previously suppressed scores.

---

## Phase 7: Data Ownership Controls (At Any Time)

### Screen: My Data

- **View:** See all individual data (assessment responses, risk scores, SHAP decompositions).
- **Export:** Download as JSON. One click.
- **Delete:** Immediate hard delete of all individual data. No 48-hour cooling-off (different from withdrawal — this is GDPR/PDPA right to erasure, not consent withdrawal).

---

## Edge Cases

| Scenario                                            | Employee Experience                                                                                                |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Employee enters exclusion category (PIP, grievance) | Invisible to employee. They simply don't receive assessment prompts while excluded.                                |
| Team drops below 5 members                          | Employee still sees own results. Team aggregate suppressed from manager view.                                      |
| Employee opts in, no CBI cycle open                 | Sees "Next assessment opens [date]" and can view historical results.                                               |
| Employee is also a manager                          | Sees employee view (own data) AND manager view (team aggregate) as separate dashboards.                            |
| Critical-tier score with human review               | Employee sees their Critical result. They do NOT see the HR review process.                                        |
| Organisation auto-flag triggered                    | Employee experience unchanged. HR receives organisational risk report; individual alerts suppressed for that team. |
