---
type: DECISION
date: 2026-05-14
created_at: 2026-05-14
author: human
phase: analyze
topic: Pipeline integrity resolution and Phase 6 clearance — fakeEMP_007 removed, deployment architecture cleared
tags:
  [
    phase6,
    pipeline-integrity,
    fakeEMP_007,
    deployment-architecture,
    clearance,
    d19,
  ]
---

# DECISION D19: Pipeline Integrity Resolution and Phase 6 Clearance

Title: "fakeEMP_007 removed — Phase 4 results carry a 12-row asterisk, full dataset run supersedes — cleared for deployment architecture"

## D19a: Pipeline Integrity Finding Resolved — With Asterisk

The root cause is clear. Finding 1 excluded the duplicate. Finding 3 was marked resolved by Finding 1 without checking whether the original row needed separate exclusion. This is a Phase 2 audit process gap not a model gap. The fix was correct — remove the contaminated row. The asterisk is this:

Every Phase 4 metric was computed on 13 rows including one contaminated row. The Random Forest model learned from fakeEMP_007's feature values. Those values were valid survey data — the contamination was in the ID format, not the feature values. So the model's learning from that row was not corrupted by garbage data — it was trained on a real employee profile with a fake ID.

That is a meaningful distinction. The model is not poisoned. The performance claims are slightly overstated because one of the 13 rows was a contamination case that the model handled correctly (TP at 0.85 probability). Removing it will likely have minimal impact on the full dataset run but we cannot know that until we run it.

Record: "Phase 4 metrics are 13-row results including one contaminated row. Phase 4 is a pipeline validation exercise only — not a performance claim. Full dataset re-run on 22,750 clean rows supersedes all 12-row results. No Phase 4 metric should be cited to a customer or investor without this caveat."

## D19b: Phase 2 Audit Process Gap Documented — Process Fix Pre-Registered

Finding 3 was marked "resolved by Finding 1" without executing the actual exclusion it flagged. This is the exact failure mode the Phase 2 audit was designed to catch and it slipped through the disposition process.

Fix for the full dataset run: When a contamination finding references a pattern (fakeEMP\_ prefix) rather than a single row — the disposition must apply to ALL rows matching the pattern, not just the specific row that triggered the finding.

Process documentation addition: "Pattern-based contamination findings must enumerate all matching rows and apply disposition to each. A finding marked 'resolved by [other finding]' must explicitly confirm that all pattern matches are covered — not just the specific row cited."

This is a process improvement not a product change. It applies to every future dataset audit run through this pipeline.

## D19c: Re-Run Required Before Deployment Claim

Before Oraclaire makes any performance claim to a real customer — Phase 4 must be re-run on the full Kaggle dataset with all Phase 2 exclusions correctly applied.

The 12-row clean sample result is a validated pipeline. It is not a validated model.

The difference: A validated pipeline means the audit, feature framing, training, and evaluation steps all work correctly. A validated model means the performance metrics are reliable enough to stake the product's commercial claims on.

We have the first. We do not yet have the second.

This is not a problem for deployment architecture — we can build the serving layer, the Streamlit UI, and the SHAP waterfall against the 12-row model now. The architecture does not change when the full dataset is loaded. The model artifact gets replaced. Everything else stays.

Sprint 1 exit criteria addition: "Full dataset Phase 4 re-run completed and all six Phase 6 floor checks pass on 22,750 rows before first customer is shown performance metrics."

## Clearance

Pipeline integrity finding: RESOLVED
Phase 4 asterisk: DOCUMENTED
Process gap: DOCUMENTED AND FIXED FOR FUTURE RUNS
Full dataset re-run: PRE-COMMITTED AND GATED

Cleared for deployment architecture.

## Consequences

1. Deployment architecture may proceed — build against 12-row model, replace artifact later
2. No Phase 4 metric cited externally without the 13-row asterisk
3. Pattern-based contamination dispositions must enumerate all matches going forward
4. Full dataset re-run is a hard gate before any customer-facing performance claim

## For Discussion

1. Should the 13-row Phase 4 results be re-run on 12 clean rows now, or is the full dataset run the only re-run that matters?
2. Does the process fix (D19b) need to be codified as a rule for future dataset audits, or is the journal entry sufficient?
3. Is the "validated pipeline vs validated model" distinction worth surfacing in the product specs?
