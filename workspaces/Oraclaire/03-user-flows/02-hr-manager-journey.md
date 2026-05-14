# HR & Manager Journey — From Deployment Through Intervention

**Purpose:** Maps the complete HR administrator and people-manager experience. Every dashboard view, alert flow, and decision point.

---

## HR Administrator Journey

### Phase 1: Deployment Setup

#### Screen: Onboarding Checklist

HR admin completes deployment checklist before activation (per D14-5):

1. **Measure exclusion fraction (e):** Count employees in exclusion categories (PIP, ADA, FMLA, grievance cooldown). This must be the first step because it determines the scorable population.
2. **Configure jurisdiction:** Select applicable regulations (Singapore PDPA, EU AI Act, works council jurisdictions).
3. **Validate HRIS connection:** Test adapter (Workday / BambooHR / manual). Confirm seniority data flows correctly.
4. **Set seniority source:** Choose HRIS-derived (default) or self-reported. Per D15-1, self-reported is fallback only.
5. **Confirm participation targets:** Sprint 1 target (20%), architectural target (40%).

Each step must be completed before activation. No partial deployments.

#### Screen: Deployment Parameters

Configurable parameters (stored in deployment parameter store, per M1-06):

| Parameter                             | Default      | Configurable |
| ------------------------------------- | ------------ | ------------ |
| Grievance cooldown (days)             | 90           | Yes          |
| Auto-flag ceiling (%)                 | 20           | Yes          |
| Auto-flag trigger (consecutive weeks) | 2            | Yes          |
| Participation target Sprint 1         | 20%          | Yes          |
| Participation target architecture     | 40%          | Yes          |
| Seniority default source              | HRIS-derived | Yes          |
| Data retention (months)               | 12           | Yes          |

---

### Phase 2: Ongoing HR Dashboard

#### Screen: HR Dashboard — Org Overview

**Always-visible summary cards:**

- Organisation-wide burnout trend (line chart by team/department over cycles)
- Participation rate: current cycle, trend against 20%/40% targets
- Exclusion count summary at category level: "47 outside scoring window: 12 on leave, 23 protected process, 12 grievance cooldown"
- Pending Critical reviews count (if any)
- Systemic risk indicator: number of teams above auto-flag ceiling

**Data source:** All aggregate. No individual employee names visible on the main dashboard.

#### Screen: Participation Drill-Down

- Participation rate by team (bar chart)
- Participation trend over time (line chart, last 6 cycles)
- Alert banner when participation falls below 20% for two consecutive cycles
- Teams approaching minimum team size (fewer than 7 members — early warning before hitting the 5-member floor)

#### Screen: Exclusion Summary

- Category-level counts (NOT employee names):
  - Medical leave: N employees
  - Active intervention program: N employees
  - PIP: N employees
  - Disciplinary review: N employees
  - ADA/FMLA/workers comp: N employees
  - Grievance cooldown: N employees
- Historical trend: how exclusion population changes over time
- Note: "Excluded employees are not counted in participation rate denominators."

#### Screen: Org Trends by Team

- Team-level aggregate scores over time (selectable by department/team)
- Teams above auto-flag ceiling highlighted in orange/red
- Trend direction indicators (improving / stable / worsening)

---

### Phase 3: Critical-Tier Human Review

#### Trigger

When an employee receives a Critical-tier classification, the alert enters a pending_review state. No automatic escalation.

#### Screen: Critical Review Queue

- List of pending Critical reviews, each showing:
  - Employee identifier (anonymised code, not name — unless HR policy requires names)
  - SHAP decomposition: top contributing factors with relative impact
  - Trajectory across cycles: improved / held / worsened / first assessment
  - Time in queue (SLA tracking)
- **No auto-escalation without human action.**

#### Screen: Individual Critical Review

- Full SHAP breakdown with plain-language explanations
- Historical trajectory chart
- Two action buttons:
  - **Approve:** Release intervention. HR proceeds with outreach using SHAP context.
  - **Override:** Change tier classification. **Requires reason text** (free-text field, minimum 20 characters). Override reason is stored for audit trail.

#### After Review

- If approved: intervention workflow begins. Employee is NOT notified of the Critical classification directly — HR initiates conversation using their own judgment.
- If overridden: classification changes. Override reason permanently stored.

---

### Phase 4: Organisational Risk Threshold

#### Trigger

When a team's combined High+Critical rate exceeds the auto-flag ceiling (default 20%) for:

- Two consecutive weekly pulses, OR
- A single quarterly CBI cycle

#### What Happens

1. **Individual alerts suppressed for that team.** No more individual High/Critical flags visible for this team.
2. **Single organisational risk report generated.**
3. Individual alerts remain suppressed until the rate drops below the ceiling.

#### Screen: Organisational Risk Report

- Team name and department
- Combined High+Critical rate (e.g., "28% — above 20% ceiling")
- Duration of elevation (e.g., "Elevated for 3 consecutive pulse cycles")
- Recommended systemic actions (NOT individual employee names):
  - "Review workload distribution across the team"
  - "Consider team-level intervention (workshop, workload audit)"
  - "Schedule follow-up pulse in 2 weeks to monitor trend"
- Historical context: previous organisational risk events for this team

---

### Phase 5: Compliance & Reports

#### Screen: Compliance Dashboard

- Jurisdiction status (PDPA / EU AI Act / works council)
- Data retention status (next scheduled deletion date)
- Data subject rights requests (view/export/delete) — count and status
- Conformity assessment status
- DPIA status

#### Screen: Bias Audit

- Last audit date
- Tier distribution per demographic slice
- Flagged disparities (>10pp deviation from population mean in Critical+High rate)
- Export for customer compliance review

---

## People Manager Journey

### Phase 1: Dashboard Access

#### Prerequisites

- Manager must have a team with ≥5 contributing members. If team size < 5, the dashboard shows: "Team aggregate requires minimum 5 members. Current contributing members: N."
- Manager sees ONLY teams they manage. No cross-team visibility.

### Phase 2: Manager Dashboard

#### Screen: Team Overview

- **Team aggregate burnout trend** (line chart over last 6+ cycles)
  - Green zone: Low+Moderate dominant
  - Amber zone: High trending upward
  - Red zone: above auto-flag ceiling
- **Team trajectory:** improved / held / worsened
- **Minimum team size indicator:** "N of 5 minimum members contributing"

#### Screen: Team Action Recommendations

- Recommendations matched to team's top SHAP factors (aggregated):
  - "Your team's top burnout driver appears to be [workload]. Recommended actions: [peer-manager actions with measured outcomes]."
  - "Three actions peer managers took in similar situations: [action 1], [action 2], [action 3]."
- **No individual employee names or scores visible. Ever.**
- Recommendations come from SHAP-matched content library, not from HR.

#### Screen: Intervention Prompt (When Triggered)

- If team has High-tier concentration (or auto-flag triggered):
  - "Your team's aggregate score suggests elevated burnout risk. Consider scheduling a team check-in or contacting HR for support resources."
  - Direct link to HR contact (not to individual data)
  - Recommended peer-manager actions

### What Managers Do NOT See

- Individual employee names, scores, or SHAP breakdowns
- Critical-tier alerts (those go to HR only)
- Withdrawal notifications
- Exclusion categories for specific employees
- HR dashboard data (org-wide trends, participation rates, compliance status)

---

## Alert Flow Summary

```
Scoring cycle closes
├── Employee score → employee sees own results immediately
│                      HR sees after 24h delay
│
├── Critical tier → held in pending_review state
│                   HR reviewer sees SHAP context
│                   HR approves or overrides (with reason)
│                   Employee never sees review process
│
├── High/Critical combined > 20% ceiling (2 consecutive weeks)
│                   → individual alerts suppressed for that team
│                   → organisational risk report generated for HR
│                   → manager sees team-level action recommendations
│
└── Participation < 20% (2 consecutive cycles)
                    → alert on HR dashboard only
                    → no employee or manager visibility
```

---

## Data Visibility Matrix

| Data Point                 | Employee            | Manager                     | HR Admin                   | System            |
| -------------------------- | ------------------- | --------------------------- | -------------------------- | ----------------- |
| Own risk tier              | Yes (own only)      | No                          | Yes (Tier 1 opted-in only) | Yes               |
| Own SHAP breakdown         | Yes (own only)      | No                          | Yes (for Critical review)  | Yes               |
| Team aggregate             | No (unless manager) | Yes (own teams, ≥5 members) | Yes (all teams)            | Yes               |
| Individual scores (others) | No                  | No                          | Yes (Tier 1 only)          | Yes               |
| Exclusion categories       | No                  | No                          | Counts only (no names)     | Yes               |
| Critical review queue      | No                  | No                          | Yes                        | Yes               |
| Participation rates        | No                  | No                          | Yes                        | Yes               |
| Organisational risk report | No                  | No                          | Yes                        | Yes               |
| Withdrawal events          | No                  | No                          | No (per D15-3)             | Yes (suppression) |
| Bias audit results         | No                  | No                          | Yes                        | Yes               |
