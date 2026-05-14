# Population and Scoring — Who Gets Scored and How

**Authority:** This spec is the single source of truth for population definition, scoring tiers, exclusions, consent mechanics, and participation implications. Every decision about who appears in the model's input and output resolves here.

**Origin:** Phase 1 Frame section 2, Decision 1 (journal/0001), Challenge 3 (journal/0006).

---

## 1. Two-Tier Scoring Model

Oraclaire implements a two-tier scoring model. Every employee falls into exactly one tier at any given time. The tier determines what data is generated, who can see it, and how it is used.

### Tier 1 — Individual Scoring (Opt-In Only)

Employees who actively opt in through the Oraclaire consent screen during onboarding receive individual-level burnout risk scores (Low / Moderate / High / Critical).

**Consent properties:**

- Opt-in is explicit and informed — employees see what data is collected, how it is used, and who can see their score before consenting.
- Consent is given per employee, not delegated by manager or HR.
- The consent screen must present all three disclosures (data collected, usage, visibility) before the opt-in action is available.

**Withdrawal mechanics:**

- Withdrawal has a 48-hour cooling-off period — the employee submits a withdrawal request, and has 48 hours to cancel. During this window the employee sees a countdown and a cancel button. After 48 hours, suppression takes effect automatically. (Locked D15-3, journal/0014.)
- After suppression: individual scores are hidden from everyone, including the employee's own history view. Not just from HR. From everyone.
- No retroactive re-activation — withdrawal clears visibility; re-opting-in starts fresh with no access to previously suppressed scores.
- Withdrawal is available at any time, through the same interface used for opt-in.
- No HR or manager notification is sent when an employee withdraws. (Locked D15-3.)

**Who sees Tier 1 scores:**

- The employee themselves (until withdrawal).
- HR, for intervention routing (see `regulatory-constraints.md` for human oversight requirements on Critical tier).
- Managers do NOT see individual scores directly — intervention routing goes through HR.

### Tier 2 — Team Aggregate Only (Default)

Employees who have not opted in appear only in team-level aggregate scores. This is the default state for all employees at initial onboarding.

**Aggregate rules:**

- Minimum team size: 5. If fewer than 5 members have data contributing to the aggregate, the aggregate score is suppressed entirely. A team of 4 produces no visible output.
- HR sees team trends only — no individual-level data for Tier 2 employees, ever.
- Tier 2 employees see nothing — they do not see scores (individual or aggregate) unless they opt in to Tier 1.

**Suppression edge cases:**

- If a team of 5 loses a member (drops to 4), the current cycle's aggregate is suppressed. Historical aggregates from when the team was 5 remain visible. (This is the default behavior; founder may choose retroactive suppression — see Open Questions.)
- If a Tier 1 employee withdraws and the team drops below 5 contributing members, the aggregate is suppressed going forward.

---

## 2. Explicit Exclusions — Operational

The following categories are excluded from scoring entirely (both Tier 1 and Tier 2). They do not appear in any output, aggregate, or model input.

| Exclusion                                                                                        | Rationale                                                                                                                                       |
| ------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Test accounts and API-generated submissions                                                      | Non-human data would corrupt the model                                                                                                          |
| Employees currently on medical leave (including mental health leave)                             | Scoring someone on medical leave is both unethical and methodologically invalid — their current state reflects treatment, not workplace burnout |
| Employees already flagged and receiving active support through a structured intervention program | Redundant scoring during active intervention creates confusion and duplicate alerts                                                             |
| Contractors and temporary staff without a defined assessment pathway                             | No employment relationship to support burnout intervention; inclusion creates data without actionability                                        |

**Detection:** These exclusions require HRIS integration to enforce automatically. Without HRIS integration, manual enforcement is required, which introduces human error. (See `product-identity.md` section 5 for HRIS dependency.)

---

## 3. Explicit Exclusions — Legal-Safety

These exclusions are not compliance afterthoughts. They are population definitions that change FN/FP arithmetic. A score generated in these contexts creates discoverable data in employment disputes.

Employees in the following categories are excluded from individual scoring entirely — not because the model cannot score them, but because a score in these contexts creates legal liability the product did not intend.

| Exclusion                                                                                                | Rationale                                                                                                                                                                                                                                                    |
| -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Employees currently on a Performance Improvement Plan (PIP)                                              | A burnout score during a PIP will be subpoenaed. It becomes evidence for either side: employer ("they were burned out, not discriminated against") or employee ("the company knew and took adverse action anyway"). Either way, the score creates liability. |
| Employees under active disciplinary review                                                               | Same discoverable-data risk as PIP.                                                                                                                                                                                                                          |
| Employees in a protected category process: ADA accommodation, FMLA leave, or workers' compensation claim | A score generated during an ADA accommodation process or FMLA leave is directly relevant to the employment dispute and will be demanded in discovery.                                                                                                        |
| Employees who have filed a workplace complaint or grievance within the last 90 days (cooldown window)    | The cooldown window prevents a recently filed grievance from being inflamed by a burnout score. The 90-day window is a default assumption; legal counsel may recommend a different window.                                                                   |

**Key implications:**

- The excluded population includes burned-out employees. Employees on PIPs are often burning out — that is frequently why performance dropped. Excluding them means the model has a systematic blind spot for a high-risk sub-population. The FN rate on this sub-population is 100% (they are never scored). This affects the cost model — see `cost-model.md` section 1.
- Suppression from HR view is insufficient. Suppression from the UI does not prevent the data from existing in the database. A subpoena reaches the database, not the UI. The data must not be generated in the first place.
- These exclusions require HRIS integration to detect who is on a PIP, who filed a grievance, etc. Without HRIS, manual enforcement is the only option.

**Interaction with cost model:** Legal-safety exclusions remove high-risk employees from the scorable population. This means:

1. The model's training data systematically under-represents employees under active management processes.
2. The FN dollar exposure in `cost-model.md` is calculated on the scorable population only — the true organizational cost of burnout is higher because the highest-risk subset is excluded by design.

---

## 4. Participation Implications

The two-tier structure means FN/FP arithmetic splits into two populations:

- **Tier 1 (opted-in):** Individual scores, individual FN/FP. This population is smaller and noisier, especially early in deployment when opt-in rates are low.
- **Tier 2 (aggregate):** Team-level FN/FP. Individual outcomes are invisible; model performance is measured at the aggregate level.

**Two-threshold FN architecture (locked D14-9):** The model applies separate FN/FP targets per tier: general population FN ≤ 15%, FP ≤ 15%; senior tier FN ≤ 10%, FP ≤ 20%. The seniority_tier field routes each employee to the correct threshold. See `cost-model.md` section 4 for the full parameter table.

**Participation rate targets (locked D7, D14):** 20% sustained participation for Sprint 1, 40% sustained for architectural target over 12 assessment cycles. Below 40%, the sample is no longer representative. Below 30%, the model cannot reliably distinguish burnout signal from self-selection bias. The model needs longitudinal data (same employees across multiple cycles) for trajectory analysis — participation below 40% means insufficient repeat-participation. See `product-identity.md` section 4 for trajectory analysis.

**Participation denominator (locked D15-4):** Participation rate is calculated against the scoreable population only (total employees minus excluded). Excluded employees do not appear in the denominator. The HR dashboard shows the exclusion count separately at category level so HR understands the gap between total headcount and scoreable population.

**Participation decay risk:** False positives drive participation decay, which disproportionately removes burned-out employees from the training data. See `cost-model.md` section 2 for the full participation death spiral mechanism.

---

## 5. Parameters Locked by D14/D15

| Parameter                 | Value                                                      | Decision             |
| ------------------------- | ---------------------------------------------------------- | -------------------- |
| Withdrawal cooling-off    | 48 hours, automatic, no HR notification                    | D15-3 (journal/0014) |
| Seniority identification  | Configurable, HRIS-derived default, self-reported fallback | D15-1                |
| Participation denominator | Scoreable population only (excluded employees removed)     | D15-4                |
| Grievance cooldown        | 90 days (configurable via deployment parameter)            | D14                  |
| Two-threshold FN targets  | General ≤15% FN/≤15% FP; Senior ≤10% FN/≤20% FP            | D14-9                |

## 6. Open Questions Remaining

- [ ] If Tier 1 opt-in rate is below 20%, is individual-level scoring worth the engineering complexity, or should the product default to team-only?
- [ ] What happens when a team of 5 loses a member (drops to 4) — does historical aggregate data get retroactively suppressed?
- [ ] Should the system notify HR when an employee enters an exclusion category ("this employee was being scored and is now on a PIP — their historical scores must be purged")?
