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
from src.views.employee_ux import render_employee_ux
from src.views.hr_aggregate import render_hr_view
from src.views.manager import render_manager_view
from src.views.reviewer import render_reviewer_view

# ── Theme constants ────────────────────────────────────────────────────────────

THEME = {
    "bg": "#1e1e2e",
    "card_bg": "#2a2a3e",
    "primary": "#0d7377",
    "primary_light": "#14919b",
    "text": "#e5e7eb",
    "text_secondary": "#9ca3af",
    "border": "#3d3d5c",
    "low_color": "#10b981",
    "moderate_color": "#f59e0b",
    "high_color": "#f97316",
    "critical_color": "#ef4444",
    "sidebar_bg": "#13131f",
    "sidebar_text": "#e5e7eb",
}


def _inject_theme():
    """Inject custom CSS for a clean, professional theme."""
    st.html(
        f"""
        <style>
        /* Page */
        .stApp, .stMainBlockContainer {{
            background: {THEME['bg']} !important;
        }}
        /* Cards */
        .stMarkdown, .element-container {{
            background: transparent !important;
        }}
        /* Headers */
        h1, h2, h3, h4 {{
            color: {THEME['text']} !important;
            font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
            font-weight: 600 !important;
        }}
        /* Sidebar */
        [data-testid="stSidebar"] {{
            background: {THEME['sidebar_bg']} !important;
        }}
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {{
            color: {THEME['sidebar_text']} !important;
        }}
        /* Metric cards */
        [data-testid="stMetric"] {{
            background: {THEME['card_bg']} !important;
            border: 1px solid {THEME['border']} !important;
            border-radius: 12px !important;
            padding: 16px 20px !important;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
        }}
        [data-testid="stMetricLabel"] {{
            color: {THEME['text_secondary']} !important;
            font-size: 0.8rem !important;
            font-weight: 500 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.04em !important;
        }}
        [data-testid="stMetricValue"] {{
            color: {THEME['text']} !important;
            font-weight: 700 !important;
            font-size: 1.6rem !important;
        }}
        /* Buttons */
        .stButton > button {{
            border-radius: 8px !important;
            font-weight: 600 !important;
            border: none !important;
            transition: all 0.15s !important;
        }}
        .stButton > button:hover {{
            opacity: 0.88 !important;
            transform: translateY(-1px) !important;
        }}
        /* Text inputs */
        .stTextInput > div > div > input, .stTextArea > div > div > textarea {{
            border-radius: 8px !important;
            border: 1px solid {THEME['border']} !important;
            background: {THEME['card_bg']} !important;
            color: {THEME['text']} !important;
        }}
        .stTextInput > div > div > input::placeholder, .stTextArea > div > div > textarea::placeholder {{
            color: {THEME['text_secondary']} !important;
        }}
        /* Select boxes */
        .stSelectbox > div > div {{
            border-radius: 8px !important;
        }}
        /* Success/warning/error boxes */
        .stAlert {{
            border-radius: 10px !important;
            border: none !important;
        }}
        /* Divider */
        hr {{
            border: none !important;
            border-top: 1px solid {THEME['border']} !important;
            margin: 24px 0 !important;
        }}
        /* Download button */
        .stDownloadButton > button {{
            border-radius: 8px !important;
        }}
        /* Expanders */
        .streamlit-expanderHeader {{
            border-radius: 8px !important;
            background: {THEME['card_bg']} !important;
            border: 1px solid {THEME['border']} !important;
        }}
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px !important;
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 8px 8px 0 0 !important;
            padding: 8px 16px !important;
        }}
        /* Sidebar button accent */
        [data-testid="stSidebar"] .stButton > button {{
            width: 100% !important;
            background: {THEME['primary']} !important;
            color: white !important;
        }}
        [data-testid="stSidebar"] .stButton > button:hover {{
            background: {THEME['primary_light']} !important;
        }}
        /* Subheader text in sidebar */
        [data-testid="stSidebar"] h3 {{
            color: {THEME['sidebar_text']} !important;
            font-size: 0.95rem !important;
            font-weight: 600 !important;
            margin-top: 16px !important;
            margin-bottom: 4px !important;
        }}
        [data-testid="stSidebar"] label {{
            color: #d1d5db !important;
        }}
        [data-testid="stSidebar"] p {{
            color: #9ca3af !important;
            font-size: 0.8rem !important;
        }}
        /* Info boxes */
        [data-testid="stInfo"] {{
            background: #eff6ff !important;
            border-left: 4px solid #3b82f6 !important;
            border-radius: 8px !important;
        }}
        [data-testid="stSuccess"] {{
            background: #f0fdf4 !important;
            border-left: 4px solid #22c55e !important;
            border-radius: 8px !important;
        }}
        [data-testid="stWarning"] {{
            background: #fffbeb !important;
            border-left: 4px solid #f59e0b !important;
            border-radius: 8px !important;
        }}
        [data-testid="stError"] {{
            background: #fef2f2 !important;
            border-left: 4px solid #ef4444 !important;
            border-radius: 8px !important;
        }}
        /* Spinner */
        .stSpinner > div {{
            border-color: {THEME['primary']} !important;
        }}
        </style>
        """
    )


def _card(content_fn, *args, **kwargs):
    """Render content inside a clean white card."""
    with st.container():
        st.markdown(
            f'<div style="background:{THEME["card_bg"]};border:1px solid {THEME["border"]};'
            f'border-radius:14px;padding:24px;margin-bottom:20px;'
            f'box-shadow:0 1px 4px rgba(0,0,0,0.06)">',
            unsafe_allow_html=True,
        )
        content_fn(*args, **kwargs)
        st.markdown("</div>", unsafe_allow_html=True)


def _section_title(title: str, icon: str = ""):
    prefix = f"{icon} " if icon else ""
    st.markdown(
        f'<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.08em;color:{THEME["text_secondary"]};margin:0 0 4px 0">'
        f"{prefix}{title}</p>",
        unsafe_allow_html=True,
    )


def _tier_badge_html(tier: str, probability: float) -> str:
    colors = {
        "low": THEME["low_color"],
        "moderate": THEME["moderate_color"],
        "high": THEME["high_color"],
        "critical": THEME["critical_color"],
    }
    color = colors.get(tier.lower(), "#888")
    return (
        f'<div style="display:inline-flex;align-items:center;gap:12px;'
        f'padding:12px 20px;border-radius:10px;background:{color}18;'
        f'border:1px solid {color}44;margin-bottom:16px">'
        f'<span style="font-size:1.5rem;font-weight:800;color:{color};'
        f'text-transform:uppercase;letter-spacing:0.05em">{tier}</span>'
        f'<span style="color:{THEME["text_secondary"]};font-size:0.9rem">'
        f'Score: <strong style="color:{THEME["text"]}">{probability:.1%}</strong></span>'
        f"</div>"
    )


def ensure_model():
    """Train model if artifact doesn't exist."""
    from src.config import MODEL_ARTIFACT_PATH

    if not Path(MODEL_ARTIFACT_PATH).exists():
        with st.spinner("Training model on clean dataset..."):
            train_model()
        st.success("Model trained and saved.")


def page_landing():
    """Welcome landing page shown when not logged in and no demo started."""
    st.markdown(
        f'<div style="text-align:center;padding:60px 20px">'
        f'<h1 style="font-size:2.5rem;font-weight:800;color:{THEME["text"]};margin-bottom:16px">'
        f'How are you really doing?</h1>'
        f'<p style="font-size:1.15rem;color:{THEME["text_secondary"]};max-width:500px;margin:0 auto 40px">'
        f'Oraclaire helps teams understand and address burnout risk — '
        f'privately, collaboratively, and early.</p></div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f'<div style="text-align:center;padding:24px;background:{THEME["card_bg"]};'
            f'border-radius:14px;border:1px solid {THEME["border"]}">'
            f'<div style="font-size:2rem;margin-bottom:12px">🔒</div>'
            f'<h3 style="color:{THEME["text"]};margin-bottom:8px">Private</h3>'
            f'<p style="color:{THEME["text_secondary"]};font-size:0.9rem">'
            f'Individual results are never shared without consent.</p></div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div style="text-align:center;padding:24px;background:{THEME["card_bg"]};'
            f'border-radius:14px;border:1px solid {THEME["border"]}">'
            f'<div style="font-size:2rem;margin-bottom:12px">👥</div>'
            f'<h3 style="color:{THEME["text"]};margin-bottom:8px">Team-focused</h3>'
            f'<p style="color:{THEME["text_secondary"]};font-size:0.9rem">'
            f'Managers see trends, never individual scores.</p></div>',
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f'<div style="text-align:center;padding:24px;background:{THEME["card_bg"]};'
            f'border-radius:14px;border:1px solid {THEME["border"]}">'
            f'<div style="font-size:2rem;margin-bottom:12px">💡</div>'
            f'<h3 style="color:{THEME["text"]};margin-bottom:8px">Actionable</h3>'
            f'<p style="color:{THEME["text_secondary"]};font-size:0.9rem">'
            f'Get resources matched to what\'s actually affecting you.</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    col_demo, col_signin = st.columns([1, 1])
    with col_demo:
        st.markdown(
            f'<p style="text-align:center;color:{THEME["text_secondary"]};margin-bottom:12px">'
            f'Want to see how it works?</p>',
            unsafe_allow_html=True,
        )
        if st.button("Try the demo", use_container_width=True, type="secondary"):
            st.session_state.ux_started = True
            st.session_state.page_nav = "Employee"
            st.rerun()

    with col_signin:
        st.markdown(
            f'<p style="text-align:center;color:{THEME["text_secondary"]};margin-bottom:12px">'
            f'Already have an account?</p>',
            unsafe_allow_html=True,
        )
        st.caption("Sign in using the sidebar →")

    st.markdown("---")
    st.caption(
        "Oraclaire is a burnout risk assessment tool. "
        "Sign in with your employee credentials to access your personal dashboard, "
        "or try the demo to see how it works."
    )


def page_employee():
    token = st.session_state.get("auth_token")
    employee_id = st.session_state.get("auth_employee_id")

    if not token or not employee_id:
        # Demo mode: full 5-screen UX with feature sliders to compute score
        demo_employee_id = st.text_input(
            "Your name or ID",
            value="EID_001",
            placeholder="e.g. Alex Chen",
            key="demo_emp_id",
        )

        # Feature sliders
        tenure_years = st.selectbox(
            "Time in this role",
            options=[0, 1, 2, 3, 4, 5],
            format_func=lambda x: [
                "< 6 months", "6–12 months", "1–2 years",
                "2–5 years", "5–10 years", "10+ years",
            ][x],
            index=2,
            key="demo_tenure",
        )
        tenure_map = {0: 90, 1: 270, 2: 547, 3: 1095, 4: 1825, 5: 2555}
        tenure_days = tenure_map.get(tenure_years, 547)

        energy = st.slider(
            "Energy level",
            min_value=1.0, max_value=10.0, value=5.0, step=0.5,
            help="1 = running on empty · 10 = feeling energized",
            key="demo_energy",
        )
        workload = st.slider(
            "Workload",
            min_value=0.0, max_value=10.0, value=5.0, step=0.5,
            help="0 =轻松应付 · 10 =不堪重负",
            key="demo_workload",
        )

        wfh = st.radio(
            "WFH setup",
            options=["Yes", "No", "N/A"],
            index=0, horizontal=True,
            key="demo_wfh",
        )
        wfh_setup = 1 if wfh == "Yes" else 0
        # 6-band MNC structure: Associate → VP/SVP
        # Maps to seniority_tier 0-5 for model scoring
        seniority_tier = st.selectbox(
            "Role level",
            options=[0, 1, 2, 3, 4, 5],
            format_func=lambda x: [
                "Associate / IC1",
                "Senior Associate / IC2",
                "Manager / IC3",
                "Senior Manager / IC4",
                "Director / VP / IC5",
                "Senior Director / SVP / IC6+",
            ][x],
            index=0,
            key="demo_seniority",
        )

        features = {
            "tenure_days": float(tenure_days),
            "mental_fatigue_score": float(energy),
            "resource_allocation": float(workload),
            "wfh_setup": float(wfh_setup),
            "company_type": 0.0,
            "seniority_tier": float(seniority_tier),
            "missing_ra": 0.0,
            "missing_mfs": 0.0,
            "tenure_fatigue": 5.0,
            "tenure_workload": 5.0,
        }

        st.markdown("---")
        if st.button("Run assessment", key="run_demo", use_container_width=True):
            # Bypass check-in screen go straight to result
            st.session_state.ux_demo_features = features
            st.session_state.ux_demo_seniority = seniority_tier
            st.session_state.ux_demo_employee_id = demo_employee_id
            st.session_state.ux_screen = "result"
            st.rerun()

        if st.session_state.get("ux_screen") in ("result", "factors", "resources", "trend", "done"):
            render_employee_ux(
                employee_id=st.session_state.get("ux_demo_employee_id", demo_employee_id),
                features=st.session_state.get("ux_demo_features", features),
                seniority_tier=st.session_state.get("ux_demo_seniority", seniority_tier),
            )
        else:
            st.info("Answer the questions above and click **Run assessment** to see your results.")

        st.caption(
            "Demo mode — results are calculated locally and never stored. "
            "Sign in to see your actual assessment."
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

    render_employee_ux(
        employee_id=employee_id,
        features=None,
        seniority_tier=None,
        risk_tier=latest.get("risk_tier"),
        burnout_probability=latest.get("numeric_score"),
        shap=shap_values,
        resources=resources,
        trajectory_data=trajectory_data,
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

    visibility_locked = trends_data.get("visibility_locked", False)
    locked_until = trends_data.get("visibility_locked_until")
    if visibility_locked:
        st.info(
            "Results are hidden for 24 hours after cycle close "
            "so employees see their scores first."
            + (f" Unlocks at {locked_until}." if locked_until else "")
        )

    tiers = trends_data.get("tiers", {"low": 0, "moderate": 0, "high": 0, "critical": 0})
    scores = [
        {"risk_tier": tier, "burnout_probability": None}
        for tier, count in tiers.items()
        for _ in range(count)
    ]
    teams = [
        {
            "name": t["name"],
            "team_size": t["member_count"],
            "high_critical_pct": t.get("high_critical_pct", 0.0),
            "consecutive_weeks_elevated": t.get("consecutive_weeks_elevated", 0),
        }
        for t in teams_data.get("teams", [])
    ]
    by_category = exclusions_data.get("by_category", {})
    exclusions = {
        "on_leave": by_category.get("on_leave", 0),
        "protected_process": by_category.get("protected_process", 0),
        "grievance_cooldown": by_category.get("grievance_cooldown", 0),
    }
    cycles = participation_data.get("cycles", [])
    responded = cycles[0].get("responded", 0) if cycles else 0
    scoreable = cycles[0].get("total_eligible", 0) if cycles else 0

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
        st.warning("Sign in to access the Manager dashboard.")
        return

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
    st.set_page_config(
        page_title="Oraclaire — Burnout Risk",
        page_icon=":brain:",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _inject_theme()
    ensure_model()

    if "auth_token" not in st.session_state:
        st.session_state.auth_token = None
    if "auth_employee_id" not in st.session_state:
        st.session_state.auth_employee_id = None
    if "auth_role" not in st.session_state:
        st.session_state.auth_role = None
    if "page_nav" not in st.session_state:
        st.session_state.page_nav = "Employee"
    if "ux_started" not in st.session_state:
        st.session_state.ux_started = False

    # Role display/selection
    role_display_map = {
        "employee": "Employee",
        "manager": "Manager",
        "hr_admin": "HR Admin",
        "system_admin": "System Admin",
    }

    with st.sidebar:
        st.markdown("### Oraclaire")
        st.caption("Burnout Risk Assessment")
        st.markdown("---")

        if not st.session_state.auth_token:
            st.markdown("**Sign in**")
            login_role = st.selectbox(
                "Your role",
                options=list(role_display_map.values()),
                index=0,
                label_visibility="collapsed",
            )
            login_emp_id = st.text_input(
                "Employee ID",
                value="",
                placeholder="e.g. 1",
                label_visibility="collapsed",
            )
            if st.button("Sign in", use_container_width=True, type="primary"):
                if not login_emp_id.strip():
                    st.warning("Enter your Employee ID.")
                else:
                    try:
                        auth_data = login(login_emp_id.strip())
                        st.session_state.auth_token = auth_data["token"]
                        st.session_state.auth_employee_id = login_emp_id.strip()
                        st.session_state.auth_role = auth_data.get("role", "")
                        # Determine initial page from actual returned role
                        actual_role = auth_data.get("role", "employee")
                        default_page = {
                            "employee": "Employee",
                            "manager": "Manager",
                            "hr_admin": "HR Aggregate",
                            "system_admin": "HR Aggregate",
                        }.get(actual_role, "Employee")
                        st.session_state.page_nav = default_page
                        st.rerun()
                    except ApiError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Login error: {e}")
        else:
            role_label = role_display_map.get(st.session_state.auth_role, st.session_state.auth_role)
            st.success(f"**{st.session_state.auth_employee_id}**")
            st.caption(f"Role: {role_label}")
            st.markdown("---")
            if st.button("Sign out", use_container_width=True):
                st.session_state.auth_token = None
                st.session_state.auth_employee_id = None
                st.session_state.auth_role = None
                st.session_state.page_nav = "Employee"
                st.session_state.ux_started = False
                st.rerun()

        st.markdown("---")
        st.markdown("#### Navigate")
        page_options = ["Employee", "HR Aggregate", "Manager", "Reviewer"]
        current_index = page_options.index(st.session_state.page_nav) if st.session_state.page_nav in page_options else 0
        page = st.selectbox(
            "View",
            options=page_options,
            index=current_index,
            label_visibility="collapsed",
        )
        st.session_state.page_nav = page

    # Show landing page when not logged in and demo not started
    if not st.session_state.auth_token and not st.session_state.get("ux_started"):
        page_landing()
        return

    if page == "Employee":
        page_employee()
    elif page == "HR Aggregate":
        page_hr()
    elif page == "Manager":
        page_manager()
    elif page == "Reviewer":
        if not st.session_state.auth_token:
            st.warning("Sign in to access the Reviewer queue.")
            return
        role = st.session_state.get("auth_role", "")
        if role not in ("system_admin", "hr_admin"):
            st.error("Access denied. The Review Queue is only available to Administrators.")
            return
        page_reviewer(st.session_state.auth_token)


if __name__ == "__main__":
    main()
