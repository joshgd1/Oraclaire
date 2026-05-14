"""
Oraclaire Burnout Risk Scorer — Sprint 1 Streamlit Application.

Three-role dashboard:
  - Employee: own risk tier, SHAP breakdown, resources
  - HR Admin: org-wide aggregates, participation, ORT, exclusions
  - Reviewer: Critical-tier human review gate

Run: streamlit run src/app.py
"""

import sys
from pathlib import Path

import streamlit as st

# Ensure project root is on sys.path for src.* imports
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from src.config import (
    FEATURES,
    SENIORITY_DESIGNATION_CUTOFF,
    TIER_ORDER,
)
from src.model.train import run as train_model
from src.views.employee import render_employee_view
from src.views.hr_aggregate import render_hr_view
from src.views.reviewer import render_reviewer_view


def ensure_model():
    """Train model if artifact doesn't exist."""
    from src.config import MODEL_ARTIFACT_PATH

    if not Path(MODEL_ARTIFACT_PATH).exists():
        with st.spinner("Training model on clean dataset..."):
            train_model()
        st.success("Model trained and saved.")


def page_employee():
    st.sidebar.markdown("### Employee Assessment")
    employee_id = st.sidebar.text_input("Employee ID", value="EID_001")

    seniority_tier = st.sidebar.selectbox(
        "Seniority tier",
        options=[0, 1],
        format_func=lambda x: "Senior (1)" if x == 1 else "Junior (0)",
        index=0,
    )

    st.sidebar.markdown("### Assessment features")
    features = {}
    feature_defaults = {
        "company_type": (0, 1),
        "wfh_setup": (0, 1),
        "resource_allocation": (0.0, 10.0),
        "mental_fatigue_score": (0.0, 10.0),
        "missing_ra": (0, 1),
        "missing_mfs": (0, 1),
        "seniority_tier": (0, 1),
        "tenure_days": (0, 3650),
    }

    for feat in FEATURES:
        default_min, default_max = feature_defaults.get(feat, (0.0, 10.0))
        val = st.sidebar.slider(
            feat.replace("_", " ").title(),
            min_value=float(default_min),
            max_value=float(default_max),
            value=(float(default_min) + float(default_max)) / 2,
            step=0.1 if default_min != default_max else 1.0,
            key=f"feat_{feat}",
        )
        features[feat] = val

    # Override seniority_tier from sidebar selector
    features["seniority_tier"] = float(seniority_tier)

    if st.sidebar.button("Run assessment"):
        render_employee_view(
            employee_id=employee_id,
            features=features,
            seniority_tier=seniority_tier,
        )
    else:
        st.info("Configure features in the sidebar and click **Run assessment**.")


def page_hr():
    # Demo data from the 12-row clean dataset
    scores = [
        {"risk_tier": "low", "burnout_probability": 0.12},
        {"risk_tier": "low", "burnout_probability": 0.08},
        {"risk_tier": "moderate", "burnout_probability": 0.25},
        {"risk_tier": "moderate", "burnout_probability": 0.22},
        {"risk_tier": "high", "burnout_probability": 0.45},
        {"risk_tier": "high", "burnout_probability": 0.52},
        {"risk_tier": "high", "burnout_probability": 0.38},
        {"risk_tier": "low", "burnout_probability": 0.15},
        {"risk_tier": "moderate", "burnout_probability": 0.28},
        {"risk_tier": "low", "burnout_probability": 0.05},
        {"risk_tier": "high", "burnout_probability": 0.61},
        {"risk_tier": "low", "burnout_probability": 0.18},
    ]

    teams = [
        {"name": "Engineering", "team_size": 8, "high_critical_pct": 0.25, "consecutive_weeks_elevated": 2},
        {"name": "Product", "team_size": 4, "high_critical_pct": 0.0, "consecutive_weeks_elevated": 0},
        {"name": "Marketing", "team_size": 6, "high_critical_pct": 0.17, "consecutive_weeks_elevated": 1},
    ]

    exclusions = {
        "on_leave": 2,
        "protected_process": 1,
        "grievance_cooldown": 1,
    }

    render_hr_view(
        scores=scores,
        teams=teams,
        exclusions=exclusions,
        scoreable=12,
        responded=8,
    )


def page_reviewer():
    reviews = [
        {
            "employee_id": "EID_007",
            "probability": 0.82,
            "shap_decomposition": [
                {"feature": "tenure_days", "label": "Your time in this role", "impact_value": 0.35, "direction": "increases"},
                {"feature": "mental_fatigue_score", "label": "Your recent energy levels", "impact_value": 0.28, "direction": "increases"},
                {"feature": "resource_allocation", "label": "Your current workload demands", "impact_value": 0.19, "direction": "increases"},
            ],
            "scored_at": "2026-05-14T10:00:00Z",
            "trajectory": "worsened",
        },
    ]

    render_reviewer_view(reviews)


def main():
    st.set_page_config(page_title="Oraclaire", page_icon=":brain:", layout="wide")

    ensure_model()

    page = st.sidebar.selectbox(
        "View",
        options=["Employee", "HR Aggregate", "Reviewer"],
    )

    if page == "Employee":
        page_employee()
    elif page == "HR Aggregate":
        page_hr()
    elif page == "Reviewer":
        page_reviewer()


if __name__ == "__main__":
    main()
