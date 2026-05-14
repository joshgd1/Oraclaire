# Appendix A — Lessons Learned

---

## Oraclaire Sprint 1 — Workplace Burnout Detection

### Transferable Lessons

---

LESSON T1 — Pre-registration after seeing the leaderboard is rationalisation, not constraint
Type: TRANSFERABLE
Learned in: Phase 6 pre-registration (D17), Phase 8 gate review

**Lesson:** Pre-registered floors written after the model is selected and its metrics are known protect against _some_ motivated reasoning (they prevent changing the floors to accommodate a future failure) but they cannot protect against _the_ motivated reasoning that occurred when the floors were written — the FP ceiling of 15% was set knowing the model's FP was 20.1%, and the pre-registration disclosure documented this honestly but did not prevent the tension from arising in the first place.

**Why it transfers:** Any ML product that pre-registers evaluation criteria after model selection faces the same structural weakness — the criteria author has seen the model's strengths and biases whether they acknowledge it or not. This applies to fraud detection (pre-registering precision floors after seeing the confusion matrix), recommendation systems (setting diversity thresholds after measuring homogeneity), and any domain where evaluation criteria are authored by someone who has seen the leaderboard.

**Cost of ignoring it:** Without explicit disclosure that pre-registration occurred after model selection, the gate journal would have presented the 15% FP ceiling as an independent constraint — when in fact it was negotiated against a model that was already failing it. The honest disclosure is the minimum defense; the stronger defense is pre-registering before Phase 4. Cost if undisclosed: the gate passes on paper while the team knows the floor was set to be passable — the gate becomes theatre.

**Near-miss prevented:** The Phase 8 gate table honestly reported FP ceiling as FAIL with accepted override. Without the disclosure discipline from Phase 6, this failure could have been retroactively justified as "within acceptable range" without documenting the override.

**Sprint 2 application:** Sprint 2 introduces behavioral features and potentially re-evaluates the model family. Pre-registration for Sprint 2 floors must be written _before_ the Sprint 2 leaderboard is read — not after. The Sprint 2 pre-registration should explicitly state whether the author has seen any Sprint 2 model metrics.

---

LESSON T2 — SHAP concentration validated on a small sample is a hypothesis, not a finding
Type: TRANSFERABLE
Learned in: Phase 4 (12-row MFS SHAP 19.4%), Phase 7 full-dataset re-run (22,750-row MFS SHAP 46.9%), D24 RE-DO

**Lesson:** SHAP feature importance validated on fewer than 1,000 rows should be treated as a hypothesis that requires full-dataset confirmation — the 12-row sample showed mental_fatigue_score at 19.4% SHAP importance (well below the 40% gate), while the full 22,750-row dataset revealed 46.9% (above the gate, requiring a model RE-DO with new interaction features `tenure_fatigue` and `tenure_workload` to reduce MFS dominance from 46.9% to 29.9%).

**Why it transfers:** Any ML product that validates feature importance, fairness metrics, or concentration risk on a sample or development subset faces this failure mode — a fraud model validated on 500 transactions may show no concentration on the merchant_id feature, while the full 10M-transaction production dataset reveals that one merchant category drives 60% of predictions. A recommendation system validated on 1,000 users may show diverse feature usage that collapses when deployed to 10M users where a single popularity signal dominates. The failure mode is structural: small samples cannot reveal concentration because they do not contain the diversity edge cases that expose it.

**Cost of ignoring it:** A fatigue-dominant model would have shipped to production without the interaction features — every employee's SHAP waterfall would have been dominated by a single signal, blocking the D16 hard gate on SHAP waterfall display. The RE-DO required new feature engineering (`tenure_fatigue`, `tenure_workload`), re-validation of all floor checks, and a threshold re-evaluation spanning D24 through D26 — three decisions that would have been avoided if full-dataset SHAP had been checked at Phase 4 instead of Phase 7.

**Near-miss prevented:** The 40% MFS SHAP gate (pre-registered in D16) caught the failure on the full dataset. Without that gate, a model where one feature drives 46.9% of all predictions would have been deployed — and every employee-facing explanation would have said "your fatigue score determines your risk" with no nuance.

**Sprint 2 application:** Sprint 2 adds behavioral features (Jira/Linear/Asana integration per D10 Option 2). When these features are added, SHAP concentration must be validated on the _full_ Kaggle dataset (or the pilot customer's full population) — not on the 12-row sample. The same gate applies: no single feature above 40% SHAP importance.

---

LESSON T3 — Threshold adjustment is a symptom response; fix the model first
Type: TRANSFERABLE
Learned in: D24 (FP breach at 0.30), D25 (MFS RE-DO), D26 (threshold locked at 0.35)

**Lesson:** When a pre-registered FP or FN floor is breached, the first response should be investigating whether the model itself is miscalibrated or feature-concentrated — not adjusting the classification threshold to pass the floor — because the FP breach at 0.30 (20.1%) appeared to be a threshold problem but was actually caused by MFS SHAP dominance (46.9%), and fixing the model with interaction features reduced the FP rate without requiring the threshold to move as far as initially proposed (0.30 → 0.40), ultimately landing at 0.35 which was closer to the original threshold than the panic response would have been.

**Why it transfers:** Any ML product with a tunable classification threshold faces this trap — a spam filter with 25% FP looks like a threshold problem, but if one feature (email length) dominates predictions, raising the threshold just hides the concentration while degrading recall. A medical screening tool with high FP looks like it needs a higher cutoff, but if the model is overfit to a single biomarker, the threshold move masks the real failure. The threshold is the operating point on a curve; if the curve is wrong, moving the point does not fix the curve.

**Cost of ignoring it:** Without the RE-DO, threshold 0.40 would have been selected to pass the FP floor — missing 5 employees with Burn Rate ≥ 0.60 at a FN exposure of $20,000-$105,000 per year (D3 cost model: 5 × $4,000-$21,000). The model fix (interaction terms) reduced FP from 20.1% to a level where 0.35 was sufficient, keeping those 5 employees in the scored population.

**Near-miss prevented:** The band review condition in D25 ("confirm no BR ≥ 0.60 employees in 0.30-0.40 band") prevented a premature threshold move to 0.40 that would have excluded the highest-risk employees from the product.

**Sprint 2 application:** Sprint 2 may produce new FP/FN rates on the pilot customer's real data. If floors are breached, the first question is whether the model's feature composition is wrong for this population — not whether to adjust the threshold. The threshold is the last lever, not the first.

---

### Domain-Specific Lessons

---

LESSON D1 — Self-report burnout signals have adversarial non-response
Type: DOMAIN-SPECIFIC (LOCAL ONLY — DO NOT EXPORT TO OTHER DOMAINS)
Learned in: Phase 1 (D5 participation decay model), Phase 2 data audit

**Lesson:** The most burned-out employees are the least likely to complete a burnout assessment — creating systematic selection bias where the population that most needs the product is least represented in its training data, and this bias is _adversarial_ (not random) because the mechanism causing non-response (burnout itself) is correlated with the outcome the model is trying to predict.

**Why it does NOT transfer:** In domains where the signal is passively collected (transaction logs, sensor data, clickstream), non-response is not a mechanism — the data exists regardless of the subject's state. A credit card fraud model trains on transactions whether or not the cardholder is stressed. Only in wellbeing and mental health products does the act of measurement require the subject's active participation, and the subject's state directly affects their willingness to participate.

**Cost of ignoring it:** The training dataset has already filtered out employees who did not complete the survey — the model trains on completers only. At deployment, the same filter applies: the model can only score employees who consent and complete the CBI. If burned-out employees opt out at higher rates, the model's training distribution diverges from its deployment distribution, and the model systematically underestimates risk for the population that needs it most. The participation decay model (D5) quantifies this: above 20% FP, 40-60% of burned-out employees drop out by cycle 3.

**Near-miss prevented:** The FP ceiling of 15% (with 20% decay threshold) was set explicitly to prevent this mechanism from activating. Without that ceiling, the product could have shipped with a 25-30% FP rate — triggering the adversarial non-response spiral within the first two quarterly cycles.

**Sprint 2 application:** Sprint 2 behavioral features (Jira/Linear/Asana integration) partially address this lesson by providing passive signals that do not depend on survey completion. The Sprint 2 fairness audit must specifically test whether model performance degrades for employees who score high on burnout but low on survey completion willingness — this is the adversarial non-response signature.

---

LESSON D2 — The buyer's motivation and the user's need are structurally misaligned
Type: DOMAIN-SPECIFIC (LOCAL ONLY — DO NOT EXPORT TO OTHER DOMAINS)
Learned in: Phase 1 (D1 consent architecture, D2 FP cost model, D5 participation decay), Phase 8 (GO condition 2)

**Lesson:** In an employee wellbeing product, the employer pays to reduce turnover cost while the employee uses it for personal insight and early support — and if the product optimises for the buyer's motivation (detection accuracy, HR dashboard richness) at the expense of the user's need (privacy, individual agency, actionable personal guidance), participation collapses and the product's data quality degrades below the threshold where the buyer's ROI is achievable.

**Why it does NOT transfer:** In domains where the buyer and user are the same person (B2C SaaS, personal finance tools, consumer health apps), product decisions that serve the user automatically serve the buyer. In B2B products where the buyer and user share incentives (enterprise security tools — the CISO buys, the employee uses, both want fewer breaches), the alignment holds. The misalignment is specific to HR and wellbeing products where the buyer's ROI (reduced turnover) is structurally in tension with the user's autonomy (privacy from their employer).

**Cost of ignoring it:** The participation decay model (D5) showed that above 20% FP, participation drops 40-60% by cycle 3. At that point, the buyer's ROI collapses because there are insufficient assessments to produce reliable team-level aggregates. Ignoring the misalignment would mean shipping a product that the HR Director loves in the demo but that employees abandon after one cycle.

**Near-miss prevented:** The two-tier scoring architecture (D1) was adopted specifically because a single-tier model that gave HR direct access to individual scores would have produced immediate trust erosion. Without it, the product would have shipped as "employer surveillance of employee mental health" — fatal as a product.

**Sprint 2 application:** Sprint 2 behavioral features (passive signals from project management tools) increase the buyer's detection accuracy but also increase the surveillance surface. The Sprint 2 design must ensure that passive-signal features are subject to the same consent architecture as self-report features — or the buyer-user misalignment re-emerges through a new channel.
