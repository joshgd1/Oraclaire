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
    "bg": "#0d7377",
    "card_bg": "#f0faf9",
    "primary": "#0d7377",
    "primary_light": "#14919b",
    "text": "#111827",
    "text_secondary": "#6b7280",
    "border": "#d1fae5",
    "low_color": "#059669",
    "moderate_color": "#d97706",
    "high_color": "#ea580c",
    "critical_color": "#dc2626",
    "sidebar_bg": "#0a3d47",
    "sidebar_text": "#e5e7eb",
    "page_bg": "#ffffff",
}


def _sidebar_html_full(name: str, role_label: str, role: str, nav_html: str) -> str:
    """Render the full sidebar as a single HTML block for complete design control."""

    # One compact info card per role (not 3-4)
    role_guide = {
        "employee": (
            "🔒 <strong>Privacy</strong> — Only you see your individual scores. "
            "Managers and HR see team averages only."
        ),
        "manager": (
            "📈 <strong>ORT</strong> — Fraction of team in High or Critical. "
            "Exceeds 20% → team flagged for review. "
            "You cannot see individual scores or who responded."
        ),
        "hr_admin": (
            "🚨 <strong>ORT ceiling 20%</strong> — Critical capped at 5% of scorable population. "
            "Individual answers are never visible to managers."
        ),
        "system_admin": (
            "🚨 <strong>ORT ceiling 20%</strong> — Critical capped at 5% of scorable population. "
            "Individual answers are never visible to managers."
        ),
    }

    guide_text = role_guide.get(role, role_guide["employee"])
    card_html = (
        f'<div class="sb-card">'
        f'<p class="sb-card-body">{guide_text}</p>'
        f'</div>'
    )

    role_badge_color = {
        "employee": "#0d7377",
        "manager": "#7c3aed",
        "hr_admin": "#b45309",
        "system_admin": "#b45309",
    }.get(role, "#0d7377")

    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* Brand header */
.sb-brand {{
    padding: 4px 0 18px 0;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    margin-bottom: 14px;
}}
.sb-brand-name {{
    font-family: 'Inter', sans-serif;
    font-size: 1.15rem;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.01em;
    margin: 0 0 2px 0;
}}
.sb-brand-sub {{
    font-family: 'Inter', sans-serif;
    font-size: 0.72rem;
    color: rgba(255,255,255,0.45);
    margin: 0;
}}

/* User card */
.sb-user {{
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 10px;
    padding: 11px 13px;
    margin-bottom: 14px;
}}
.sb-user-name {{
    font-family: 'Inter', sans-serif;
    font-size: 0.9rem;
    font-weight: 600;
    color: #ffffff;
    margin: 0 0 5px 0;
}}
.sb-user-role-badge {{
    display: inline-block;
    background: {role_badge_color};
    color: #ffffff;
    font-family: 'Inter', sans-serif;
    font-size: 0.68rem;
    font-weight: 600;
    padding: 2px 9px;
    border-radius: 100px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}}

/* Nav links */
.sb-nav-btn {{
    display: block;
    width: 100%;
    padding: 9px 13px;
    border-radius: 8px;
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.1);
    color: rgba(255,255,255,0.75);
    font-family: 'Inter', sans-serif;
    font-size: 0.82rem;
    font-weight: 500;
    text-decoration: none;
    text-align: left;
    margin-bottom: 7px;
    transition: background 0.15s, color 0.15s;
}}
.sb-nav-btn:hover {{
    background: rgba(255,255,255,0.13);
    color: #ffffff;
}}
.sb-nav-active {{
    display: block;
    width: 100%;
    padding: 9px 13px;
    border-radius: 8px;
    background: #0d7377;
    border: 1px solid rgba(13,115,119,0.4);
    color: #ffffff;
    font-family: 'Inter', sans-serif;
    font-size: 0.82rem;
    font-weight: 600;
    text-decoration: none;
    text-align: left;
    margin-bottom: 7px;
}}

/* Sign out */
.sb-signout {{
    display: block;
    width: 100%;
    padding: 8px 13px;
    border-radius: 8px;
    background: transparent;
    border: 1px solid rgba(255,255,255,0.15);
    color: rgba(255,255,255,0.5);
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    font-weight: 500;
    text-decoration: none;
    text-align: center;
    margin-top: 10px;
    transition: background 0.15s, color 0.15s;
}}
.sb-signout:hover {{
    background: rgba(255,255,255,0.06);
    color: rgba(255,255,255,0.8);
}}

/* Section label */
.sb-label {{
    font-family: 'Inter', sans-serif;
    font-size: 0.62rem;
    font-weight: 700;
    color: rgba(255,255,255,0.35);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin: 0 0 8px 2px;
}}

/* Info cards */
.sb-card {{
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 10px;
    padding: 11px 13px;
    margin-bottom: 8px;
}}
.sb-card-header {{
    display: flex;
    align-items: center;
    gap: 7px;
    margin-bottom: 5px;
}}
.sb-card-icon {{
    font-size: 0.85rem;
    flex-shrink: 0;
}}
.sb-card-heading {{
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    font-weight: 600;
    color: #ffffff;
    margin: 0;
}}
.sb-card-body {{
    font-family: 'Inter', sans-serif;
    font-size: 0.74rem;
    color: rgba(255,255,255,0.6);
    line-height: 1.5;
    margin: 0;
}}

/* Divider */
.sb-divider {{
    border: none;
    border-top: 1px solid rgba(255,255,255,0.1);
    margin: 12px 0;
}}
</style>

<div class="sb-brand">
    <p class="sb-brand-name">Oraclaire</p>
    <p class="sb-brand-sub">Burnout Risk Assessment</p>
</div>

<div class="sb-user">
    <p class="sb-user-name">{name}</p>
    <span class="sb-user-role-badge">{role_label}</span>
</div>

<p class="sb-label">Navigate</p>
{nav_html}

<hr class="sb-divider"/>

<p class="sb-label">Role guide</p>
{card_html}

<hr class="sb-divider"/>

<a href="?signout=1" class="sb-signout">Sign out</a>
"""


def _inject_theme():
    """Inject custom CSS matching the teal login page theme."""
    st.html(
        f"""
        <style>
        /* Page */
        .stApp, .stMainBlockContainer {{
            background: {THEME['page_bg']} !important;
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
            background: {THEME['primary']} !important;
            color: white !important;
        }}
        .stButton > button:hover {{
            background: {THEME['primary_light']} !important;
            transform: translateY(-1px) !important;
        }}
        /* Text inputs */
        .stTextInput > div > div > input, .stTextArea > div > div > textarea {{
            border-radius: 8px !important;
            border: 1px solid {THEME['border']} !important;
            background: white !important;
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
            border-left: 4px solid {THEME['primary']} !important;
            border-radius: 8px !important;
        }}
        [data-testid="stSuccess"] {{
            background: #f0fdf4 !important;
            border-left: 4px solid {THEME['low_color']} !important;
            border-radius: 8px !important;
        }}
        [data-testid="stWarning"] {{
            background: #fffbeb !important;
            border-left: 4px solid {THEME['moderate_color']} !important;
            border-radius: 8px !important;
        }}
        [data-testid="stError"] {{
            background: #fef2f2 !important;
            border-left: 4px solid {THEME['critical_color']} !important;
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


def _get_demo_features(emp_id: str) -> dict:
    """Generate deterministic demo features from employee ID.

    Each employee ID produces consistent but distinct features,
    so login 1, 2, 3 each show different risk profiles.
    """
    # Deterministic hash from employee ID string
    seed = sum(ord(c) * (i + 1) for i, c in enumerate(emp_id))

    # Map seed to distinct but plausible feature ranges
    # Mental fatigue: 3-8 (higher = more fatigued = higher risk)
    mental_fatigue = 3.0 + (seed % 50) / 10.0
    # Resource allocation: 4-9 (higher = more overloaded = higher risk)
    resource_alloc = 4.0 + ((seed * 7) % 50) / 10.0
    # Tenure days: 90-1200 (longer tenure = lower risk generally)
    tenure = 90.0 + (seed * 13) % 1110.0
    # Work setup: 0=wfh, 1=hybrid, 2=office
    wfh_setup = float((seed * 3) % 3)
    # Seniority: 1-4
    seniority = 1.0 + float((seed * 5) % 4)
    # Company type: 0-3
    company_type = float((seed * 11) % 4)

    return {
        "tenure_days": round(tenure, 1),
        "mental_fatigue_score": round(mental_fatigue, 1),
        "resource_allocation": round(resource_alloc, 1),
        "wfh_setup": round(wfh_setup, 1),
        "company_type": round(company_type, 1),
        "seniority_tier": round(seniority, 1),
        "missing_ra": 0.0,
        "missing_mfs": 0.0,
        "tenure_fatigue": round(mental_fatigue, 1),
        "tenure_workload": round(resource_alloc, 1),
    }


def _clear_auth():
    """Clear auth session state after token expiry or sign-out."""
    for key in ["auth_token", "auth_employee_id", "auth_role"]:
        st.session_state[key] = None
    st.session_state.page_nav = "Employee"
    st.session_state.ux_started = False
    # Wipe demo UX state so next login starts fresh
    for key in ["ux_screen", "ux_pulse", "ux_demo_features",
                 "ux_demo_seniority", "ux_demo_employee_id", "radar_values"]:
        st.session_state.pop(key, None)


def ensure_model():
    """Train model if artifact doesn't exist."""
    from src.config import MODEL_ARTIFACT_PATH

    if not Path(MODEL_ARTIFACT_PATH).exists():
        with st.spinner("Training model on clean dataset..."):
            train_model()
        st.success("Model trained and saved.")


# ── Login page ────────────────────────────────────────────────────────────────

def page_landing():
    """Split-screen login page rendered as pure HTML.

    Left panel: teal gradient with branding and feature pills.
    Right panel: white card with Employee ID field and Sign in button.
    Both panels and the form are in a single st.html() call so they render
    together in the DOM.
    """
    st.html(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500;600;700&display=swap');

        section[data-testid="stMain"] {
            position: fixed !important;
            top: 0 !important; left: 0 !important;
            width: 100vw !important; height: 100vh !important;
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
        .login-input {
            width: 100% !important;
            border-radius: 10px !important; border: 1.5px solid #e5e7eb !important;
            background: #f9fafb !important; color: #111827 !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.9rem !important; padding: 10px 14px !important;
            box-sizing: border-box !important;
            transition: border-color 0.15s !important;
            outline: none !important;
        }
        .login-input:focus {
            border-color: #0d7377 !important;
            background: #ffffff !important;
            box-shadow: 0 0 0 3px rgba(13,115,119,0.1) !important;
        }
        .login-input::placeholder { color: #9ca3af !important; }
        .login-input {
            width: 100% !important;
            border-radius: 10px !important; border: 1.5px solid #e5e7eb !important;
            background: #f9fafb !important; color: #111827 !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.9rem !important; padding: 10px 14px !important;
            box-sizing: border-box !important;
            transition: border-color 0.15s !important;
            outline: none !important;
            -webkit-appearance: none !important;
            appearance: none !important;
        }
        select.login-input {
            cursor: pointer !important;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%236b7280' d='M6 8L1 3h10z'/%3E%3C/svg%3E") !important;
            background-repeat: no-repeat !important;
            background-position: right 14px center !important;
            padding-right: 36px !important;
        }
        select.login-input:focus {
            border-color: #0d7377 !important;
            background-color: #ffffff !important;
            box-shadow: 0 0 0 3px rgba(13,115,119,0.1) !important;
        }
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
                        <label class="login-label" for="empIdInput">Employee ID</label>
                        <input class="login-input" type="text" id="empIdInput" name="emp_id"
                               placeholder="e.g. 1" autocomplete="off" />
                    </div>
                    <div>
                        <label class="login-label" for="roleSelect">Role</label>
                        <select class="login-input" id="roleSelect" name="role"
                                style="cursor:pointer">
                            <option value="employee">Employee</option>
                            <option value="hr_admin">HR Admin</option>
                            <option value="manager">Manager</option>
                        </select>
                    </div>
                    <button class="btn-primary" type="submit">Sign in</button>
                </form>

                <div style="margin-top:28px;padding-top:20px;border-top:1px solid #e5e7eb">
                    <p style="font-family:'Inter',sans-serif;font-size:0.75rem;font-weight:600;
                              color:#9ca3af;margin:0 0 12px 0;letter-spacing:0.05em;text-transform:uppercase">
                        Quick demo access
                    </p>
                    <div style="display:flex;flex-direction:column;gap:8px">
                        <a href="?emp_id=1&role=employee"
                           style="display:flex;align-items:center;gap:10px;padding:9px 12px;
                                  background:#f0fdfa;border:1px solid #99f6e4;border-radius:8px;
                                  text-decoration:none;font-family:'Inter',sans-serif;
                                  font-size:0.82rem;font-weight:500;color:#065f46">
                            <span>👤</span>
                            <span><strong>Employee 1</strong> — high risk demo</span>
                        </a>
                        <a href="?emp_id=2&role=employee"
                           style="display:flex;align-items:center;gap:10px;padding:9px 12px;
                                  background:#f0fdfa;border:1px solid #99f6e4;border-radius:8px;
                                  text-decoration:none;font-family:'Inter',sans-serif;
                                  font-size:0.82rem;font-weight:500;color:#065f46">
                            <span>👤</span>
                            <span><strong>Employee 2</strong> — low risk demo</span>
                        </a>
                        <a href="?emp_id=3&role=employee"
                           style="display:flex;align-items:center;gap:10px;padding:9px 12px;
                                  background:#f0fdfa;border:1px solid #99f6e4;border-radius:8px;
                                  text-decoration:none;font-family:'Inter',sans-serif;
                                  font-size:0.82rem;font-weight:500;color:#065f46">
                            <span>👤</span>
                            <span><strong>Employee 3</strong> — moderate risk demo</span>
                        </a>
                        <a href="?emp_id=manager1&role=manager"
                           style="display:flex;align-items:center;gap:10px;padding:9px 12px;
                                  background:#faf5ff;border:1px solid #e9d5ff;border-radius:8px;
                                  text-decoration:none;font-family:'Inter',sans-serif;
                                  font-size:0.82rem;font-weight:500;color:#6b21a8">
                            <span>📊</span>
                            <span><strong>Manager</strong> — team dashboard demo</span>
                        </a>
                        <a href="?emp_id=hr1&role=hr_admin"
                           style="display:flex;align-items:center;gap:10px;padding:9px 12px;
                                  background:#fffbeb;border:1px solid #fef08a;border-radius:8px;
                                  text-decoration:none;font-family:'Inter',sans-serif;
                                  font-size:0.82rem;font-weight:500;color:#92400e">
                            <span>📋</span>
                            <span><strong>HR Admin</strong> — org overview demo</span>
                        </a>
                    </div>
                </div>
            </div>
        </div>
        """
    )


def page_employee():
    token = st.session_state.get("auth_token")
    employee_id = st.session_state.get("auth_employee_id")
    role = st.session_state.get("auth_role")

    # Managers and HR don't take assessments — redirect to their dashboard
    if not token and role in ("manager", "hr_admin", "system_admin"):
        st.info(f"You're logged in as {role.replace('_', ' ').title()}. Use the sidebar to view your dashboard.")
        st.caption("The assessment is for employees only.")
        default_page = {
            "manager": "Manager",
            "hr_admin": "HR Aggregate",
            "system_admin": "HR Aggregate",
        }.get(role, "Employee")
        if st.button(f"Go to {role.replace('_', ' ').title()} Dashboard"):
            st.session_state.page_nav = default_page
            st.rerun()
        return

    if not token or not employee_id:
        # Demo mode: run the full employee UX flow locally (no backend needed).
        # Mirrors the real employee experience: disclosure → pulse → results → radar → factors.
        # Use demo employee ID and defaults for all inputs.
        if "ux_demo_features" not in st.session_state:
            # First time: initialise demo features with sensible defaults
            demo_id = employee_id or "Demo"
            demo_feats = _get_demo_features(demo_id)
            st.session_state.ux_demo_employee_id = demo_id
            st.session_state.ux_demo_seniority = int(demo_feats["seniority_tier"])
            st.session_state.ux_demo_features = demo_feats

        render_employee_ux(
            employee_id=st.session_state.ux_demo_employee_id,
            features=st.session_state.ux_demo_features,
            seniority_tier=st.session_state.ux_demo_seniority,
        )
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
        # Demo mode — render a mock HR dashboard with no backend needed
        render_hr_view(
            scores=[
                {"risk_tier": tier, "burnout_probability": None}
                for tier, count in (("low", 28), ("moderate", 18), ("high", 12), ("critical", 4))
                for _ in range(count)
            ],
            teams=[
                {"name": "Engineering", "member_count": 8, "high_critical_pct": 0.375, "consecutive_weeks_elevated": 2},
                {"name": "Product", "member_count": 6, "high_critical_pct": 0.167, "consecutive_weeks_elevated": 0},
                {"name": "Design", "member_count": 5, "high_critical_pct": 0.20, "consecutive_weeks_elevated": 1},
            ],
            exclusions={"on_leave": 2, "protected_process": 1, "grievance_cooldown": 0},
            scoreable=62,
            responded=52,
        )
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
        # Demo mode — render a mock manager dashboard with no backend needed
        render_manager_view(
            team_id=1,
            team_name="Engineering",
            team_size=8,
            suppressed=False,
            suppression_reason=None,
            visibility_locked=False,
            cycles=[{
                "cycle_type": "monthly",
                "closed_at": "2026-05-01",
                "tiers": {"low": 3, "moderate": 2, "high": 2, "critical": 1},
            }],
            tier_distribution={"low": 3, "moderate": 2, "high": 2, "critical": 1},
            high_critical_pct=0.375,
            consecutive_weeks_elevated=2,
            top_factors=[
                {"feature": "mental_fatigue_score", "avg_impact": 0.21, "direction": "increases"},
                {"feature": "resource_allocation", "avg_impact": 0.15, "direction": "increases"},
            ],
            recommendations=[
                "Workload negotiation guide",
                "Energy management toolkit",
            ],
            worst_tier="high",
            ort_ceiling=0.20,
            team_trajectory_data=None,
        )
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

    # ── Session state init ─────────────────────────────────────────────────
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

    # ── Handle login form submission via query params ─────────────────────────
    # This runs on EVERY page re-render (including after form submission),
    # so we check params before any page rendering to intercept the redirect.
    qp = st.query_params
    emp_id_param = qp.get("emp_id", "")
    role_param = qp.get("role", "employee")

    if emp_id_param:
        qp.clear()
        emp_id = emp_id_param.strip()
        if emp_id:
            failed = st.session_state.get("login_failed_attempts", 0)
            if failed >= 5:
                st.error("Too many failed attempts. Please wait a moment before trying again.")
            else:
                try:
                    auth_data = login(emp_id)
                    st.session_state.login_failed_attempts = 0
                    st.session_state.auth_token = auth_data["token"]
                    st.session_state.auth_employee_id = emp_id
                    # Use role from form if valid, otherwise from backend
                    st.session_state.auth_role = (
                        role_param
                        if role_param in ("employee", "manager", "hr_admin", "system_admin")
                        else auth_data.get("role", "employee")
                    )
                    actual_role = st.session_state.auth_role
                    default_page = {
                        "employee": "Employee",
                        "manager": "Manager",
                        "hr_admin": "HR Aggregate",
                        "system_admin": "HR Aggregate",
                    }.get(actual_role, "Employee")
                    st.session_state.page_nav = default_page
                except AuthExpiredError:
                    st.session_state.auth_token = None
                    st.session_state.auth_employee_id = None
                    st.session_state.auth_role = None
                    st.session_state.page_nav = "Employee"
                    st.session_state.ux_started = False
                    st.error("Session expired. Please sign in again.")
                except ApiError:
                    # No backend running — enter demo mode (no token needed for employee view)
                    st.session_state.login_failed_attempts = 0
                    st.session_state.auth_token = None  # demo mode: no backend
                    st.session_state.auth_employee_id = emp_id
                    st.session_state.auth_role = (
                        role_param
                        if role_param in ("employee", "manager", "hr_admin", "system_admin")
                        else "employee"
                    )
                    # Pre-load demo features keyed to the actual employee ID for this session
                    demo_feats = _get_demo_features(emp_id)
                    st.session_state.ux_demo_employee_id = emp_id
                    st.session_state.ux_demo_seniority = int(demo_feats["seniority_tier"])
                    st.session_state.ux_demo_features = demo_feats
                    st.session_state.ux_started = True  # ensure role routing fires next render
                    actual_role = st.session_state.auth_role
                    default_page = {
                        "employee": "Employee",
                        "manager": "Manager",
                        "hr_admin": "HR Aggregate",
                        "system_admin": "HR Aggregate",
                    }.get(actual_role, "Employee")
                    st.session_state.page_nav = default_page
                except Exception as e:
                    st.error(f"Login error: {e}")

    # ── Authenticated sidebar view ──────────────────────────────────────────
    if st.session_state.auth_token:
        role_display_map = {
            "employee": "Employee",
            "manager": "Manager",
            "hr_admin": "HR Admin",
            "system_admin": "System Admin",
        }

        role = st.session_state.auth_role
        role_label = role_display_map.get(role, role)
        name = st.session_state.auth_employee_id or "Unknown"
        is_demo = st.session_state.auth_token is None

        # Sidebar with role guide — shown for all authenticated users
        # Managers/HR in demo mode don't take assessments — skip "My Assessment" nav
        if is_demo and role == "manager":
            pages = [("Team Dashboard", "Manager")]
        elif is_demo and role in ("hr_admin", "system_admin"):
            pages = [("Org Overview", "HR Aggregate")]
        else:
            pages = {
                "manager": [("Team Dashboard", "Manager"), ("My Assessment", "Employee")],
                "hr_admin": [("Org Overview", "HR Aggregate"), ("Reviewer Queue", "Reviewer")],
                "system_admin": [("Org Overview", "HR Aggregate"), ("Reviewer Queue", "Reviewer")],
            }.get(role, [])

        current_page = st.session_state.page_nav
        nav_html = ""
        for label, page_name in pages:
            active = current_page == page_name
            cls = "sb-nav-active" if active else "sb-nav-btn"
            nav_html += f'<a href="?nav={page_name}" class="{cls}">{label}</a>'

        with st.sidebar:
            st.html(_sidebar_html_full(name, role_label, role, nav_html))

        # Handle sign-out via query param
        if qp.get("signout") == "1":
            qp["signout"] = ""
            logout(st.session_state.get("auth_token", ""))
            _clear_auth()
            st.session_state.login_failed_attempts = 0
            st.rerun()

        # Handle navigation via query params
        nav_param = qp.get("nav", "")
        if nav_param and nav_param != current_page:
            qp["nav"] = ""
            st.session_state.page_nav = nav_param
            st.rerun()

        page = st.session_state.page_nav

        if page == "Employee":
            page_employee()
        elif page == "Manager":
            page_manager()
        elif page == "HR Aggregate":
            page_hr()
        elif page == "Reviewer":
            if not st.session_state.auth_token:
                st.warning("Sign in to access the Reviewer queue.")
                return
            role = st.session_state.get("auth_role", "")
            if role not in ("system_admin", "hr_admin"):
                st.error(
                    "Access denied. The Review Queue is only available to Administrators."
                )
                return
            page_reviewer(st.session_state.auth_token)

    else:
        # Not logged in — show landing page (no sidebar)
        if not st.session_state.get("ux_started"):
            page_landing()
        else:
            # Route based on the role selected in the form (not the employee quiz)
            auth_role = st.session_state.get("auth_role")
            if auth_role == "manager":
                page_manager()
            elif auth_role == "hr_admin":
                page_hr()
            elif auth_role == "system_admin":
                page_hr()
            else:
                page_employee()


if __name__ == "__main__":
    main()
