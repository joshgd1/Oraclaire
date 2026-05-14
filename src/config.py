"""
Oraclaire Burnout Risk Scorer — Sprint 1 Configuration

All configurable values in one place. No magic numbers elsewhere.
Update threshold values here when full dataset re-run completes.
"""

# ── Model ──────────────────────────────────────────────────────────────────────

MODEL_PARAMS = {
    "n_estimators": 100,
    "max_depth": 5,
    "random_state": 42,
}

FEATURES = [
    "company_type",
    "wfh_setup",
    "resource_allocation",
    "mental_fatigue_score",
    "missing_ra",
    "missing_mfs",
    "seniority_tier",
    "tenure_days",
    "tenure_fatigue",
    "tenure_workload",
]

SENIORITY_DESIGNATION_CUTOFF = 4    # Kaggle fallback — Designation >= this value = senior (superseded by HRIS at deployment)
BINARISATION_THRESHOLD = 0.45

# ── Thresholds ─────────────────────────────────────────────────────────────────
# Two-threshold architecture (D11 Nuance 3, D17 confirmed).
# Both start at 0.30. Threshold B updated after HRIS validation — no code change.

THRESHOLD_A = 0.35  # General population (FN cost $4,000) — D26 locked
THRESHOLD_B = 0.30  # Senior tier (FN cost $21,000) — provisional, update after HRIS validation

# Pre-registered floors (D18 confirmed, D20 re-confirmed)

THRESHOLD_A_FP_CEILING = 0.15  # 15% FP ceiling on general population
THRESHOLD_A_FN_TARGET = 0.15   # 15% FN target on general population
THRESHOLD_B_FP_CEILING = 0.20  # 20% FP ceiling on senior tier
THRESHOLD_B_FN_TARGET = 0.10   # 10% FN target on senior tier

DRIFT_TOLERANCE = 0.05         # ±0.05 from current THRESHOLD_A. Original 0.30 exceeded per D26 — new anchor is THRESHOLD_A = 0.35. Range: DRIFT_ACCEPTABLE_RANGE.
DRIFT_ACCEPTABLE_RANGE = (0.30, 0.40)  # ±0.05 from THRESHOLD_A 0.35 (D26). Future adjustments within this range are adjustments. Outside this range require a new cost rationale.

BRIER_FLOOR = 0.15  # Calibration floor (D18). Exceed → Platt scaling before threshold selection.

# ── Risk Tier Boundaries ──────────────────────────────────────────────────────
# D20 amendment: Critical at 0.75 (not 0.60) to keep Critical ≤ 5% of scorable
# population per D14 Parameter 7. Validate on full dataset.

TIER_BOUNDARIES = {
    "low": (0.00, 0.20),
    "moderate": (0.20, 0.30),
    "high": (0.30, 0.90),
    "critical": (0.90, 1.00),
}

TIER_COLORS = {
    "low": "#22c55e",       # green
    "moderate": "#eab308",  # yellow
    "high": "#f97316",      # orange
    "critical": "#ef4444",  # red
}

TIER_ORDER = ["low", "moderate", "high", "critical"]

# ── Feature Labels ─────────────────────────────────────────────────────────────
# Employee-facing plain language. None = not shown in employee SHAP waterfall.
# Appears in DPO audit trail only. Update in one place when features change.

FEATURE_LABELS = {
    "tenure_days": "Your time in this role",
    "mental_fatigue_score": "Your recent energy levels",
    "resource_allocation": "Your current workload demands",
    "seniority_tier": "Your role level",
    "wfh_setup": "Your working arrangement",
    "company_type": "Your organisation type",
    "missing_ra": None,   # DPO audit trail only
    "missing_mfs": None,  # DPO audit trail only
}

# ── Curated Resources ─────────────────────────────────────────────────────────
# Matched by top SHAP contributor for Moderate and above.

RESOURCES = {
    "tenure_days": [
        "Role rotation programme — discuss with your manager",
        "Career development conversation guide",
        "Internal mobility opportunities",
    ],
    "mental_fatigue_score": [
        "Energy management toolkit",
        "Recovery strategies for sustained performance",
        "Mindfulness and reset techniques",
    ],
    "resource_allocation": [
        "Workload negotiation guide",
        "Delegation skills workshop",
        "Priority management framework",
    ],
}

# ── HR Aggregate ───────────────────────────────────────────────────────────────

MIN_TEAM_SIZE = 5                       # D1 — below this, aggregate suppressed
ORT_CEILING = 0.20                      # D14 Parameter 10 — High+Critical combined
ORT_PULSE_CONSECUTIVE_WEEKS = 2         # D15 amendment — consecutive weekly pulses exceeding ceiling to trigger ORT alert
ORT_TRIGGER_WEEKS = 2                   # D15-2 — consecutive weekly pulses
ORT_TRIGGER_QUARTERLY = 1               # D15-2 — single quarterly CBI

# ── Employee Dashboard ────────────────────────────────────────────────────────

EMPLOYEE_FIRST_GATE_HOURS = 24          # D13 Mechanism C — HR delay after assessment

# ── Weekly Pulse ───────────────────────────────────────────────────────────────

PULSE_DRIFT_THRESHOLD = 2               # Points decline per week to count as drift
PULSE_DRIFT_CONSECUTIVE_WEEKS = 3       # D13 Mechanism A — triggers early reassessment

# ── Critical Tier Review ──────────────────────────────────────────────────────

REVIEW_TIMEOUT_HOURS = 48               # Auto-escalate if no review within this window

# ── Audit ──────────────────────────────────────────────────────────────────────

PREDICTIONS_LOG = "data/audit/predictions.jsonl"
PULSE_LOG = "data/audit/pulse.jsonl"

UNLABELLED_POOL_PATH = "data/processed/unlabelled_pool.csv"

# ── Data Paths ─────────────────────────────────────────────────────────────────

CLEAN_DATA_PATH = "data/processed/train_clean.csv"
MODEL_ARTIFACT_PATH = "data/models/rf_model.joblib"
