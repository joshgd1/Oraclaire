---
type: DECISION
date: 2026-05-13
created_at: 2026-05-13T21:45:00+08:00
author: human
phase: analyze
topic: EU AI Act added as structural floor alongside PDPA — human oversight for Critical tier
tags:
  [
    eu-ai-act,
    high-risk-ai,
    human-oversight,
    critical-tier,
    structural-constraint,
  ]
---

# CHALLENGE 5: EU AI Act as Named Structural Floor

## Decision

Add the EU AI Act (Annex III — high-risk AI in employment) alongside Singapore PDPA as a named structural floor in the Phase 1 frame.

**Hard constraint:** Critical-tier burnout risk flags must require a human review step before any intervention or escalation is triggered. This is not a Phase 2 compliance spec — it is a Phase 1 architectural constraint.

## Alternatives Considered

1. **Defer to Phase 2 as a market expansion consideration** — Rejected. If the system is designed without this constraint and added later, the intervention workflow (Phase 3) must be redesigned. Better to acknowledge now and build around it.

2. **Apply human oversight to all tiers (not just Critical)** — Rejected. Requiring human review for every Low/Moderate/High flag would bottleneck the intervention pipeline and make the product unusable at scale. The EU AI Act's human oversight requirement applies proportionally — the highest-risk automated decisions need the most oversight. Critical tier is the threshold.

3. **Address only at the documentation level (conformity assessment)** — Rejected. The EU AI Act requires both documentation AND operational human oversight mechanisms. Documenting that a system is fully automated does not satisfy the requirement — the system must be designed to allow human intervention.

## Chosen Approach

EU AI Act acknowledged as a structural floor. Critical-tier flags require a human-in-the-loop review before action. SHAP interpretability (already pre-selected as the model family) satisfies the transparency obligation — each score can be decomposed into contributing features.

## Rationale

Automated scoring in employment contexts is a high-risk AI system under Annex III. This applies to any Oraclaire customer with EU-based employees — not just EU-headquartered companies. A Singapore-based company with 50 employees in Berlin is covered. Designing the intervention workflow with a human gate at the Critical tier from day one avoids Phase 3 redesign.

## Trade-offs Accepted

- **Human review at the Critical tier adds latency.** A fully automated system could flag and route within seconds. Human review adds hours or days. This is acceptable because Critical-tier flags should be rare (the model's precision target should ensure this) and the consequences of a wrong Critical flag are severe.
- **The definition of "human review" is not specified.** Who reviews? What training do they need? What is the SLA? These are Phase 3 implementation details. The frame only requires that the mechanism exists.
- **EU AI Act enforcement is still maturing.** The Act was passed in 2024 with phased implementation. Specific technical standards for high-risk AI are still being developed. The frame acknowledges the constraint at the principle level; detailed compliance maps to the specific standards when they are finalized.

## For Discussion

1. Should the human review gate apply only to Critical tier, or should High tier also require human confirmation before manager notification?
2. What qualifies as "human review" — any trained HR professional, or someone with specific burnout/intervention training? This affects the deployment cost model.
3. Should the frame include a "right to explanation" mechanism (EU AI Act Article 14) — i.e., any employee who receives a Critical flag can request a human-readable explanation of why SHAP generated that score?
