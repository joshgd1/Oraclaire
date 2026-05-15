---
type: DECISION
date: 2026-05-14
created_at: 2026-05-14T22:30:00+10:00
author: co-authored
session_id: resume-post-clear
session_turn: 8
project: Oraclaire
topic: Sprint 1 codification — agent, specs, and institutional knowledge updated
phase: codify
tags:
  [codify, sprint1-complete, agent-update, spec-update, institutional-knowledge]
---

# Decision D28 — Sprint 1 Codification

**Title:** Project agent and specs updated with Sprint 1 completion knowledge

---

## What Was Codified

### 1. Project Agent Updated

File: `.claude/agents/project/oraclaire-product-knowledge.md`

Updated from Phase 1 frame (D1-D17) to Sprint 1 complete (D1-D27). Added:

- Tier boundaries and locked thresholds (THRESHOLD_A = 0.35, Critical = 0.90, D24-D26)
- Pre-registered floors table with PASS/FAIL/PENDING status
- Hard constraints H1-H8 and soft constraints S1-S4 (Phase 11)
- Objective function with 4 cost terms (Phase 10)
- Deployment gate outcome (D27 GO with four conditions)
- Customer deployment checklist (6-gate structure)
- Monitoring plan (7 signals)
- Sprint 2 opens-with (5 items)
- Decision log expanded from 12 to 27 entries
- Lessons learned (3 transferable, 2 domain-specific)

Agent is 277 lines (within 400-line limit per cc-artifacts.md).

### 2. Specs Updated

File: `specs/product-identity.md`

Updated section 3 (Model Family) and section 7 (Parameters Locked):

- Threshold: 0.30 provisional → 0.35 locked (D26), drift range (0.30, 0.40)
- Feature set: 8 → 10 features (added `tenure_fatigue`, `tenure_workload` from D24 RE-DO)
- Critical boundary: 0.75 → 0.90 (D24)
- MFS SHAP post-RE-DO: 29.9%
- FP rate at 0.35: 16.6% (accepted override)
- Deployment status: GO (D27)
- DPO hard gate clarified with D27 Condition 1 reference

### 3. Files NOT Changed (already current)

- `specs/population-and-scoring.md` — accurate through D14/D15
- `specs/cost-model.md` — accurate through D14; Phase 10 objective lives in journal (not spec — it contains unvalidated cost terms)
- `specs/regulatory-constraints.md` — accurate
- `workspaces/Oraclaire/playbook/appendix-a-lessons.md` — written this session during Phase 9
- `workspaces/Oraclaire/customer-deployment-checklist.md` — written this session

---

## What Was NOT Codified (and Why)

- **Phase 10/11 as specs:** The objective function and constraints contain unvalidated cost terms (reviewer rate, review time, assessment cost). Per spec-accuracy.md Rule 5, these cannot enter specs until validated against real data. They remain in `workspaces/Oraclaire/journal/phase_10_objective.md` and `phase_11_constraints.md`.
- **Sprint 2 backlog items:** Not spec'd — they are todos, not domain truth.
- **New agents or skills:** No new Kailash SDK patterns emerged. The codification updated the existing Oraclaire product-knowledge agent.

---

## For Discussion

1. Should the customer deployment checklist (6-gate, D27 operationalisation) be promoted to `specs/` once the first customer completes it, or does it remain a workspace artifact?
2. When Sprint 2 validates the three full-dataset requirements (gender fairness, per-tier Brier, Threshold B HRIS), should the specs be updated to remove "provisional" from Threshold B?
3. The objective function's four unvalidated cost terms — if the founder confirms them before Sprint 2, should they enter `specs/cost-model.md` as a new section?
