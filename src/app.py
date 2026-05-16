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

from src.model.train import run as train_model
from src.views.api_client import (
    ApiError,
    get_employee_scores,
    get_employee_shap,
    get_employee_trajectory,
    get_exclusions,
    get_participation,
    get_my_team,
    get_team_aggregate,
    get_team_recommendations,
    get_team_trajectory,
    get_teams,
    get_trends,
    login,
)
from src.views.employee import render_employee_view
from src.views.hr_aggregate import render_hr_view
from src.views.manager import render_manager_view
from src.views.reviewer import render_reviewer_view


def ensure_model():
    """Train model if artifact doesn't exist."""
    from src.config import MODEL_ARTIFACT_PATH

    if not Path(MODEL_ARTIFACT_PATH).exists():
        with st.spinner("Training model on clean dataset..."):
            train_model()
        st.success("Model trained and saved.")


def page_employee():
    token = st.session_state.get("auth_token")
    employee_id = st.session_state.get("auth_employee_id")

    if not token or not employee_id:
        # Demo mode: feature sliders + local scoring
        st.sidebar.markdown("### Demo: Employee Assessment")
        demo_employee_id = st.sidebar.text_input("Employee ID (for reference)", value="EID_001")

        # ── Natural-language questionnaire ───────────────────────────────────────
        # Maps human-readable questions to model features.
        # Internal-only features (missing_ra, missing_mfs) get safe defaults (0 = not missing).

        st.sidebar.markdown("### About your role")

        tenure_years = st.sidebar.selectbox(
            "How long have you been in your current role?",
            options=[0, 1, 2, 3, 4, 5],
            format_func=lambda x: [
                "Less than 6 months", "6–12 months", "1–2 years",
                "2–5 years", "5–10 years", "10+ years",
            ][x],
            index=2,
        )
        # Map to approximate days
        tenure_map = {0: 90, 1: 270, 2: 547, 3: 1095, 4: 1825, 5: 2555}
        tenure_days = tenure_map.get(tenure_years, 547)

        st.sidebar.markdown("### How have you been feeling?")

        energy = st.sidebar.slider(
            "Energy levels over the past few weeks",
            min_value=1.0,
            max_value=10.0,
            value=5.0,
            step=0.5,
            help="1 = completely drained, 10 = full of energy",
        )

        workload = st.sidebar.slider(
            "Current workload intensity",
            min_value=0.0,
            max_value=10.0,
            value=5.0,
            step=0.5,
            help="0 = very light, 10 = overwhelming",
        )

        st.sidebar.markdown("### Your working situation")

        wfh = st.sidebar.radio(
            "Do you have a suitable work-from-home setup?",
            options=["Yes", "No", "Not applicable"],
            index=0,
            horizontal=True,
        )
        wfh_setup = 1 if wfh == "Yes" else 0

        company = st.sidebar.radio(
            "Which best describes your organisation?",
            options=["Product company", "Service company"],
            index=0,
            horizontal=True,
        )
        company_type = 0 if company == "Product company" else 1

        st.sidebar.markdown("### Your level")

        seniority_tier = st.sidebar.selectbox(
            "Your role level",
            options=[0, 1],
            format_func=lambda x: "Senior (manager / principal / director)" if x == 1 else "Junior / individual contributor",
            index=0,
        )

        # ── Build features dict ───────────────────────────────────────────────
        # Internal-only features: defaults (0 = not missing, normal case for demo)
        features = {
            "tenure_days": float(tenure_days),
            "mental_fatigue_score": float(energy),
            "resource_allocation": float(workload),
            "wfh_setup": float(wfh_setup),
            "company_type": float(company_type),
            "seniority_tier": float(seniority_tier),
            # Internal audit features — not shown to employees, defaults only
            "missing_ra": 0.0,
            "missing_mfs": 0.0,
            "tenure_fatigue": 5.0,
            "tenure_workload": 5.0,
        }

        if st.sidebar.button("Run assessment"):
            render_employee_view(
                employee_id=demo_employee_id,
                features=features,
                seniority_tier=seniority_tier,
                auth_token=None,
            )
        else:
            st.info("Answer the questions above and click **Run assessment** to see your results.")
            st.caption(
                "ℹ️ Demo mode — results are calculated locally and never stored. "
                "Sign in with your Employee ID to see your actual assessment."
            )
        return

    # Authenticated: fetch from backend
    try:
        scores_data = get_employee_scores(token)
        shap_data = get_employee_shap(token)
        trajectory_data = get_employee_trajectory(token)
    except ApiError as e:
        st.error(f"Failed to load your assessment data: {e}")
        return
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return

    scores = scores_data.get("scores", [])
    if not scores:
        st.info("No assessment results yet. Complete a cycle when one is open.")
        return

    latest = scores[0]
    shap_values = shap_data.get("shap_values", [])
    resources = latest.get("resources", [])

    render_employee_view(
        employee_id=employee_id,
        features=None,
        seniority_tier=None,
        risk_tier=latest.get("risk_tier"),
        burnout_probability=latest.get("numeric_score"),
        shap=shap_values,
        resources=resources,
        trajectory_data=trajectory_data,
        auth_token=token,
    )


def page_hr():
    token = st.session_state.get("auth_token")
    if not token:
        st.warning("Sign in to view the HR dashboard.")
        return
    role = st.session_state.get("auth_role", "")
    if role not in ("hr_admin", "system_admin"):
        st.error("Access denied. HR Aggregate is only available to HR Admins.")
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


def page_manager():
    token = st.session_state.get("auth_token")
    if not token:
        st.warning("Sign in with your Employee ID to access the manager dashboard.")
        return

    # Get the manager's own team
    try:
        team_info = get_my_team(token)
    except ApiError as e:
        st.error(f"Failed to load team data: {e}")
        return
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return

    team_id = team_info.get("team_id")
    team_name = team_info.get("team_name", "Your Team")

    if team_id is None:
        st.info(
            "You don't have a team assigned. "
            "The Manager view is available to employees with a manager role."
        )
        return

    try:
        aggregate_data = get_team_aggregate(token, team_id)
        rec_data = get_team_recommendations(token, team_id)
        trajectory_data = get_team_trajectory(token, team_id)
    except ApiError as e:
        st.error(f"Failed to load team data: {e}")
        return
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return

    render_manager_view(
        team_id=aggregate_data.get("team_id", team_id),
        team_name=aggregate_data.get("team_name", team_name),
        team_size=aggregate_data.get("team_size", 0),
        suppressed=aggregate_data.get("suppressed", False),
        suppression_reason=aggregate_data.get("suppression_reason"),
        visibility_locked=aggregate_data.get("visibility_locked", False),
        cycles=aggregate_data.get("cycles", []),
        tier_distribution=aggregate_data.get("tier_distribution", {}),
        high_critical_pct=aggregate_data.get("high_critical_pct"),
        consecutive_weeks_elevated=aggregate_data.get("consecutive_weeks_elevated", 0),
        top_factors=rec_data.get("top_factors", []),
        recommendations=rec_data.get("recommendations", []),
        worst_tier=rec_data.get("worst_tier", "low"),
        ort_ceiling=aggregate_data.get("ort_ceiling", 0.20),
        team_trajectory_data=trajectory_data,
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
        options=["Employee", "HR Aggregate", "Manager", "Reviewer"],
    )

    if page == "Employee":
        page_employee()
    elif page == "HR Aggregate":
        page_hr()
    elif page == "Manager":
        page_manager()
    elif page == "Reviewer":
        if not st.session_state.auth_token:
            st.warning("Sign in with your Employee ID to access the reviewer queue.")
            return
        role = st.session_state.get("auth_role", "")
        if role not in ("system_admin", "hr_admin"):
            st.error("Access denied. The Review Queue is only available to Administrators.")
            return
        page_reviewer(st.session_state.auth_token)


if __name__ == "__main__":
    main()
