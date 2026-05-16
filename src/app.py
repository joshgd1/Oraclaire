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
    AuthExpiredError,
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
    logout,
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


def _clear_auth():
    """Clear auth session state after token expiry."""
    for key in ["auth_token", "auth_employee_id", "auth_role"]:
        st.session_state[key] = None
    st.session_state.page_nav = "Employee"
    st.session_state.ux_started = False


def ensure_model():
    """Train model if artifact doesn't exist."""
    from src.config import MODEL_ARTIFACT_PATH

    if not Path(MODEL_ARTIFACT_PATH).exists():
        with st.spinner("Training model on clean dataset..."):
            train_model()
        st.success("Model trained and saved.")


def page_landing():
    """Split-screen login — Traveler-inspired.

    Left panel: teal gradient with branding, headline, feature pills.
    Right panel: white form card with role selector, employee ID, demo CTA.

    Uses fixed positioning so the split-screen is fully isolated from
    Streamlit's global CSS — no global theme overrides that persist after login.

    The entire login UI (both panels + form fields) is rendered via a single
    st.html() call so all elements land in the DOM together, immune to
    Streamlit's structural DOM rendering quirks.
    """
    import urllib.parse

    # Read current query params to detect form submission
    qp = st.query_params
    submitted_emp_id = qp.get("login_emp_id", "")
    demo_mode = qp.get("demo", "")

    # ── Clear params after reading (prevent URL accumulation) ────────────
    if submitted_emp_id or demo_mode:
        qp.clear()
        if demo_mode:
            st.session_state.ux_started = True
            st.session_state.page_nav = "Employee"
            st.rerun()
        elif submitted_emp_id:
            emp_id = submitted_emp_id.strip()
            if not emp_id:
                st.warning("Enter your Employee ID.")
            else:
                failed = st.session_state.get("login_failed_attempts", 0)
                if failed >= 5:
                    st.error("Too many failed attempts. Please wait a moment before trying again.")
                else:
                    try:
                        auth_data = login(emp_id)
                        st.session_state.login_failed_attempts = 0
                        st.session_state.auth_token = auth_data["token"]
                        st.session_state.auth_employee_id = emp_id
                        st.session_state.auth_role = auth_data.get("role", "")
                        actual_role = auth_data.get("role", "employee")
                        default_page = {
                            "employee": "Employee",
                            "manager": "Manager",
                            "hr_admin": "HR Aggregate",
                            "system_admin": "HR Aggregate",
                        }.get(actual_role, "Employee")
                        st.session_state.page_nav = default_page
                        st.rerun()
                    except AuthExpiredError:
                        st.session_state.auth_token = None
                        st.session_state.auth_employee_id = None
                        st.session_state.auth_role = None
                        st.session_state.page_nav = "Employee"
                        st.session_state.ux_started = False
                        st.error("Session expired. Please sign in again.")
                    except ApiError as e:
                        st.session_state.login_failed_attempts = failed + 1
                        remaining = max(0, 5 - st.session_state.login_failed_attempts)
                        msg = str(e)
                        if remaining == 0:
                            msg += " (locked out — too many attempts)"
                        st.error(msg)
                    except Exception as e:
                        st.error(f"Login error: {e}")
            return

    # ── Full login page via single st.html() call ────────────────────────
    st.html(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500;600;700&display=swap');

        section[data-testid="stMain"] {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            overflow: hidden !important;
            background: #ffffff !important;
        }
        [data-testid="stSidebar"] { display: none !important; }

        div.login-left {
            position: fixed !important;
            top: 0 !important; left: 0 !important;
            width: 40vw !important; height: 100vh !important;
            background: linear-gradient(155deg, #0a3d47 0%, #0d5650 35%, #0d7377 60%, #14919b 100%);
            display: flex !important; flex-direction: column !important;
            justify-content: center !important;
            padding: 60px 52px !important;
            box-sizing: border-box !important;
            overflow: hidden !important; z-index: 1 !important;
        }
        div.login-right {
            position: fixed !important;
            top: 0 !important; right: 0 !important;
            width: 60vw !important; height: 100vh !important;
            background: #ffffff !important;
            display: flex !important; align-items: center !important;
            justify-content: center !important;
            padding: 60px 48px !important;
            box-sizing: border-box !important;
            overflow-y: auto !important; z-index: 1 !important;
        }
        div.login-card {
            width: 100% !important; max-width: 420px !important;
        }
        div.login-blob1 {
            position: absolute !important; top: -120px !important; right: -100px !important;
            width: 420px !important; height: 420px !important;
            border-radius: 50% !important;
            background: rgba(20,145,155,0.22) !important;
            filter: blur(60px) !important; pointer-events: none !important;
        }
        div.login-blob2 {
            position: absolute !important; bottom: -80px !important; left: -60px !important;
            width: 320px !important; height: 320px !important;
            border-radius: 50% !important;
            background: rgba(13,115,119,0.35) !important;
            filter: blur(50px) !important; pointer-events: none !important;
        }
        div.login-dot1 {
            position: absolute !important; top: 80px !important; right: 50px !important;
            width: 14px !important; height: 14px !important;
            border-radius: 50% !important;
            background: rgba(255,255,255,0.25) !important; pointer-events: none !important;
        }
        div.login-dot2 {
            position: absolute !important; bottom: 140px !important; left: 40px !important;
            width: 8px !important; height: 8px !important;
            border-radius: 50% !important;
            background: rgba(255,255,255,0.18) !important; pointer-events: none !important;
        }
        .login-label {
            font-family: 'Inter', sans-serif !important;
            font-size: 0.8rem !important; font-weight: 600 !important;
            color: #374151 !important; margin-bottom: 6px !important;
            display: block !important;
        }
        .login-select, .login-input {
            width: 100% !important;
            border-radius: 10px !important; border: 1.5px solid #e5e7eb !important;
            background: #f9fafb !important; color: #111827 !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.9rem !important; padding: 10px 14px !important;
            box-sizing: border-box !important;
            transition: border-color 0.15s !important;
            outline: none !important;
        }
        .login-select:focus, .login-input:focus {
            border-color: #0d7377 !important;
            background: #ffffff !important;
            box-shadow: 0 0 0 3px rgba(13,115,119,0.1) !important;
        }
        .login-input::placeholder { color: #9ca3af !important; }
        .btn-primary {
            width: 100% !important; background: #0d7377 !important;
            color: #ffffff !important; border: none !important;
            border-radius: 10px !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.9rem !important; font-weight: 600 !important;
            padding: 11px 20px !important;
            cursor: pointer !important;
            transition: background 0.15s, transform 0.1s !important;
            margin-top: 4px !important;
        }
        .btn-primary:hover { background: #0a5f66 !important; transform: translateY(-1px) !important; }
        .btn-demo {
            width: 100% !important; background: #f3f4f6 !important;
            color: #374151 !important; border: 1.5px solid #d1d5db !important;
            border-radius: 10px !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.9rem !important; font-weight: 600 !important;
            padding: 10px 20px !important;
            cursor: pointer !important;
            transition: background 0.15s !important;
            margin-top: 4px !important;
        }
        .btn-demo:hover { background: #e5e7eb !important; }
        .stMainBlockContainer {
            width: 100% !important; max-width: 100% !important; padding: 0 !important;
        }
        </style>

        <div class="login-left">
            <div class="login-blob1"></div>
            <div class="login-blob2"></div>
            <div class="login-dot1"></div>
            <div class="login-dot2"></div>

            <div style="display:inline-flex;align-items:center;gap:12px;margin-bottom:48px;position:relative;z-index:1">
                <div style="width:44px;height:44px;background:rgba(255,255,255,0.15);border-radius:12px;
                            display:flex;align-items:center;justify-content:center;
                            backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,0.2)">
                    <span style="font-size:1.4rem">🧠</span>
                </div>
                <span style="font-family:'Inter',sans-serif;font-size:1.15rem;font-weight:700;
                            color:#ffffff;letter-spacing:-0.01em">Oraclaire</span>
            </div>

            <h1 style="font-family:'DM Serif Display',Georgia,serif;font-size:2.8rem;font-weight:400;
                      color:#ffffff;line-height:1.18;margin:0 0 20px 0;letter-spacing:-0.02em;
                      position:relative;z-index:1">Your wellbeing,<br>protected.</h1>

            <p style="font-family:'Inter',sans-serif;font-size:0.95rem;font-weight:400;
                      color:rgba(255,255,255,0.72);line-height:1.65;margin:0 0 52px 0;
                      max-width:300px;position:relative;z-index:1">
                Burnout risk insights for you and your team — private, collaborative, and early.
                Used by HR teams at forward-thinking companies.
            </p>

            <div style="position:relative;z-index:1">
                <div style="display:inline-flex;align-items:center;gap:8px;
                            background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.18);
                            border-radius:100px;padding:7px 14px;margin-bottom:10px;margin-right:8px">
                    <span style="font-size:0.8rem">🔒</span>
                    <span style="font-family:'Inter',sans-serif;font-size:0.78rem;font-weight:500;
                                color:rgba(255,255,255,0.88)">End-to-end encrypted</span>
                </div>
                <div style="display:inline-flex;align-items:center;gap:8px;
                            background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.18);
                            border-radius:100px;padding:7px 14px;margin-bottom:10px;margin-right:8px">
                    <span style="font-size:0.8rem">👥</span>
                    <span style="font-family:'Inter',sans-serif;font-size:0.78rem;font-weight:500;
                                color:rgba(255,255,255,0.88)">Managers see trends only</span>
                </div>
                <div style="display:inline-flex;align-items:center;gap:8px;
                            background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.18);
                            border-radius:100px;padding:7px 14px;margin-bottom:10px;margin-right:8px">
                    <span style="font-size:0.8rem">✓</span>
                    <span style="font-family:'Inter',sans-serif;font-size:0.78rem;font-weight:500;
                                color:rgba(255,255,255,0.88)">HR-validated methodology</span>
                </div>
            </div>

            <div style="position:absolute;bottom:32px;left:52px;font-family:'Inter',sans-serif;
                        font-size:0.72rem;color:rgba(255,255,255,0.38);z-index:1">
                © 2026 Oraclaire. All rights reserved.
            </div>
        </div>

        <div class="login-right">
            <div class="login-card">
                <div style="margin-bottom:32px">
                    <h2 style="font-family:'Inter',sans-serif;font-size:1.55rem;font-weight:700;
                              color:#111827;margin:0 0 8px 0;letter-spacing:-0.025em">
                        Sign in to Oraclaire
                    </h2>
                    <p style="font-family:'Inter',sans-serif;font-size:0.875rem;color:#6b7280;
                              margin:0;line-height:1.5">
                        Access your personalised burnout risk dashboard
                    </p>
                </div>

                <form id="loginForm" method="GET" style="display:flex;flex-direction:column;gap:16px">
                    <div>
                        <label class="login-label" for="roleSelect">Your role</label>
                        <select class="login-select" id="roleSelect" name="role">
                            <option value="employee">Employee</option>
                            <option value="manager">Manager</option>
                            <option value="hr_admin">HR Admin</option>
                            <option value="system_admin">System Admin</option>
                        </select>
                    </div>
                    <div>
                        <label class="login-label" for="empIdInput">Employee ID</label>
                        <input class="login-input" type="text" id="empIdInput" name="emp_id"
                               placeholder="e.g. 1" autocomplete="off" />
                    </div>
                    <div style="display:flex;gap:10px;margin-top:4px">
                        <button class="btn-demo" type="button" id="demoBtn">Try demo</button>
                        <button class="btn-primary" type="submit">Sign in</button>
                    </div>
                </form>

                <script>
                document.getElementById('demoBtn').addEventListener('click', function() {
                    var form = document.getElementById('loginForm');
                    var input = document.createElement('input');
                    input.type = 'hidden'; input.name = 'demo'; input.value = '1';
                    form.appendChild(input);
                    form.submit();
                });
                </script>
            </div>
        </div>
        """
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
    except AuthExpiredError:
        _clear_auth()
        st.rerun()
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
    except AuthExpiredError:
        _clear_auth()
        st.rerun()
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
    except AuthExpiredError:
        _clear_auth()
        st.rerun()
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
    except AuthExpiredError:
        _clear_auth()
        st.rerun()
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
    try:
        render_reviewer_view(token=token)
    except AuthExpiredError:
        _clear_auth()
        st.rerun()


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
    if "login_failed_attempts" not in st.session_state:
        st.session_state.login_failed_attempts = 0

    # Role display/selection
    role_display_map = {
        "employee": "Employee",
        "manager": "Manager",
        "hr_admin": "HR Admin",
        "system_admin": "System Admin",
    }

    # Sidebar only shown to logged-in users
    if st.session_state.auth_token:
        with st.sidebar:
            st.markdown("### Oraclaire")
            st.caption("Burnout Risk Assessment")
            st.markdown("---")

            role_label = role_display_map.get(st.session_state.auth_role, st.session_state.auth_role)
            st.success(f"**{st.session_state.auth_employee_id}**")
            st.caption(f"Role: {role_label}")
            st.markdown("---")
            if st.button("Sign out", use_container_width=True):
                logout(st.session_state.get("auth_token", ""))
                _clear_auth()
                st.session_state.login_failed_attempts = 0
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
    else:
        # Not logged in — show landing page (no sidebar)
        if not st.session_state.get("ux_started"):
            page_landing()
        else:
            # Demo in progress — show demo assessment with no sidebar
            st.session_state.page_nav = "Employee"
            page_employee()


if __name__ == "__main__":
    main()
