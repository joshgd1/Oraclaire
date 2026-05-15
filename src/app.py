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
from src.views.api_client import (
    ApiError,
    get_exclusions,
    get_participation,
    get_teams,
    get_trends,
    login,
)
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
    token = st.session_state.get("auth_token")
    if not token:
        st.warning("Sign in to view the HR dashboard.")
        return

    try:
        trends_data = get_trends(token)
        teams_data = get_teams(token)
        exclusions_data = get_exclusions(token)
        participation_data = get_participation(token)
    except ApiError as e:
        st.error(f"Failed to load HR data: {e}")
        return
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return

    # M6-08: 24h employee-first visibility gate
    visibility_locked = trends_data.get("visibility_locked", False)
    locked_until = trends_data.get("visibility_locked_until")
    if visibility_locked:
        st.info(
            "📋 **Results pending** — Risk distribution and team-level scores are "
            "hidden for 24 hours after cycle close to give employees first access "
            + (f"to their own scores (unlocks at {locked_until})." if locked_until else "")
        )

    # Extract trends data
    tiers = trends_data.get("tiers", {"low": 0, "moderate": 0, "high": 0, "critical": 0})
    total_scored = trends_data.get("total_scored", 0)
    scores = [
        {"risk_tier": tier, "burnout_probability": None}
        for tier, count in tiers.items()
        for _ in range(count)
    ]

    # Extract teams data (may be empty if gate active)
    teams = [
        {
            "name": t["name"],
            "team_size": t["member_count"],
            "high_critical_pct": t.get("high_critical_pct", 0.0),
            "consecutive_weeks_elevated": t.get("consecutive_weeks_elevated", 0),
        }
        for t in teams_data.get("teams", [])
    ]

    # Extract exclusions
    by_category = exclusions_data.get("by_category", {})
    exclusions = {
        "on_leave": by_category.get("on_leave", 0),
        "protected_process": by_category.get("protected_process", 0),
        "grievance_cooldown": by_category.get("grievance_cooldown", 0),
    }

    # Extract latest cycle participation
    cycles = participation_data.get("cycles", [])
    responded = 0
    scoreable = 0
    if cycles:
        latest = cycles[0]
        responded = latest.get("responded", 0)
        scoreable = latest.get("total_eligible", 0)

    render_hr_view(
        scores=scores,
        teams=teams,
        exclusions=exclusions,
        scoreable=scoreable,
        responded=responded,
    )


def page_reviewer(token: str):
    render_reviewer_view(token=token)


def main():
    st.set_page_config(page_title="Oraclaire", page_icon=":brain:", layout="wide")

    ensure_model()

    # Auth: simple employee-id login stored in session state
    if "auth_token" not in st.session_state:
        st.session_state.auth_token = None
    if "auth_employee_id" not in st.session_state:
        st.session_state.auth_employee_id = None
    if "auth_role" not in st.session_state:
        st.session_state.auth_role = None

    with st.sidebar:
        st.markdown("### Sign in")
        login_emp_id = st.text_input(
            "Employee ID",
            value=st.session_state.auth_employee_id or "",
            placeholder="Enter your employee ID",
            key="login_emp_id_input",
        )
        if st.button("Sign in", key="sign_in_btn"):
            if login_emp_id.strip():
                try:
                    auth_data = login(login_emp_id.strip())
                    st.session_state.auth_token = auth_data["token"]
                    st.session_state.auth_employee_id = login_emp_id.strip()
                    st.session_state.auth_role = auth_data.get("role", "")
                    st.rerun()
                except ApiError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Login error: {e}")
        if st.session_state.auth_token:
            st.success(f"Signed in as {st.session_state.auth_employee_id} ({st.session_state.auth_role})")
            if st.button("Sign out", key="sign_out_btn"):
                st.session_state.auth_token = None
                st.session_state.auth_employee_id = None
                st.session_state.auth_role = None
                st.rerun()

    page = st.sidebar.selectbox(
        "View",
        options=["Employee", "HR Aggregate", "Reviewer"],
    )

    if page == "Employee":
        page_employee()
    elif page == "HR Aggregate":
        page_hr()
    elif page == "Reviewer":
        if not st.session_state.auth_token:
            st.warning("Sign in with your Employee ID to access the reviewer queue.")
            return
        page_reviewer(st.session_state.auth_token)


if __name__ == "__main__":
    main()
