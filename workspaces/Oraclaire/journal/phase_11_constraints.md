# Phase 11 — Constraint Classification

# Oraclaire Burnout Risk Scorer

# Sprint 1

Date: 2026-05-14
Status: APPROVED (D29) — seven approved, two challenged and split, one citation corrected
Supersedes: prior phase_11_constraints.md (8H/4S structure)

---

## 1. Classification Table

| #   | Constraint                       | Hard/Soft | Regime or penalty shape                                                                                                                                                                                                                                                                                                                                                       | Cost rate source                                                                          |
| --- | -------------------------------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| 1   | FP rate ceiling — 15%            | SOFT      | Linear: $15 x N_FP per cycle. Pre-registered target overridden to 16.6% in D26 — proof it is crossable at cost                                                                                                                                                                                                                                                                | D2: "$15 per unnecessary HR check-in per employee"                                        |
| 1b  | FP decay threshold — 20%         | HARD      | Physical product viability limit (not legal). Participation-feedback-loop: at FP > 20%, decay begins (D5). At FP > 30%, 40-60% drop by cycle 3. Product cannot function without participant data                                                                                                                                                                              | D5: "the product has destroyed its own data collection"                                   |
| 2a  | FN rate — general 15%            | SOFT      | Linear: $4,000 x N_FN_junior per year                                                                                                                                                                                                                                                                                                                                         | D3: "$4,000 per missed burned-out junior employee per year"                               |
| 2b  | FN rate — senior 10%             | SOFT      | Linear: $21,000 x N_FN_senior per year                                                                                                                                                                                                                                                                                                                                        | D3: "$21,000 per missed burned-out senior employee per year" (citation corrected per D29) |
| 3a  | Critical tier calibration signal | HARD      | Internal product health limit (D14 Parameter 7). If Critical fires above 5%, the model is miscalibrated or the deployment population is not representative. Named physical fact: "above 5% Critical the model's probability calibration is inconsistent with the D14 design intent." Response is model review, not more reviewers                                             | D14 Parameter 7 — design intent                                                           |
| 3b  | Reviewer queue capacity          | SOFT      | Dollar penalty per hour of delay per unreviewed Critical flag beyond REVIEW_TIMEOUT_HOURS (48h). Operational constraint the solver can optimise against                                                                                                                                                                                                                       | NOT in cost model — unvalidated                                                           |
| 4   | Human review gate                | HARD      | EU AI Act Annex III point 4 (employment), Article 14 (human oversight). Article 14(4)(e): ability to override output. Non-compliance: Article 71 (up to EUR 20M or 4% global turnover). Demotion impossible: statutory obligation for all EU deployments                                                                                                                      | Statutory — EU AI Act                                                                     |
| 5   | Minimum team size — 5            | HARD      | GDPR Article 5(1)(c) data minimisation + Article 32 security of processing. n=5 implements k-anonymity preventing re-identification from aggregate statistics. The number is a product choice; the principle (no re-identifiable aggregates) is statutory                                                                                                                     | GDPR Article 5(1)(c), Article 32                                                          |
| 6a  | Consent — EU/GDPR                | HARD      | GDPR Article 9(1) prohibits processing health data without Article 9(2) exception. Burnout risk scores are health-adjacent (mental fatigue, stress). Opt-in: Article 9(2)(a) explicit consent. Withdrawal: Article 7(3). 48-hour cooling-off (D15-3) is a product safeguard beyond statutory minimum                                                                          | GDPR Article 9 + Article 7                                                                |
| 6b  | Consent — Singapore/PDPA         | HARD      | PDPA Part IV (Sections 13-14) requires consent for collection, use, disclosure. Deemed-consent (Section 15) offers broader pathways than GDPR but consent remains mandatory                                                                                                                                                                                                   | PDPA Part IV                                                                              |
| 6c  | Consent — US                     | SOFT      | No federal general privacy law. No statutory opt-in for employment data. CCPA/CPRA provides opt-out for sale/sharing, not opt-in for employment processing. Contractual and ethical obligation only. NOTE (D29): California CPRA treats health data as sensitive personal information with opt-in requirements — flag as deployment-time check for California-based customers | D11: "litigation exposure and product credibility risk" — qualitative only                |
| 7a  | Retention — maximum principle    | HARD      | GDPR Article 5(1)(e). Data cannot be retained longer than necessary. The principle is hard. The value is not                                                                                                                                                                                                                                                                  | GDPR Article 5(1)(e)                                                                      |
| 7b  | Retention — 12-month default     | SOFT      | Operational choice within the hard principle. DPA review determines what "necessary" means for quarterly burnout trend tracking. Until review completes, 12 months is a conservative default — likely compliant but not confirmed. Penalty: dollar per employee record retained beyond DPA-approved period. DPO review package Appendix B open question 2                     | NOT in cost model — DPA review required                                                   |
| 8a  | No HRIS integration — AUP        | HARD      | Contract law (Acceptable Use Policy). Every customer signs the AUP. Integration with performance management is a breach of contract. Not statutory — voluntary contractual hard constraint                                                                                                                                                                                    | Contract — AUP                                                                            |
| 8b  | No HRIS integration — technical  | N/A       | Product architecture choice (no HRIS write API in serve.py). Not a constraint classification — implementation detail that prevents accidental AUP violation                                                                                                                                                                                                                   | N/A — architecture, not constraint                                                        |
| 9   | Organisational Risk Threshold    | SOFT      | Step function reflecting two-consecutive-weeks design (D15-2). Week 1 above 20%: penalty = 0 (transient spike tolerance). Week 2 consecutive above 20%: full penalty activates. System switches from individual alerts to organisational risk report. Penalty = suppressed-individual-alert opportunity cost + organisational response cost                                   | NOT in cost model — unvalidated                                                           |

---

## 2. Infeasibility Check

The four constraints named — human review gate (HARD), GDPR consent (HARD), Critical calibration signal (HARD per D29), minimum team size (HARD) — produce **no LP infeasibility**. The hard constraints do not conflict:

- C4 (human review) fires on individual Critical flags regardless of team size. Always satisfiable given reviewer capacity.
- C6a EU (GDPR consent) limits who can be individually scored. Satisfiable: only opted-in employees receive scores.
- C5 (minimum team size 5) suppresses aggregates for teams below threshold. Satisfiable: suppression IS the enforcement mechanism.
- C3a (Critical calibration 5%) is HARD per D29. If Critical exceeds 5%, response is model review, not reviewer scaling.

**Small-team edge case (team of 4, all opt in):** aggregates suppressed per C5 (satisfied). Individual Critical flags reviewed per C4 (satisfied). Consent per C6a (satisfied). No hard constraint violated. The small-team scenario produces a product experience with no HR visibility (aggregate suppressed at n<5) and Critical flags visible to reviewer only. The product still functions — it provides less organisational insight for small teams. This is expected behaviour, not an infeasibility (D29).

**Product viability concern (not LP infeasibility):** if opt-in rates are low, many teams fall below MIN_TEAM_SIZE, aggregates are widely suppressed, and the product's value proposition degrades. This is a business risk, not a mathematical infeasibility. The LP remains feasible; the solution space may be empty of commercially useful solutions.

---

## 3. Unvalidated Cost Terms

The following cost terms are NOT in the Oraclaire cost model and CANNOT enter the objective function until validated:

1. **Reviewer cost** — cost per Critical flag review (30-minute HR check-in). No dollar figure in any decision log. Flagged as unvalidated since Phase 10.

2. **Assessment cost** — cost per assessment cycle (platform, administration, opportunity). No dollar figure in any decision log. Flagged as unvalidated since Phase 10.

3. **Disparate impact** — D11 describes "litigation exposure and product credibility risk" — qualitative only. No dollar figure exists. Cannot be expressed as a penalty term without a validated cost anchor.

4. **ORT organisational response cost** — the penalty that activates when ORT fires (week 2 consecutive above 20%). The cost of switching from individual alerts to organisational reporting is not quantified.

These four terms appear as cost terms in the Phase 10 objective function but carry no grounded dollar values. The LP can be formulated with placeholder variables, but the solver output is ungrounded until the founder provides cost anchors.

**Phase 12 instruction (D29):** Run the solver with placeholder values for reviewer cost and assessment cost explicitly flagged as [UNVALIDATED — FOUNDER TO CONFIRM]. The LP output is directionally useful — it shows the structure of the optimal plan. Absolute cost numbers are unreliable until placeholders are replaced. All cost calculations involving reviewer cost or assessment cost are directional only. Replace placeholders before using Phase 12 output for any customer-facing cost justification.

---

## 4. Regulatory Injection Protocol

No regulatory injection has fired in this session.

If a regulatory event fires post-classification:

1. Create NEW file: `workspaces/Oraclaire/journal/phase_11_post_[event].md`
2. Do NOT overwrite this file.
3. Re-classify affected constraints. Show before/after table:

| Constraint | First-pass | Post-injection | Regime change |
| ---------- | ---------- | -------------- | ------------- |

4. State explicitly: "Phase 12 must re-solve. config.py must differ from the pre-injection state. If config.py is byte-identical — the solver did not pick up the new hard constraint. Writing the post-injection journal without updating config.py is a decision log failure."

---

## 5. For Discussion

1. C1b (FP decay threshold 20%) is HARD as a physical limit. Is this the right LP classification, or should it be SOFT with an extreme penalty that lets the solver approach asymptotically?

2. C5 (min team size) n=5 is a product choice implementing k-anonymity. Should n be configurable per deployment with DPA sign-off on the chosen k?

3. C3a is HARD as a model calibration signal. What operational procedure fires when Critical exceeds 5% — model retrain, threshold adjustment, or deployment pause?

---

Phase 11 approved (D29). Changes applied: C3 split into C3a (hard) + C3b (soft), C7 split into C7a (hard) + C7b (soft), C2b citation corrected D4→D3, California CPRA note added to C6c, Phase 12 placeholder instruction added. Ready for Phase 12.
