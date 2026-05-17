"""
Employee-facing UX — 7-screen flow.

Screen 0: What to expect (intro, what we'll ask, privacy promise)
Screen 1: Weekly check-in (5 questions mapping to burnout drivers)
Screen 2: Your result (privacy notice, plain label, one action)
Screen 3: Wellbeing dimensions (radar chart, all 8 axes)
Screen 4: What is affecting this (three plain sentences)
Screen 5: What might help (matched resources, max 3)
Screen 6: Your trend (simple line, no numbers)

Mobile-first. No jargon. Privacy notice visible on every result screen.
Target audiences: employees using the app, business managers approving launch,
fellow developers inheriting the codebase.
"""

from typing import Literal

import plotly.graph_objects as go
import streamlit as st

from src.config import FEATURE_LABELS, RESOURCES
from src.model.serve import score_employee

# ── Theme ────────────────────────────────────────────────────────────────────

THEME = {
    "low": "#10b981",
    "moderate": "#f59e0b",
    "high": "#f97316",
    "critical": "#ef4444",
    "text": "#e5e7eb",
    "text_secondary": "#9ca3af",
    "card_bg": "#2a2a3e",
    "border": "#3d3d5c",
    "bg": "#1e1e2e",
}

# ── Plain-language label map ────────────────────────────────────────────────

TIER_LABELS = {
    "low": "You seem to be doing well right now",
    "moderate": "A few things worth keeping an eye on",
    "high": "Some signs worth paying attention to",
    "critical": "This might be a good time to reach out for support",
}

TIER_DESCRIPTIONS = {
    "low": "Your recent patterns suggest things are stable. Keep doing what's working.",
    "moderate": "There are a couple of areas that might be worth paying attention to.",
    "high": "You're showing some signs that things are getting difficult. Support is available.",
    "critical": "Your responses suggest things are really tough right now. Please consider reaching out.",
}

# Plain-language signal labels shown alongside the tier badge (no numbers)
SIGNAL_LABELS = {
    "low": "Signs of stability",
    "moderate": "Some strain showing",
    "high": "Elevated pressure",
    "critical": "High strain — support needed",
}

# ── Privacy notice ──────────────────────────────────────────────────────────

PRIVACY_NOTICE = (
    "Only you can see this. Your manager and HR see team averages only."
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _privacy_card():
    st.markdown(
        f'<div style="background:#0d737720;border:1px solid #0d737740;'
        f'border-radius:10px;padding:12px 16px;margin-bottom:20px">'
        f'<p style="margin:0;color:{THEME["text"]};font-size:0.88rem;font-weight:500">'
        f"🔒 {PRIVACY_NOTICE}</p></div>",
        unsafe_allow_html=True,
    )


def _render_tier_badge(tier: str):
    """Colored badge showing tier name + plain-language signal label."""
    color = THEME.get(tier.lower(), "#888")
    signal = SIGNAL_LABELS.get(tier.lower(), "")
    tier_display = tier.upper()

    st.markdown(
        f'<div style="display:inline-flex;align-items:center;gap:16px;'
        f'padding:16px 24px;border-radius:12px;background:{color}18;'
        f'border:1px solid {color}44;margin-bottom:20px">'
        f'<span style="font-size:1.6rem;font-weight:800;color:{color};'
        f'text-transform:uppercase;letter-spacing:0.05em">{tier_display}</span>'
        f'<span style="color:{THEME["text_secondary"]};font-size:0.95rem">'
        f'{signal}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )


def _section_title(text: str):
    st.markdown(
        f'<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.08em;color:{THEME["text_secondary"]};margin:0 0 12px 0">'
        f"{text}</p>",
        unsafe_allow_html=True,
    )


def _card(content_fn, *args, **kwargs):
    with st.container():
        st.markdown(
            f'<div style="background:{THEME["card_bg"]};border:1px solid {THEME["border"]};'
            f'border-radius:14px;padding:24px;margin-bottom:16px;'
            f'box-shadow:0 1px 4px rgba(0,0,0,0.2)">',
            unsafe_allow_html=True,
        )
        content_fn(*args, **kwargs)
        st.markdown("</div>", unsafe_allow_html=True)


# ── Assessment questions ─────────────────────────────────────────────────────
# Questions map to burnout drivers. Labels are plain-language;
# internal names map to model features.
# To change a question, edit only the dictionaries below.

ASSESSMENT_QUESTIONS = [
    {
        "id": "workload",
        "question": "How would you describe your workload this week?",
        "subtext": "Consider tasks, deadlines, and how busy you've been.",
        "feature": "resource_allocation",
        "options": [
            ("Very light — plenty of downtime", 1),
            ("Manageable — I kept on top of things", 2),
            ("Busy — but sustainable", 3),
            ("Very busy — regularly overtime", 4),
            ("Overwhelming — couldn't keep up", 5),
        ],
    },
    {
        "id": "energy",
        "question": "How would you describe your energy levels this week?",
        "subtext": "How full did your energy reserves feel day to day?",
        "feature": "mental_fatigue_score",
        "options": [
            ("Fully recharged — always had energy", 1),
            ("Mostly good — occasional dips", 2),
            ("Moderate — some fatigue creeping in", 3),
            ("Low energy most days", 4),
            ("Exhausted — running on empty", 5),
        ],
    },
    {
        "id": "sleep",
        "question": "How well did you recover between workdays?",
        "subtext": "Think about sleep quality and whether work followed you home.",
        "feature": "mental_fatigue_score",
        "options": [
            ("Fully switched off — work didn't follow me", 1),
            ("Mostly relaxed — occasional thoughts", 2),
            ("Some tension — found it hard to fully unwind", 3),
            ("Often still thinking about work", 4),
            ("Could never properly switch off", 5),
        ],
    },
    {
        "id": "pressure",
        "question": "Did you notice any signs of excessive pressure?",
        "subtext": "Physical or emotional signals that things were too much.",
        "feature": "resource_allocation",
        "options": [
            ("None — felt calm throughout", 1),
            ("Minor — a few moments of strain", 2),
            ("Some — felt stretched at times", 3),
            ("Significant — several difficult days", 4),
            ("Severe — constantly under pressure", 5),
        ],
    },
    {
        "id": "support",
        "question": "How well supported did you feel at work?",
        "subtext": "Whether you had the resources, help, or backing you needed.",
        "feature": "wfh_setup",
        "options": [
            ("Fully supported — always had what I needed", 1),
            ("Mostly supported — small gaps", 2),
            ("Somewhat — a few things were missing", 3),
            ("Often unsupported — struggling at times", 4),
            ("No real support — isolated and stretched", 5),
        ],
    },
]


def _privacy_badge():
    """Shown at the top of every screen."""
    st.markdown(
        '<div style="background:#f0fdfa;border:1px solid #99f6e4;'
        'border-radius:10px;padding:10px 16px;margin-bottom:20px">'
        '<p style="margin:0;color:#065f46;font-size:0.85rem;font-weight:500">'
        '🔒 Your answers are private. Only team-level trends are visible to managers and HR.</p></div>',
        unsafe_allow_html=True,
    )


# ── Screen 0: What to expect ──────────────────────────────────────────────

def screen_intro() -> None:
    """Intro screen — explains what we'll ask and why."""

    # Header
    st.markdown(
        f'<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.08em;color:{THEME["text_secondary"]};margin:0 0 4px 0">'
        f"Weekly check-in</p>",
        unsafe_allow_html=True,
    )
    st.title("A quick check on how you're doing")

    # Privacy badge — always visible at top
    _privacy_badge()

    # Time estimate callout — prominent but clean
    st.markdown(
        f'<div style="background:{THEME["card_bg"]};border:1px solid {THEME["border"]};'
        f'border-radius:12px;padding:16px 20px;margin-bottom:24px;'
        f'display:flex;align-items:center;gap:14px">'
        f'<span style="font-size:1.5rem">⏱️</span>'
        f'<div>'
        f'<p style="margin:0;color:{THEME["text"]};font-size:1rem;font-weight:600">'
        f'Takes about 60 seconds</p>'
        f'<p style="margin:0;color:{THEME["text_secondary"]};font-size:0.85rem">'
        f'Five short questions, plain language</p>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # What we measure — icon cards in a clean grid
    _section_title("What we're checking")
    dimensions = [
        ("⚡", "Workload", "How busy you've been and whether it's sustainable"),
        ("🔋", "Energy", "Whether your energy levels have been holding up"),
        ("😴", "Recovery", "How well you've been switching off outside work"),
        ("📈", "Pressure", "Any signs you were being stretched too far"),
        ("🤝", "Support", "Whether you had the resources and backing you needed"),
    ]

    # Render as a 2-column grid of cards
    cols = st.columns(2)
    for i, (icon, dim, desc) in enumerate(dimensions):
        with cols[i % 2]:
            st.markdown(
                f'<div style="background:{THEME["card_bg"]};border:1px solid {THEME["border"]};'
                f'border-radius:10px;padding:14px 16px;margin-bottom:10px;'
                f'display:flex;align-items:flex-start;gap:12px">'
                f'<span style="font-size:1.3rem;flex-shrink:0;margin-top:1px">{icon}</span>'
                f'<div>'
                f'<p style="margin:0 0 2px 0;color:{THEME["text"]};'
                f'font-size:0.95rem;font-weight:600">{dim}</p>'
                f'<p style="margin:0;color:{THEME["text_secondary"]};font-size:0.82rem;'
                f'line-height:1.4">{desc}</p>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

    # Divider — the Start button lives in render_employee_ux
    st.markdown("---")


# ── Screen 1: Weekly check-in ──────────────────────────────────────────────

def screen_checkin(on_submit) -> int | None:
    """Multi-question check-in. Returns pulse (1-5) or None when cancelled."""
    questions = ASSESSMENT_QUESTIONS
    total = len(questions)
    q_num = st.session_state.get("ux_q_num", 1)

    # Privacy badge at top
    _privacy_badge()

    if q_num > total:
        # All questions answered — compute aggregate pulse and advance
        answers = st.session_state.get("ux_answers", {})
        raw_score = sum(answers.values()) / len(answers)
        pulse = max(1, min(5, round(raw_score)))
        on_submit(pulse)
        return

    # Progress header
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown(
            f'<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.08em;color:{THEME["text_secondary"]};margin:0">'
            f"Question {q_num} of {total}</p>",
            unsafe_allow_html=True,
        )
    with col2:
        # Progress bar
        progress = q_num / total
        st.progress(progress, text="")

    # Current question
    q = questions[q_num - 1]
    st.title(q["question"])

    # Subtext with better styling
    st.markdown(
        f'<p style="color:{THEME["text_secondary"]};font-size:0.95rem;'
        f'margin-bottom:28px;line-height:1.5">'
        f"{q['subtext']}</p>",
        unsafe_allow_html=True,
    )

    # Record answer and advance
    answer_key = f"q_{q['id']}"
    selected = st.session_state.get(answer_key)

    # Show option buttons with intensity indicator
    # Color gradient: low intensity (green) → high intensity (red)
    intensity_colors = [
        ("#10b981", "#059669"),  # 1 - green
        ("#34d399", "#10b981"),  # 2 - light green
        ("#fbbf24", "#f59e0b"), # 3 - yellow/amber
        ("#fb923c", "#f97316"),  # 4 - orange
        ("#f87171", "#ef4444"),  # 5 - red
    ]

    for idx, (label, value) in enumerate(q["options"]):
        is_selected = (selected == value)
        bg_color, border_color = intensity_colors[idx]

        # Selected state card
        if is_selected:
            st.markdown(
                f'<div style="background:{bg_color}18;border:2px solid {bg_color};'
                f'border-radius:12px;padding:14px 18px;margin-bottom:10px;'
                f'display:flex;align-items:center;gap:12px">'
                f'<span style="color:{bg_color};font-size:1.1rem">✓</span>'
                f'<span style="color:{THEME["text"]};font-size:0.95rem;font-weight:500">'
                f'{label}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            # Normal button-like option
            if st.button(
                f"{label}",
                key=f"{answer_key}_{value}",
                use_container_width=True,
            ):
                st.session_state[answer_key] = value
                answers = st.session_state.get("ux_answers", {})
                answers[q["feature"]] = value
                st.session_state.ux_answers = answers
                st.session_state.ux_q_num = q_num + 1
                st.rerun()

    # Back button (not on first question)
    if q_num > 1:
        st.markdown("<br>", unsafe_allow_html=True)  # spacing
        if st.button("← Back", key="checkin_back", use_container_width=True):
            st.session_state.ux_q_num = q_num - 1
            st.rerun()

    return None


# ── Screen 2: Your result ──────────────────────────────────────────────────

def screen_result(tier: str, probability: float | None, on_see_factors) -> bool:
    """
    Show the result card with tier badge + plain label.
    Returns True if user clicked 'See what's behind this'.
    """
    label = TIER_LABELS.get(tier, "Here's your result")
    description = TIER_DESCRIPTIONS.get(tier, "")
    color = THEME.get(tier.lower(), "#888")

    st.markdown(
        f'<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.08em;color:{THEME["text_secondary"]};margin:0 0 4px 0">'
        f"Your result</p>",
        unsafe_allow_html=True,
    )

    _render_tier_badge(tier)
    st.title(label)

    _privacy_card()

    st.markdown(
        f'<div style="background:{color}18;border:1px solid {color}44;'
        f'border-radius:14px;padding:24px;margin-bottom:20px;text-align:center">'
        f'<p style="color:{THEME["text"]};font-size:1.05rem;margin:0;line-height:1.6">'
        f"{description}</p></div>",
        unsafe_allow_html=True,
    )

    return st.button(
        "See what's affecting this",
        key="see_factors",
        use_container_width=True,
    )


# ── Screen 3: What is affecting this ──────────────────────────────────────

def screen_factors(shap_decomposition: list[dict], on_see_help) -> bool:
    """
    Show top 3 plain-sentence factors.
    Returns True if user clicked 'See what might help'.
    """
    st.markdown(
        f'<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.08em;color:{THEME["text_secondary"]};margin:0 0 4px 0">'
        f"What is affecting this</p>",
        unsafe_allow_html=True,
    )
    st.title("What is driving this")

    _privacy_card()

    _section_title("The biggest factors right now")

    factors = [
        item for item in (shap_decomposition or [])
        if item.get("label") and item.get("feature") not in ("missing_ra", "missing_mfs")
    ][:3]

    if not factors:
        st.info("Not enough data yet to show what is affecting this.")
        return False

    for i, item in enumerate(factors, 1):
        feature = item.get("feature", "")
        label = FEATURE_LABELS.get(feature, item.get("label", ""))
        direction = item.get("direction", "")

        # Build a plain sentence
        if direction == "increases":
            sentence = _build_factor_sentence(label, increases=True)
        else:
            sentence = _build_factor_sentence(label, increases=False)

        color = "#ef4444" if direction == "increases" else "#10b981"
        icon = "↑" if direction == "increases" else "↓"

        txt = THEME["text"]
        card_bg = THEME["card_bg"]
        border = THEME["border"]
        st.markdown(
            f'<div style="display:flex;align-items:flex-start;gap:12px;'
            f'padding:16px;background:{card_bg};border:1px solid {border};'
            f'border-radius:10px;margin-bottom:10px">'
            f'<span style="font-size:1.1rem;color:{color};flex-shrink:0;margin-top:2px">{icon}</span>'
            '<p style="margin:0;color:' + txt + ';font-size:1rem;line-height:1.5">'
            + sentence + "</p></div>",
            unsafe_allow_html=True,
        )

    return st.button(
        "See what might help",
        key="see_help",
        use_container_width=True,
    )


def _build_factor_sentence(label: str, increases: bool) -> str:
    """Convert a feature label into a plain English sentence."""
    # Map feature keys to plain sentence templates
    sentences = {
        "tenure_days": (
            "The length of time you've been in this role is a factor right now."
            if increases
            else "How long you've been here is not adding to pressure right now."
        ),
        "mental_fatigue_score": (
            "Your recent energy levels are contributing to how you're feeling."
            if increases
            else "Your recent energy is helping offset other pressures."
        ),
        "resource_allocation": (
            "Your workload is having the biggest effect right now."
            if increases
            else "Your workload is not a major pressure right now."
        ),
        "wfh_setup": (
            "Your working arrangement is a factor in how you're doing."
            if increases
            else "Your working setup is not adding pressure."
        ),
        "seniority_tier": (
            "The demands of your role level are part of what you're managing."
            if increases
            else "Your role level is not adding pressure right now."
        ),
        "company_type": (
            "The nature of your organisation is part of your current situation."
            if increases
            else "Your organisation type is not a pressure right now."
        ),
    }
    return sentences.get(label, f"{label} is a factor in your result.")


# ── Screen 4: What might help ──────────────────────────────────────────────

def screen_resources(top_feature: str, tier: str, on_done) -> bool:
    """
    Show up to 3 resources matched to the top SHAP factor.
    Returns True if user clicked 'Done for now'.
    """
    st.markdown(
        f'<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.08em;color:{THEME["text_secondary"]};margin:0 0 4px 0">'
        f"What might help</p>",
        unsafe_allow_html=True,
    )
    st.title("Things that might help")

    _privacy_card()

    resources = RESOURCES.get(top_feature, [])
    if not resources:
        st.info(
            "No specific suggestions for this situation yet. "
            "Speaking with your manager or HR is always a good step."
        )
        return st.button("Done for now", key="done_no_resources", use_container_width=True)

    # Show top 3
    for resource in resources[:3]:
        st.markdown(
            f'<div style="padding:16px 20px;background:{THEME["card_bg"]};'
            f'border:1px solid {THEME["border"]};border-left:3px solid #0d7377;'
            f'border-radius:10px;margin-bottom:12px">'
            f'<p style="margin:0 0 4px 0;color:{THEME["text"]};font-weight:600;font-size:1rem">'
            f"{resource}</p></div>",
            unsafe_allow_html=True,
        )

    return st.button("Done for now", key="done", use_container_width=True)


# ── Screen 5: Wellbeing Dimensions Radar ───────────────────────────────────

def _compute_radar_from_features(features: dict, seniority_tier: int) -> dict:
    """Derive 0-100 risk scores for each wellbeing dimension from feature values."""

    def _scale(value: float, lo: float, hi: float, invert: bool = False) -> float:
        """Normalise value to 0-100, inverting if invert=True (lower raw = higher risk)."""
        normalized = (value - lo) / (hi - lo) if hi != lo else 0.5
        normalized = max(0.0, min(1.0, normalized))
        return round((1 - normalized if invert else normalized) * 100, 1)

    return {
        "Energy": _scale(
            features.get("mental_fatigue_score", 5.0), 1.0, 10.0, invert=True
        ),
        "Workload": _scale(
            features.get("resource_allocation", 5.0), 0.0, 10.0, invert=False
        ),
        "Tenure Pressure": _scale(
            features.get("tenure_days", 547), 0.0, 3650.0, invert=False
        ),
        "Work Arrangement": (
            100.0
            if features.get("wfh_setup", 1.0) == 0.0
            else 30.0
        ),
        "Role Demands": _scale(
            features.get("seniority_tier", 0.0), 0.0, 5.0, invert=False
        ),
        "Company Context": 50.0,  # not modifiable; neutral
        "Fatigue Trend": _scale(
            features.get("tenure_fatigue", 5.0), 0.0, 10.0, invert=True
        ),
        "Workload Trend": _scale(
            features.get("tenure_workload", 5.0), 0.0, 10.0, invert=False
        ),
    }


def _compute_radar_from_shap(shap_decomposition: list[dict]) -> dict:
    """Derive 0-100 risk scores from SHAP impact values.

    Uses normalised absolute SHAP impact so the largest-contributing
    dimension always scores 100; others scale proportionally.
    """
    feat_map = {item["feature"]: item["impact_value"] for item in shap_decomposition}

    impacts = {
        "Energy": abs(feat_map.get("mental_fatigue_score", 0)),
        "Workload": abs(feat_map.get("resource_allocation", 0)),
        "Tenure Pressure": abs(feat_map.get("tenure_days", 0)),
        "Work Arrangement": abs(feat_map.get("wfh_setup", 0)),
        "Role Demands": abs(feat_map.get("seniority_tier", 0)),
        "Company Context": abs(feat_map.get("company_type", 0)),
        "Fatigue Trend": abs(feat_map.get("tenure_fatigue", 0)),
        "Workload Trend": abs(feat_map.get("tenure_workload", 0)),
    }

    max_impact = max(impacts.values()) or 1.0
    return {dim: round((impact / max_impact) * 100, 1) for dim, impact in impacts.items()}


def _tier_color(tier: str) -> str:
    return {"low": "#10b981", "moderate": "#f59e0b", "high": "#f97316", "critical": "#ef4444"}.get(
        tier.lower(), "#0d7377"
    )


def _tier_color_rgba(tier: str, alpha: float = 0.18) -> str:
    """Return rgba() string for a tier hex color with configurable alpha."""
    hex_color = _tier_color(tier)
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"rgba({r},{g},{b},{alpha})"


def screen_radar(
    radar_values: dict,
    tier: str,
    on_see_factors,
):
    """
    Render the wellbeing dimensions radar chart.
    Returns True if user clicked 'See what's affecting this'.
    """
    st.markdown(
        f'<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.08em;color:{THEME["text_secondary"]};margin:0 0 4px 0">'
        f"Wellbeing dimensions</p>",
        unsafe_allow_html=True,
    )
    st.title("Your wellbeing at a glance")

    _privacy_card()

    _section_title("How you're doing across each dimension")

    # ── Build Plotly radar ──────────────────────────────────────────────
    dimensions = list(radar_values.keys())
    values = list(radar_values.values())

    tier_color = _tier_color(tier)

    fig = go.Figure(
        data=[
            go.Scatterpolar(
                r=values + [values[0]],  # close the polygon
                theta=dimensions + [dimensions[0]],
                fill="toself",
                fillcolor=_tier_color_rgba(tier),
                line_color=tier_color,
                line_width=2.5,
                marker=dict(size=6, color=tier_color),
                hoverinfo="r+theta",
            )
        ]
    )

    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                range=[0, 100],
                tickvals=[0, 25, 50, 75, 100],
                ticktext=["0", "25", "50", "75", "100"],
                tickfont=dict(color="#9ca3af", size=10),
                tickcolor="#3d3d5c",
                linecolor="#3d3d5c",
                gridcolor="#3d3d5c",
                showticklabels=True,
                side="clockwise",
            ),
            angularaxis=dict(
                tickfont=dict(color="#e5e7eb", size=11, family="Inter, sans-serif"),
                tickcolor="#3d3d5c",
                linecolor="#3d3d5c",
                gridcolor="#3d3d5c",
                rotation=90,
                direction="clockwise",
            ),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        margin=dict(l=20, r=20, t=20, b=20),
        height=420,
        width=None,
    )

    st.plotly_chart(fig, use_container_width=True)

    # Tier context label under the chart
    st.markdown(
        f'<p style="text-align:center;color:{THEME["text_secondary"]};'
        f'font-size:0.8rem;margin-top:-8px;margin-bottom:20px">'
        f"0 = lower risk &nbsp;·&nbsp; 100 = higher risk &nbsp;·&nbsp; "
        f'Your overall level: <strong style="color:{tier_color}">'
        f'{tier.upper()}</strong></p>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1, 1])
    with col2:
        see_factors = st.button(
            "See what's affecting this →",
            key="see_factors_from_radar",
            use_container_width=True,
        )
    with col1:
        if st.button("← Back", key="back_from_radar", use_container_width=True):
            st.session_state.ux_screen = "result"
            st.rerun()

    return see_factors


# ── Screen 6: Your trend ──────────────────────────────────────────────────

def screen_trend(trajectory_data: dict | None):
    """
    Simple trend — no numbers, no axes labels.
    """
    st.markdown(
        f'<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.08em;color:{THEME["text_secondary"]};margin:0 0 4px 0">'
        f"Your trend</p>",
        unsafe_allow_html=True,
    )
    st.title("How you've been doing")

    _privacy_card()

    if not trajectory_data:
        st.info(
            "Complete a couple more check-ins to see your trend over time."
        )
        return

    trajectory = trajectory_data.get("trajectory", "no_trajectory")

    if trajectory == "no_trajectory":
        st.info(
            "Complete a couple more check-ins to see your trend over time."
        )
        return

    # Build a plain-sentence description
    trend_sentences = {
        "improved": "You're doing better than you were. Keep it up.",
        "worsened": "Things have been harder lately. It might be worth talking to someone.",
        "held": "You're in a similar place to where you've been.",
    }
    sentence = trend_sentences.get(trajectory, "")

    # Show a simple directional card
    icons = {"improved": "↗", "worsened": "↘", "held": "→"}
    colors = {"improved": "#10b981", "worsened": "#ef4444", "held": "#f59e0b"}
    icon = icons.get(trajectory, "·")
    color = colors.get(trajectory, "#888")

    st.markdown(
        f'<div style="text-align:center;padding:32px 24px;background:{THEME["card_bg"]};'
        f'border:1px solid {THEME["border"]};border-radius:14px;margin-bottom:16px">'
        f'<div style="font-size:3rem;margin-bottom:8px;color:{color}">{icon}</div>'
        f'<p style="margin:0;color:{THEME["text"]};font-size:1.1rem;font-weight:500">'
        f"{sentence}</p></div>",
        unsafe_allow_html=True,
    )

    # Simple line chart — hide axes via CSS
    cycles = trajectory_data.get("history", [])
    if cycles:
        chart_data = {c.get("label", f"Check-in {i+1}"): c.get("value", 0) for i, c in enumerate(cycles)}
        st.line_chart(chart_data, height=180)
        st.caption(
            "This shows the direction of how you've been feeling — not the exact numbers."
        )


# ── Main render function ────────────────────────────────────────────────────

def render_employee_ux(
    employee_id: str,
    *,
    features: dict | None = None,
    seniority_tier: int | None = None,
    risk_tier: str | None = None,
    burnout_probability: float | None = None,
    shap: list[dict] | None = None,
    resources: list[str] | None = None,
    trajectory_data: dict | None = None,
):
    """
    Render the 5-screen employee UX.

    Two modes:
    - Demo / local: pass features + seniority_tier
    - API-backed:   pass risk_tier + burnout_probability + shap + resources
    """
    # ── Score computation (local mode) ──────────────────────────────────
    if features is not None and seniority_tier is not None:
        try:
            result = score_employee(
                employee_id=employee_id,
                features=features,
                seniority_tier=seniority_tier,
            )
        except FileNotFoundError:
            st.error("Model not found. Run: `python -m src.model.train`")
            return
        except ValueError as e:
            st.error(f"Input validation error: {e}")
            return

        tier = result["risk_tier"]
        probability = result.get("burnout_probability")
        shap_decomposition = result.get("shap", [])

        # Filter out internal features
        shap_decomposition = [
            item for item in shap_decomposition
            if item.get("feature") not in ("missing_ra", "missing_mfs")
            and item.get("label")
        ]
        shap_decomposition.sort(key=lambda x: abs(x.get("impact_value", 0)), reverse=True)

        top_feature = shap_decomposition[0].get("feature", "") if shap_decomposition else ""

        # Compute radar values for demo mode (from raw features)
        radar_values = _compute_radar_from_features(features, seniority_tier)

    else:
        if risk_tier is None:
            st.error("Provide features+seniority_tier or risk_tier.")
            return
        tier = risk_tier
        probability = burnout_probability
        shap_decomposition = shap or []
        top_feature = shap_decomposition[0].get("feature", "") if shap_decomposition else ""

        # Compute radar values for API mode (from SHAP decomposition)
        radar_values = _compute_radar_from_shap(shap_decomposition)

    # ── Store for radar screen ──────────────────────────────────────────────
    st.session_state.radar_values = radar_values

    # ── State machine: which screen are we on? ─────────────────────────────
    # States: intro → checkin → result → radar/factors/trend → resources → done
    if "ux_screen" not in st.session_state:
        st.session_state.ux_screen = "intro"

    # Reset check-in progress when starting a new assessment
    if st.session_state.ux_screen in ("intro", "done"):
        st.session_state.ux_q_num = 1
        st.session_state.ux_answers = {}

    screen = st.session_state.ux_screen

    # ── Screen 0: What to expect ────────────────────────────────────────
    if screen == "intro":
        screen_intro()
        # Start button — bottom of intro screen, right-aligned
        col_spacer, col_btn = st.columns([3, 1])
        with col_btn:
            if st.button("Start check-in →", key="start_checkin", use_container_width=True):
                st.session_state.ux_screen = "checkin"
                st.rerun()
        return

    # ── Screen 1: Weekly check-in ────────────────────────────────────────
    if screen == "checkin":
        def handle_pulse(value: int):
            st.session_state.ux_pulse = value
            st.session_state.ux_screen = "result"

        result = screen_checkin(handle_pulse)
        return  # form-based; no results to render here

    # ── Screen 2: Your result ────────────────────────────────────────────
    elif screen == "result":
        def on_see_factors():
            st.session_state.ux_screen = "factors"
            st.rerun()

        col_dim, col_trend = st.columns([1, 1])
        with col_dim:
            if st.button("See your dimensions →", key="see_radar", use_container_width=True):
                st.session_state.ux_screen = "radar"
                st.rerun()
        with col_trend:
            if st.button("See your trend →", key="see_trend", use_container_width=True):
                st.session_state.ux_screen = "trend"
                st.rerun()

        if screen_result(tier, probability, on_see_factors):
            return  # state updated, rerun will show next screen

    # ── Screen 3: Wellbeing dimensions (radar) ───────────────────────────
    elif screen == "radar":
        def on_see_factors():
            st.session_state.ux_screen = "factors"
            st.rerun()

        if screen_radar(
            st.session_state.get("radar_values", {}),
            tier,
            on_see_factors,
        ):
            return

        if st.button("← Back to my result", key="back_from_radar_main", use_container_width=True):
            st.session_state.ux_screen = "result"
            st.rerun()

    # ── Screen 4: What is affecting this ───────────────────────────────
    elif screen == "factors":
        def on_see_help():
            st.session_state.ux_screen = "resources"
            st.rerun()

        if screen_factors(shap_decomposition, on_see_help):
            return

        if st.button("← Back to my result", key="back_result", use_container_width=True):
            st.session_state.ux_screen = "result"
            st.rerun()

    # ── Screen 4: What might help ───────────────────────────────────────
    elif screen == "resources":
        def on_done():
            st.session_state.ux_screen = "done"
            st.rerun()

        if screen_resources(top_feature, tier, on_done):
            return

        if st.button("← Back", key="back_factors", use_container_width=True):
            st.session_state.ux_screen = "factors"
            st.rerun()

    # ── Screen 5: Your trend ────────────────────────────────────────────
    elif screen == "trend":
        screen_trend(trajectory_data)
        if st.button("← Back to my result", key="back_trend", use_container_width=True):
            st.session_state.ux_screen = "result"
            st.rerun()

    # ── Done state ─────────────────────────────────────────────────────
    elif screen == "done":
        st.markdown(
            f'<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.08em;color:{THEME["text_secondary"]};margin:0 0 4px 0">'
            f"Done</p>",
            unsafe_allow_html=True,
        )
        st.title("All done for now")

        _privacy_card()

        st.markdown(
            f'<div style="background:{THEME["card_bg"]};border:1px solid {THEME["border"]};'
            f'border-radius:14px;padding:24px;margin-bottom:16px;text-align:center">'
            f'<p style="color:{THEME["text"]};font-size:1.05rem;margin:0;line-height:1.6">'
            f"Come back next week and we'll check in again. "
            f"Your trend builds over time.</p></div>",
            unsafe_allow_html=True,
        )

        if st.button("Check in again →", key="restart", use_container_width=True):
            for key in ["ux_screen", "ux_pulse"]:
                st.session_state.pop(key, None)
            st.rerun()
