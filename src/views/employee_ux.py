"""
Employee-facing UX — dashboard-first flow.

After completing the check-in, the employee sees a single dashboard with four cards:
  Card 1 — How you are doing        (tier badge + description, pastel background)
  Card 2 — What is affecting this  (top 3 factors, expandable)
  Card 3 — Your trend this week    (sparkline + sentence, expandable)
  Card 4 — What might help         (2-3 resources matched to top factor)

A privacy banner sits at the very top of the dashboard, always visible.

Mobile-first. No jargon. Privacy notice visible at all times.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

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

# Pastel backgrounds per tier (soft, no harsh colours)
PASTEL_BG = {
    "low": "#dcfce7",      # soft green
    "moderate": "#fef9c3", # soft amber
    "high": "#ffedd5",     # soft orange
    "critical": "#fee2e2", # soft red
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

SIGNAL_LABELS = {
    "low": "Signs of stability",
    "moderate": "Some strain showing",
    "high": "Elevated pressure",
    "critical": "High strain — support needed",
}

# ── Privacy notice ──────────────────────────────────────────────────────────

PRIVACY_NOTICE = (
    "🔒 Only you can see this. Your manager and HR see team averages only."
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _privacy_banner():
    """Full-width banner at the top of the dashboard — always visible, not dismissible."""
    st.markdown(
        f'<div style="background:#f0fdfa;border:1px solid #99f6e4;'
        'border-radius:10px;padding:12px 20px;margin-bottom:20px;width:100%">'
        f'<p style="margin:0;color:#065f46;font-size:0.95rem;font-weight:500">'
        f"{PRIVACY_NOTICE}</p></div>",
        unsafe_allow_html=True,
    )


def _section_title(text: str):
    st.markdown(
        f'<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.08em;color:{THEME["text_secondary"]};margin:0 0 8px 0">'
        f"{text}</p>",
        unsafe_allow_html=True,
    )


def _card_wrap(label: str, contents_fn, pastel_bg: str = None):
    """Render a labelled card with optional pastel background."""
    bg = pastel_bg or THEME["card_bg"]
    text_color = "#065f46" if pastel_bg else THEME["text"]
    border_color = "#bbf7d0" if pastel_bg else THEME["border"]
    st.markdown(
        f'<div style="background:{bg};border:1px solid {border_color};'
        f'border-radius:14px;padding:20px 22px;margin-bottom:16px">',
        unsafe_allow_html=True,
    )
    if label:
        st.markdown(
            f'<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.08em;color:{THEME["text_secondary"]};margin:0 0 10px 0">'
            f"{label}</p>",
            unsafe_allow_html=True,
        )
    contents_fn()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_tier_badge(tier: str):
    """Colored badge showing tier name + plain-language signal label."""
    color = THEME.get(tier.lower(), "#888")
    signal = SIGNAL_LABELS.get(tier.lower(), "")
    st.markdown(
        f'<span style="display:inline-flex;align-items:center;gap:12px;'
        f'padding:10px 18px;border-radius:10px;background:{color}18;'
        f'border:1px solid {color}33;font-size:0.85rem;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.05em;color:{color}">'
        f"{tier.upper()}</span>"
        f'&nbsp;<span style="color:{THEME["text_secondary"]};font-size:0.9rem;font-weight:400">'
        f"{signal}</span>",
        unsafe_allow_html=True,
    )


# ── Pulse history ──────────────────────────────────────────────────────────

def _load_pulse_history(employee_id: str) -> list[dict]:
    """Load up to 5 weeks of pulse history for an employee.

    Returns list of dicts: [{week_label: str, pulse: int}, ...]
    Ordered oldest → newest.
    """
    pulse_path = Path("data/audit/pulse.jsonl")
    if not pulse_path.exists():
        return []

    history = []
    try:
        with open(pulse_path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if str(record.get("employee_id", "")) != str(employee_id):
                    continue
                history.append({
                    "week_label": record.get("week_label", "Week"),
                    "pulse": record.get("pulse"),
                    "date": record.get("date", ""),
                })
    except (IOError, OSError):
        return []

    # Sort oldest first; keep last 5
    history.sort(key=lambda r: r.get("date", ""))
    return history[-5:]


# ── Assessment questions ─────────────────────────────────────────────────────

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


# ── Screen 0: What to expect ──────────────────────────────────────────────

def screen_intro() -> None:
    """Intro screen — explains what we'll ask and why."""

    st.markdown(
        f'<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.08em;color:{THEME["text_secondary"]};margin:0 0 4px 0">'
        f"Weekly check-in</p>",
        unsafe_allow_html=True,
    )
    st.title("A quick check on how you're doing")

    _privacy_banner()

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

    _section_title("What we're checking")
    dimensions = [
        ("⚡", "Workload", "How busy you've been and whether it's sustainable"),
        ("🔋", "Energy", "Whether your energy levels have been holding up"),
        ("😴", "Recovery", "How well you've been switching off outside work"),
        ("📈", "Pressure", "Any signs you were being stretched too far"),
        ("🤝", "Support", "Whether you had the resources and backing you needed"),
    ]
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

    st.markdown("---")


# ── Screen 1: Weekly check-in ──────────────────────────────────────────────

def screen_checkin(on_submit) -> int | None:
    """Multi-question check-in. Returns pulse (1-5) or None when cancelled."""
    questions = ASSESSMENT_QUESTIONS
    total = len(questions)
    q_num = st.session_state.get("ux_q_num", 1)

    _privacy_banner()

    if q_num > total:
        # Guard: only call on_submit once per check-in cycle
        if not st.session_state.get("_ux_checkin_done"):
            st.session_state._ux_checkin_done = True
            on_submit()
            st.rerun()
        return

    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown(
            f'<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.08em;color:{THEME["text_secondary"]};margin:0">'
            f"Question {q_num} of {total}</p>",
            unsafe_allow_html=True,
        )
    with col2:
        st.progress(q_num / total, text="")

    q = questions[q_num - 1]
    st.title(q["question"])
    st.markdown(
        f'<p style="color:{THEME["text_secondary"]};font-size:0.95rem;'
        f'margin-bottom:28px;line-height:1.5">'
        f"{q['subtext']}</p>",
        unsafe_allow_html=True,
    )

    answer_key = f"q_{q['id']}"
    selected = st.session_state.get(answer_key)

    intensity_colors = [
        ("#10b981", "#059669"),
        ("#34d399", "#10b981"),
        ("#fbbf24", "#f59e0b"),
        ("#fb923c", "#f97316"),
        ("#f87171", "#ef4444"),
    ]

    for idx, (label, value) in enumerate(q["options"]):
        is_selected = selected == value
        bg_color, _ = intensity_colors[idx]

        if is_selected:
            st.markdown(
                f'<div style="background:{bg_color}18;border:2px solid {bg_color};'
                f'border-radius:12px;padding:14px 18px;margin-bottom:10px;'
                f'display:flex;align-items:center;gap:12px">'
                f'<span style="color:{bg_color};font-size:1.1rem">✓</span>'
                f'<span style="color:{THEME["text"]};font-size:0.95rem;font-weight:500">'
                f'{label}</span></div>',
                unsafe_allow_html=True,
            )
        else:
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

    if q_num > 1:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("← Back", key="checkin_back", use_container_width=True):
            st.session_state.ux_q_num = q_num - 1
            st.rerun()

    return None


# ── Dashboard ──────────────────────────────────────────────────────────────

def _build_factor_sentence(label: str, increases: bool) -> str:
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


def _compute_radar_from_features(features: dict, seniority_tier: int) -> dict:
    """Derive 0-100 risk scores for each wellbeing dimension from feature values."""

    def _scale(value: float, lo: float, hi: float, invert: bool = False) -> float:
        normalized = (value - lo) / (hi - lo) if hi != lo else 0.5
        normalized = max(0.0, min(1.0, normalized))
        return round((1 - normalized if invert else normalized) * 100, 1)

    return {
        "Workload": _scale(features.get("resource_allocation", 5.0), 0.0, 10.0, invert=False),
        "Energy levels": _scale(features.get("mental_fatigue_score", 5.0), 1.0, 10.0, invert=True),
        "How long in this role": _scale(features.get("tenure_days", 547.0), 0.0, 3650.0, invert=False),
        "Work setup": (
            100.0 if features.get("wfh_setup", 1.0) == 0.0 else 30.0
        ),
        "Role level": _scale(features.get("seniority_tier", 0.0), 0.0, 5.0, invert=False),
        "Organisation type": 50.0,
    }


def _tier_color(tier: str) -> str:
    return {"low": "#10b981", "moderate": "#f59e0b", "high": "#f97316", "critical": "#ef4444"}.get(
        tier.lower(), "#0d7377"
    )


def _render_dimensions_chart(radar_values: dict, tier: str):
    """Always renders a radar chart — uses radar_values or placeholder."""
    if not radar_values:
        radar_values = {
            "Workload": 50, "Energy levels": 50,
            "How long in this role": 50, "Work setup": 50,
            "Role level": 50, "Organisation type": 50,
        }

    dimensions = list(radar_values.keys())
    values = list(radar_values.values())
    tier_color = _tier_color(tier)

    def _rgba(hex_color: str, alpha: float = 0.18) -> str:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        return f"rgba({r},{g},{b},{alpha})"

    fig = go.Figure(
        data=[
            go.Scatterpolar(
                r=values + [values[0]],
                theta=dimensions + [dimensions[0]],
                fill="toself",
                fillcolor=_rgba(tier_color, 0.2),
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
                tickvals=[0, 50, 100],
                ticktext=["0", "50", "100"],
                tickfont=dict(color="#9ca3af", size=10),
                tickcolor="#3d3d5c",
                linecolor="#3d3d5c",
                gridcolor="#3d3d5c",
                showticklabels=True,
                side="clockwise",
            ),
            angularaxis=dict(
                tickfont=dict(color="#e5e7eb", size=10, family="Inter, sans-serif"),
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
        height=300,
        width=None,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_trend_chart(history: list[dict]):
    """Render trend sparkline from pulse history, or a placeholder if empty."""
    if not history:
        st.markdown(
            '<div style="background:#f0fdfa;border:1px dashed #99f6e4;'
            'border-radius:10px;padding:20px;text-align:center">'
            '<p style="margin:0;color:#065f46;font-size:0.9rem;line-height:1.5">'
            "Your trend will appear here after a few check-ins. Come back next week.</p></div>",
            unsafe_allow_html=True,
        )
        return

    # Word labels for y-axis
    PULSE_WORDS = {
        1: "Really rough",
        2: "Tough",
        3: "Okay",
        4: "Pretty good",
        5: "Great",
    }

    # Build chart data: week labels → word labels, no numbers
    chart_data = {}
    for i, entry in enumerate(history):
        label = entry.get("week_label", f"Week {i+1}")
        pulse = entry.get("pulse")
        if pulse is None:
            continue
        word = PULSE_WORDS.get(pulse, str(pulse))
        chart_data[label] = word

    if chart_data:
        st.line_chart(chart_data, height=140)

    # Direction sentence
    if len(history) >= 2:
        first = history[0].get("pulse", 3)
        last = history[-1].get("pulse", 3)
        delta = last - first
        if delta <= -1:
            trend_text = "You're feeling better than you were."
        elif delta >= 1:
            trend_text = "Things have been harder lately."
        else:
            trend_text = "You're holding steady."
        st.caption(trend_text)


def _render_dashboard(
    tier: str,
    probability: float | None,
    shap_decomposition: list[dict],
    radar_values: dict,
    pulse_history: list[dict],
    top_feature: str,
    ux_answers: dict,
):
    """Single dashboard with 4 cards + privacy banner at top."""
    tier_lower = tier.lower()
    pastel_bg = PASTEL_BG.get(tier_lower, THEME["card_bg"])
    tier_color = _tier_color(tier)
    label = TIER_LABELS.get(tier, "Here's your result")
    description = TIER_DESCRIPTIONS.get(tier, "")

    # ── Privacy banner — top of dashboard, always visible ─────────────────
    _privacy_banner()

    # ── Card 1 — How you are doing ─────────────────────────────────────
    def _card1():
        _render_tier_badge(tier)
        st.markdown(
            f'<p style="color:{THEME["text"]};font-size:1.05rem;'
            f'margin:8px 0 0 0;line-height:1.6">{label}</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p style="color:{THEME["text_secondary"]};font-size:0.9rem;margin:8px 0 0 0;'
            f'line-height:1.5">{description}</p>',
            unsafe_allow_html=True,
        )

    _card_wrap("How you are doing", _card1, pastel_bg=pastel_bg)

    # ── Card 2 — What is affecting this ─────────────────────────────────
    factors = [
        item for item in (shap_decomposition or [])
        if item.get("label") and item.get("feature") not in ("missing_ra", "missing_mfs")
    ][:3]

    def _card2():
        if not factors:
            st.markdown(
                f'<p style="color:{THEME["text_secondary"]};font-size:0.9rem">'
                f"Not enough data yet to show what's affecting this.</p>",
                unsafe_allow_html=True,
            )
            return

        # Always show top 3, expandable for all
        for item in factors:
            feat = item.get("feature", "")
            lbl = FEATURE_LABELS.get(feat, item.get("label", ""))
            direction = item.get("direction", "")
            color = "#ef4444" if direction == "increases" else "#10b981"
            icon = "↑" if direction == "increases" else "→"
            sentence = _build_factor_sentence(feat, direction == "increases")
            st.markdown(
                f'<div style="display:flex;align-items:flex-start;gap:10px;'
                f'padding:10px 12px;background:{THEME["bg"]};border-radius:8px;margin-bottom:8px">'
                f'<span style="color:{color};font-size:1rem;flex-shrink:0">{icon}</span>'
                f'<p style="margin:0;color:{THEME["text"]};font-size:0.88rem;line-height:1.4">'
                f"{sentence}</p></div>",
                unsafe_allow_html=True,
            )

        # Expandable section for all factors
        all_factors = [
            item for item in (shap_decomposition or [])
            if item.get("label") and item.get("feature") not in ("missing_ra", "missing_mfs")
        ]
        if len(all_factors) > 3:
            with st.expander(f"See all {len(all_factors)} factors"):
                for item in all_factors[3:]:
                    feat = item.get("feature", "")
                    lbl = FEATURE_LABELS.get(feat, item.get("label", ""))
                    direction = item.get("direction", "")
                    color = "#ef4444" if direction == "increases" else "#10b981"
                    icon = "↑" if direction == "increases" else "→"
                    sentence = _build_factor_sentence(feat, direction == "increases")
                    st.markdown(
                        f'<div style="display:flex;align-items:flex-start;gap:10px;'
                        f'padding:10px 12px;background:{THEME["bg"]};border-radius:8px;margin-bottom:8px">'
                        f'<span style="color:{color};font-size:1rem;flex-shrink:0">{icon}</span>'
                        f'<p style="margin:0;color:{THEME["text"]};font-size:0.88rem;line-height:1.4">'
                        f"{sentence}</p></div>",
                        unsafe_allow_html=True,
                    )

    _card_wrap("What is affecting this", _card2)

    # ── Card 3 — Your trend this week ───────────────────────────────────
    def _card3():
        _render_trend_chart(pulse_history)

    _card_wrap("Your trend this week", _card3)

    # ── Card 4 — What might help ────────────────────────────────────────
    # Derive recommendation feature: prefer SHAP top_feature, fall back to highest-scored survey answer
    rec_feature = top_feature
    if not RESOURCES.get(rec_feature):
        # Find the survey answer with the highest score (worst burnout signal)
        worst_score = 0
        worst_feat = None
        for feat, score in (ux_answers or {}).items():
            if score is not None and score > worst_score:
                worst_score = score
                worst_feat = feat
        if worst_feat and RESOURCES.get(worst_feat):
            rec_feature = worst_feat

    resources = RESOURCES.get(rec_feature, [])
    rec_label = FEATURE_LABELS.get(rec_feature, rec_feature or "your responses")

    def _card4():
        if not resources:
            st.markdown(
                f'<p style="color:{THEME["text_secondary"]};font-size:0.9rem">'
                f"No specific suggestions yet. Speaking with your manager or HR is always a good step.</p>",
                unsafe_allow_html=True,
            )
            return

        st.caption(f"Based on: {rec_label}")

        for resource in resources[:3]:
            st.markdown(
                f'<div style="padding:14px 16px;background:{THEME["bg"]};'
                f'border:1px solid {THEME["border"]};border-left:3px solid #0d7377;'
                f'border-radius:10px;margin-bottom:10px">'
                f'<p style="margin:0 0 6px 0;color:{THEME["text"]};'
                f'font-weight:600;font-size:0.92rem">{resource}</p>'
                f'<button style="background:#0d7377;color:#fff;border:none;'
                f'border-radius:6px;padding:6px 14px;font-size:0.8rem;cursor:pointer">'
                f"Read this</button>",
                unsafe_allow_html=True,
            )

    _card_wrap("What might help", _card4)

    # ── Dimensions chart (collapsible) ───────────────────────────────────
    with st.expander("See your wellbeing dimensions"):
        _render_dimensions_chart(radar_values, tier)


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
    Two modes:
    - Demo / local: pass features + seniority_tier
    - API-backed:   pass risk_tier + burnout_probability + shap + resources

    Flow: intro → check-in → dashboard (4 cards, always visible).
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
        shap_decomposition = [
            item for item in shap_decomposition
            if item.get("feature") not in ("missing_ra", "missing_mfs") and item.get("label")
        ]
        shap_decomposition.sort(key=lambda x: abs(x.get("impact_value", 0)), reverse=True)
        top_feature = shap_decomposition[0].get("feature", "") if shap_decomposition else ""
        radar_values = _compute_radar_from_features(features, seniority_tier)
        pulse_history = _load_pulse_history(employee_id)

    else:
        if risk_tier is None:
            st.error("Provide features+seniority_tier or risk_tier.")
            return
        tier = risk_tier
        probability = burnout_probability
        shap_decomposition = shap or []
        top_feature = shap_decomposition[0].get("feature", "") if shap_decomposition else ""

        # Compute radar from SHAP if available, else placeholder
        if shap_decomposition:
            feat_map = {item["feature"]: item["impact_value"] for item in shap_decomposition}
            max_impact = max(abs(v) for v in feat_map.values()) or 1.0
            radar_values = {
                "Workload": round(abs(feat_map.get("resource_allocation", 0)) / max_impact * 100, 1),
                "Energy levels": round(abs(feat_map.get("mental_fatigue_score", 0)) / max_impact * 100, 1),
                "How long in this role": round(abs(feat_map.get("tenure_days", 0)) / max_impact * 100, 1),
                "Work setup": round(abs(feat_map.get("wfh_setup", 0)) / max_impact * 100, 1),
                "Role level": round(abs(feat_map.get("seniority_tier", 0)) / max_impact * 100, 1),
                "Organisation type": round(abs(feat_map.get("company_type", 0)) / max_impact * 100, 1),
            }
        else:
            radar_values = {
                "Workload": 50, "Energy levels": 50,
                "How long in this role": 50, "Work setup": 50,
                "Role level": 50, "Organisation type": 50,
            }
        pulse_history = _load_pulse_history(employee_id)

    # ── Store for screens ────────────────────────────────────────────────
    st.session_state.radar_values = radar_values
    st.session_state.shap_decomposition = shap_decomposition
    st.session_state.top_feature = top_feature

    # ── State machine ────────────────────────────────────────────────────
    # States: intro → checkin → dashboard
    if "ux_screen" not in st.session_state:
        st.session_state.ux_screen = "intro"

    if st.session_state.ux_screen in ("intro", "done"):
        st.session_state.ux_q_num = 1
        st.session_state.ux_answers = {}
        st.session_state._ux_checkin_done = False

    screen = st.session_state.ux_screen

    # ── Screen 0: What to expect ────────────────────────────────────────
    if screen == "intro":
        screen_intro()
        col_spacer, col_btn = st.columns([3, 1])
        with col_btn:
            if st.button("Start check-in →", key="start_checkin", use_container_width=True):
                st.session_state.ux_screen = "checkin"
                st.rerun()
        return

    # ── Screen 1: Weekly check-in ────────────────────────────────────────
    if screen == "checkin":
        def handle_pulse():
            st.session_state.ux_screen = "dashboard"

        screen_checkin(handle_pulse)
        return

    # ── Dashboard ────────────────────────────────────────────────────────
    if screen == "dashboard":
        _render_dashboard(
            tier=tier,
            probability=probability,
            shap_decomposition=shap_decomposition,
            radar_values=radar_values,
            pulse_history=pulse_history,
            top_feature=top_feature,
            ux_answers=st.session_state.get("ux_answers", {}),
        )
        st.markdown("---")
        if st.button("Check in again →", key="restart", use_container_width=True):
            for key in ["ux_screen", "ux_pulse", "ux_q_num", "ux_answers", "_ux_checkin_done"]:
                st.session_state.pop(key, None)
            st.rerun()
        st.markdown(
            '<p style="text-align:center;margin-top:8px">'
            '<a href="/?signout=1" style="color:#9ca3af;font-size:0.8rem;text-decoration:none">'
            '🚪 Sign out</a></p>',
            unsafe_allow_html=True,
        )
        return
