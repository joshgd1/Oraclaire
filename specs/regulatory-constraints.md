# Regulatory Constraints — Legal and Compliance Architecture

**Authority:** This spec is the single source of truth for regulatory constraints that shape Oraclaire's architecture. Every compliance requirement, legal floor, and regulatory obligation resolves here.

**Origin:** Phase 1 Frame section 6 (Structural Constraints), Challenge 5 (journal/0008).

**Cross-references:**

- The two-tier scoring model that satisfies PDPA consent requirements is in `population-and-scoring.md` section 1.
- The 4-tier burnout risk classification that triggers human oversight at the Critical tier is in `product-identity.md` section 2.
- The SHAP interpretability mechanism that satisfies EU AI Act transparency is in `product-identity.md` section 3.

---

## 1. Singapore PDPA — Mental Health Data Hard Floor

### Scope

Singapore's Personal Data Protection Act (PDPA) imposes specific requirements on the collection, use, and disclosure of personal data, with heightened obligations around health data. Burnout indicators fall under health data because they are mental health inferences.

### Requirements

**Consent:**

- PDPA requires explicit, informed consent before collecting personal data.
- For health data (including mental health / burnout indicators), the consent bar is higher — the data subject must understand what is being collected and how it will be used.
- Consent under an employment relationship must be genuinely voluntary. PDPA treats employer-directed consent with skepticism.

**Collection limitation:**

- Only data necessary for the stated purpose may be collected.
- Oraclaire must be able to articulate exactly what data points are collected and why each one is necessary for burnout risk classification.

**Use and disclosure:**

- Data collected for burnout risk scoring cannot be repurposed for performance evaluation, promotion decisions, or disciplinary action without separate consent.
- Disclosure to third parties (insurers, external consultants) requires separate consent.

**Cross-border transfer:**

- If data is processed outside Singapore, PDPA requires that the receiving jurisdiction provides comparable data protection, or that contractual safeguards are in place.

### How Oraclaire Satisfies PDPA

The two-tier scoring model (see `population-and-scoring.md` section 1) is designed to satisfy PDPA's consent requirements:

- **Tier 1 (individual scoring) requires active opt-in.** Employees explicitly consent to individual-level burnout risk scoring. This is not opt-out — opt-out consent in an employment context is considered coerced under both PDPA and GDPR Article 7(4).
- **Tier 2 (aggregate only) requires no individual consent** because no individual-level data is generated or displayed. Team aggregates at minimum team size 5 are de-identified enough to avoid individual inference.
- **Withdrawal is immediate and complete.** PDPA requires that consent can be withdrawn. Oraclaire's withdrawal suppresses all individual scores from all viewers immediately.

### Status

PDPA is a structural compliance floor — it gates what data can be collected, how consent is obtained, and whether cross-border transfer is permitted. Detailed compliance specification belongs in Phase 2, but the architectural constraints (opt-in, withdrawal, de-identification) are embedded in the population model from Phase 1.

---

## 2. EU AI Act — High-Risk Employment AI

### Scope

Automated scoring in employment contexts is classified as a **high-risk AI system** under EU AI Act Annex III. This applies to any Oraclaire customer with EU-based employees — not just EU-headquartered companies. A Singapore-based company with 50 employees in Berlin is covered.

### Classification

Oraclaire is high-risk because it:

- Makes assessments that affect employment outcomes (burnout risk scoring used for intervention routing).
- Produces scores that influence workplace decisions (which employees receive HR outreach, intervention resources).
- Uses automated profiling to classify individuals into risk tiers.

### Requirements

#### Human Oversight for Critical Tier (Phase 1 Architectural Constraint)

**Hard constraint:** Oraclaire cannot produce a fully automated "Critical" burnout risk tier that triggers action without a human in the loop.

Specifically:

- Critical-tier flags must require a human review step before any intervention or escalation is triggered.
- The human reviewer must have the authority to override the model's classification.
- The human review step cannot be a rubber stamp — the reviewer must have access to sufficient context (SHAP explanations, contributing factors) to make an informed decision.
- This is not a Phase 2 compliance spec — it is a Phase 1 architectural constraint. The intervention workflow must be designed with a human gate at the Critical tier from day one.

**Why this was not deferred:** If the system is designed without this constraint and added later, the intervention workflow (Phase 3) must be redesigned. The human gate must be built into the escalation pipeline from the start.

**Why only Critical tier (not all tiers):** Requiring human review for every Low/Moderate/High flag would bottleneck the intervention pipeline and make the product unusable at scale. The EU AI Act's human oversight requirement applies proportionally — the highest-risk automated decisions need the most oversight. Critical tier is the threshold.

#### Conformity Assessment

The system must support a conformity assessment documenting:

- How risk scores are generated (model architecture, features, training data).
- What data flows in (input features, data sources, preprocessing).
- How decisions are audited (logging, versioning, reproducibility).
- What human oversight mechanisms exist (Critical-tier review gate).

#### Transparency Obligations

Employees have the right to know:

- That they are being scored for burnout risk.
- How the scoring works (in general terms — they do not need to understand XGBoost, but they need to understand that the score is generated from survey responses and reflects current burnout risk).
- What the score means and how it is used.

SHAP interpretability (see `product-identity.md` section 3) satisfies the transparency requirement by making each score decomposable into contributing features. This is the response to the ethical risk analysis recommendation to prefer transparent scoring over opaque ML models.

#### Right to Explanation

Any employee who receives a Critical flag can request a human-readable explanation of why the model generated that score. SHAP provides this — each score can be decomposed into the top contributing features with their relative impact.

### EU AI Act Enforcement Status

The Act was passed in 2024 with phased implementation. Specific technical standards for high-risk AI are still being developed. This spec acknowledges the constraint at the principle level; detailed compliance maps to the specific standards when they are finalized.

---

## 3. Interaction Between PDPA and EU AI Act

A single Oraclaire deployment may need to satisfy both frameworks simultaneously:

- **PDPA** governs data collection and consent (how data is obtained).
- **EU AI Act** governs the AI system's operation (how scores are generated, used, and overseen).

For a company with employees in both Singapore and the EU:

- PDPA consent requirements apply to Singapore-based employees.
- EU AI Act requirements apply to EU-based employees.
- The stricter requirement in each dimension wins. Where PDPA requires opt-in consent and the EU AI Act requires transparency, both apply simultaneously.

---

## 4. Parameters Locked by D14/D15

| Parameter               | Value                                                              | Decision             |
| ----------------------- | ------------------------------------------------------------------ | -------------------- |
| Human review gate scope | Critical tier only                                                 | D8                   |
| Right to explanation    | Required for Critical tier, available for all                      | EU AI Act Article 14 |
| Conformity assessment   | Required before any EU customer engagement                         | EU AI Act Annex III  |
| Jurisdictional gating   | Deployment parameter; works council approval required for DE/FR/NL | D14                  |

## 5. Open Questions Remaining

- [ ] What qualifies as "human review" — any trained HR professional, or someone with specific burnout/intervention training? This affects the deployment cost model.
- [ ] Should Oraclaire proactively conform to the strictest jurisdiction (EU AI Act) globally, or build jurisdiction-specific compliance modules?
