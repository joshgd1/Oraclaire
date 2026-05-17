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
from src.model.services.peer_benchmark import get_peer_benchmark

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
    st.html(
        f"""
        <div style="background:linear-gradient(135deg,#f0fdfa 0%,#ecfdf5 100%);"
        f"border:1px solid #6ee7b7;border-radius:12px;padding:14px 20px;margin-bottom:20px;">
        f"<div style="display:flex;align-items:center;gap:10px;">
        f"<span style="font-size:1.1rem">🔒</span>"
        f"<p style="margin:0;color:#065f46;font-size:0.95rem;font-weight:500;line-height:1.4;">"
        f"{PRIVACY_NOTICE}</p></div></div>
        """
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
    # Pastel backgrounds are light → use dark text; dark backgrounds → use light text
    text_color = "#065f46" if pastel_bg else THEME["text"]
    text_secondary = "#047857" if pastel_bg else THEME["text_secondary"]
    border_color = "#bbf7d0" if pastel_bg else THEME["border"]
    st.markdown(
        f'<div style="background:{bg};border:1px solid {border_color};'
        f'border-radius:14px;padding:20px 22px;margin-bottom:16px">',
        unsafe_allow_html=True,
    )
    if label:
        st.markdown(
            f'<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.08em;color:{text_secondary};margin:0 0 10px 0">'
            f"{label}</p>",
            unsafe_allow_html=True,
        )
    # Pass text colors to content fn via session state so card content is readable
    st.session_state._card_text_color = text_color
    st.session_state._card_text_secondary = text_secondary
    contents_fn()
    st.markdown("</div>", unsafe_allow_html=True)


# ── Collapsible card helpers (CSS defined once, shared across all cards) ──────

def _inject_collapsible_css(pastel_bg: str | None, text_color: str):
    """Inject the oraclaire-card CSS exactly once, styled for the current card background."""
    border = "#bbf7d0" if pastel_bg else THEME["border"]
    card_bg = pastel_bg or THEME["card_bg"]
    st.markdown(f"""
    <style>
    details.oraclaire-card {{
        background: {card_bg};
        border: 1px solid {border};
        border-radius: 12px;
        margin-bottom: 16px;
        overflow: hidden;
    }}
    details.oraclaire-card summary {{
        padding: 14px 18px;
        cursor: pointer;
        list-style: none;
        display: flex;
        align-items: center;
        justify-content: space-between;
        color: {text_color};
        font-size: 0.95rem;
        font-weight: 600;
        font-family: inherit;
    }}
    details.oraclaire-card summary::-webkit-details-marker {{ display: none; }}
    details.oraclaire-card summary::after {{
        content: '▼';
        color: {text_color};
        font-size: 0.8rem;
    }}
    details.oraclaire-card[open] summary::after {{ content: '▲'; }}
    details.oraclaire-card .card-body {{
        padding: 0 18px 16px;
        border-top: 1px solid {border};
    }}
    </style>
    """, unsafe_allow_html=True)


def _collapsible_card(label: str, card_id: str, default_open: bool = False):
    """Render an HTML details/summary card (CSS injected once by _inject_collapsible_css)."""
    open_attr = " open" if default_open else ""
    st.markdown(
        f'<details class="oraclaire-card"{open_attr} id="d_{card_id}">'
        f'<summary>{label}</summary>'
        f'<div class="card-body">',
        unsafe_allow_html=True,
    )


def _collapsible_end():
    st.markdown("</div></details>", unsafe_allow_html=True)


def _render_tier_badge(tier: str):
    """Colored badge showing tier name + plain-language signal label."""
    color = THEME.get(tier.lower(), "#888")
    signal = SIGNAL_LABELS.get(tier.lower(), "")
    # Use stored card text color for the badge text — ensures visibility on pastel backgrounds
    tc = st.session_state.get("_card_text_color", THEME["text"])
    tcs = st.session_state.get("_card_text_secondary", THEME["text_secondary"])
    st.markdown(
        f'<span style="display:inline-flex;align-items:center;gap:12px;'
        f'padding:10px 18px;border-radius:10px;background:{color}18;'
        f'border:1px solid {color}33;font-size:0.85rem;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.05em;color:{tc}">'
        f"{tier.upper()}</span>"
        f'&nbsp;<span style="color:{tcs};font-size:0.9rem;font-weight:400">'
        f"{signal}</span>",
        unsafe_allow_html=True,
    )


# ── Pulse history ──────────────────────────────────────────────────────────

def _save_pulse(
    employee_id: str,
    pulse: int,
    tier: str,
    probability: float | None = None,
) -> None:
    """Append a completed pulse/check-in to the audit log for longitudinal tracking."""
    from datetime import date
    pulse_path = Path("data/audit/pulse.jsonl")
    pulse_path.parent.mkdir(parents=True, exist_ok=True)

    today = date.today()
    week_label = f"Week {today.isocalendar()[1]}, {today.year}"

    record = {
        "employee_id": str(employee_id),
        "date": str(today),
        "week_label": week_label,
        "pulse": pulse,
        "tier": tier,
        "probability": probability,
    }
    try:
        with open(pulse_path, "a") as fh:
            fh.write(json.dumps(record) + "\n")
    except (IOError, OSError):
        pass  # Non-fatal in demo mode


def _load_pulse_history(employee_id: str) -> list[dict]:
    """Load up to 12 weeks of pulse history for an employee.

    Returns list of dicts: [{week_label, pulse, tier, date, probability}, ...]
    Ordered oldest → newest.
    """
    pulse_path = Path("data/audit/pulse.jsonl")
    if not pulse_path.exists():
        return []

    history = []
    seen_dates = set()
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
                date_str = record.get("date", "")
                # Deduplicate by date — keep the most recent entry per day
                if date_str in seen_dates:
                    continue
                seen_dates.add(date_str)
                history.append({
                    "week_label": record.get("week_label", "Week"),
                    "pulse": record.get("pulse"),
                    "tier": record.get("tier"),
                    "date": date_str,
                    "probability": record.get("probability"),
                })
    except (IOError, OSError):
        return []

    history.sort(key=lambda r: r.get("date", ""))
    return history[-12:]  # last 12 weeks


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
            bgcolor="#2a2a3e",
            radialaxis=dict(
                range=[0, 100],
                tickvals=[0, 50, 100],
                ticktext=["0", "50", "100"],
                tickfont=dict(color="#d1d5db", size=10),
                tickcolor="#4b5563",
                linecolor="#4b5563",
                gridcolor="#374151",
                showticklabels=True,
                side="clockwise",
            ),
            angularaxis=dict(
                tickfont=dict(color="#f3f4f6", size=11, family="Inter, sans-serif"),
                tickcolor="#374151",
                linecolor="#374151",
                gridcolor="#374151",
                rotation=90,
                direction="clockwise",
            ),
        ),
        paper_bgcolor="#2a2a3e",
        plot_bgcolor="#2a2a3e",
        showlegend=False,
        margin=dict(l=20, r=20, t=20, b=20),
        height=300,
        width=None,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_trend_chart(history: list[dict]):
    """Render trend chart from pulse history using Plotly, or a placeholder if empty."""
    if not history:
        st.markdown(
            '<div style="background:#f0fdfa;border:1px dashed #99f6e4;'
            'border-radius:12px;padding:28px 24px;text-align:center;margin-bottom:8px">'
            '<p style="font-size:2.2rem;margin:0 0 12px 0">📊</p>'
            '<p style="margin:0 0 6px 0;color:#065f46;font-size:0.95rem;font-weight:600;line-height:1.4">'
            "Your weekly trend will appear here</p>"
            '<p style="margin:0;color:#065f46;font-size:0.85rem;line-height:1.5;opacity:0.75">'
            "Complete a weekly check-in to start tracking your wellbeing over time.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    PULSE_WORDS = {
        1: "Really rough",
        2: "Tough",
        3: "Okay",
        4: "Pretty good",
        5: "Great",
    }

    TIER_CHART_COLORS = {
        "low": "#10b981",
        "moderate": "#f59e0b",
        "high": "#f97316",
        "critical": "#ef4444",
    }

    # Build chart data — each point colored by its tier
    labels = []
    pulses = []
    tier_colors = []
    tiers = []
    for i, entry in enumerate(history):
        label = entry.get("week_label", f"Week {i+1}")
        pulse = entry.get("pulse")
        if pulse is None:
            continue
        tier = entry.get("tier", "moderate")
        labels.append(label)
        pulses.append(pulse)
        tiers.append(tier)
        tier_colors.append(TIER_CHART_COLORS.get(tier.lower(), "#0d7377"))

    if not pulses:
        return

    # Richer trajectory analysis
    if len(history) >= 2:
        first_pulse = history[0].get("pulse", 3)
        last_pulse = history[-1].get("pulse", 3)
        delta = last_pulse - first_pulse
        first_tier = history[0].get("tier", "moderate")
        last_tier = history[-1].get("tier", "moderate")

        if delta <= -1:
            trend_text = "You're feeling better than you were."
            trend_color = "#10b981"
            trend_icon = "↓"
        elif delta >= 1:
            trend_text = "Things have been harder lately."
            trend_color = "#ef4444"
            trend_icon = "↑"
        else:
            trend_text = "You're holding steady."
            trend_color = "#f59e0b"
            trend_icon = "→"

        # Compare first vs last tier
        tier_change = ""
        if first_tier != last_tier:
            tier_change = f" · Tier shifted {first_tier} → {last_tier}"

        trend_sub = f"{abs(delta):.1f} points this period{tier_change}"
    else:
        trend_text = ""
        trend_color = "#9ca3af"
        trend_icon = ""
        trend_sub = ""

    # Create Plotly chart with tier-colored markers and connecting line
    fig = go.Figure()

    # Add a subtle connecting line
    fig.add_trace(go.Scatter(
        x=list(range(len(pulses))),
        y=pulses,
        mode="lines",
        line=dict(color="rgba(13,115,119,0.3)", width=2, dash="solid"),
        hoverinfo="skip",
        showlegend=False,
    ))

    # Add colored markers — one trace per tier group for legend
    tier_trace_data = {}
    for i, (pulse, tier, color) in enumerate(zip(pulses, tiers, tier_colors)):
        if tier not in tier_trace_data:
            tier_trace_data[tier] = {"x": [], "y": [], "c": [], "t": []}
        tier_trace_data[tier]["x"].append(i)
        tier_trace_data[tier]["y"].append(pulse)
        tier_trace_data[tier]["c"].append(color)
        tier_trace_data[tier]["t"].append(PULSE_WORDS.get(pulse, str(pulse)))

    for tier, data in tier_trace_data.items():
        tier_label = tier.title()
        fig.add_trace(go.Scatter(
            x=data["x"],
            y=data["y"],
            mode="markers",
            marker=dict(
                size=12,
                color=data["c"],
                symbol="circle",
                line=dict(width=2, color="rgba(255,255,255,0.5)"),
            ),
            text=[f"{t} — {tier_label}" for t in data["t"]],
            hovertemplate="<b>%{text}</b><br>Week %{x+1}<extra></extra>",
            name=tier_label,
            showlegend=True,
        ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(color="#9ca3af", size=10),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
        ),
        margin=dict(l=10, r=10, t=10, b=10),
        height=200,
        xaxis=dict(
            showticklabels=True,
            ticktext=labels,
            tickvals=list(range(len(labels))),
            showgrid=False,
            zeroline=False,
            color="#9ca3af",
            tickangle=-30,
            tickfont=dict(size=9),
        ),
        yaxis=dict(
            range=[0.5, 5.5],
            showgrid=True,
            gridcolor="rgba(156,163,175,0.15)",
            gridwidth=1,
            zeroline=False,
            showticklabels=False,
            color="#9ca3af",
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Trajectory summary bar
    if trend_text:
        delta_str = f"+{delta:.1f}" if delta > 0 else f"{delta:.1f}"
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;padding:10px 14px;'
            f'background:{trend_color}18;border:1px solid {trend_color}44;'
            f'border-radius:10px;margin-bottom:8px">'
            f'<span style="font-size:1.1rem;font-weight:800;color:{trend_color}">{trend_icon}</span>'
            f'<div>'
            f'<p style="margin:0;color:{trend_color};font-size:0.88rem;font-weight:700;'
            f'line-height:1.3">{trend_text}</p>'
            f'<p style="margin:2px 0 0 0;color:#9ca3af;font-size:0.78rem;line-height:1.3">'
            f'{trend_sub} · Δ{delta_str} points</p>'
            f'</div></div>',
            unsafe_allow_html=True,
        )


def _render_dashboard(
    tier: str,
    probability: float | None,
    shap_decomposition: list[dict],
    radar_values: dict,
    pulse_history: list[dict],
    top_feature: str,
    ux_answers: dict,
    features: dict | None = None,
    seniority_tier: int | None = None,
):
    """Single dashboard with 4 cards + privacy banner at top."""
    tier_lower = tier.lower()
    pastel_bg = PASTEL_BG.get(tier_lower, THEME["card_bg"])
    tier_color = _tier_color(tier)
    label = TIER_LABELS.get(tier, "Here's your result")
    description = TIER_DESCRIPTIONS.get(tier, "")

    # Text colors — dark on pastel backgrounds (WCAG 4.5:1 compliant)
    tc = "#065f46" if pastel_bg else THEME["text"]
    tcs = "#047857" if pastel_bg else THEME["text_secondary"]
    st.session_state["_card_text_color"] = tc
    st.session_state["_card_text_secondary"] = tcs

    # ── Page-level H1 ──────────────────────────────────────────────────────
    st.markdown(
        f'<h1 style="font-size:1.5rem;font-weight:700;color:{tc};margin:0 0 4px 0;'
        f'line-height:1.3">Your wellbeing check-in</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="color:{tcs};font-size:0.875rem;margin:0 0 20px 0">'
        f"Here's what we found from your responses</p>",
        unsafe_allow_html=True,
    )

    # ── Privacy banner — top of dashboard, always visible ─────────────────
    _privacy_banner()

    # ── Card 1 — How you are doing ─────────────────────────────────────
    def _card1():
        _render_tier_badge(tier)
        st.markdown(
            f'<p style="color:{tc};font-size:1.05rem;'
            f'margin:8px 0 0 0;line-height:1.6">{label}</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p style="color:{tcs};font-size:0.9rem;margin:8px 0 0 0;'
            f'line-height:1.5">{description}</p>',
            unsafe_allow_html=True,
        )

    _card_wrap("How you are doing", _card1, pastel_bg=pastel_bg)

    # ── CSS for collapsible cards — defined once at module level ───────────
    # Forces readable text on all background colours (WCAG compliance).
    # Injected once; shared by all four collapsible cards below.
    _inject_collapsible_css(pastel_bg, tc)

    # ── Card 2 — What is affecting this ─────────────────────────────────
    factors = [
        item for item in (shap_decomposition or [])
        if item.get("label") and item.get("feature") not in ("missing_ra", "missing_mfs")
    ][:3]
    all_factors = [
        item for item in (shap_decomposition or [])
        if item.get("label") and item.get("feature") not in ("missing_ra", "missing_mfs")
    ]

    _collapsible_card("💡 What is affecting this", "factors")
    if not factors:
        # Show general factors when no SHAP data available
        typical_factors = [
            ("Your recent energy levels", "↑", "#ef4444", "Energy levels are a key driver of how you're feeling day to day."),
            ("Your current workload demands", "↑", "#f97316", "High workload over sustained periods is a common source of strain."),
            ("Your time in this role", "→", "#f59e0b", "How long you've been in the role can affect your sense of pace and renewal."),
        ]
        for feat, arrow, color, sentence in typical_factors:
            st.markdown(
                f'<div style="display:flex;align-items:flex-start;gap:12px;'
                f'padding:12px 14px;background:rgba(0,0,0,0.04);border-radius:10px;margin-bottom:8px">'
                f'<div style="width:32px;height:32px;border-radius:8px;background:{color}18;'
                f'display:flex;align-items:center;justify-content:center;flex-shrink:0">'
                f'<span style="color:{color};font-size:0.9rem">{arrow}</span></div>'
                f'<div><p style="margin:0 0 2px 0;color:{tc};font-size:0.9rem;font-weight:600;line-height:1.3">{feat}</p>'
                f'<p style="margin:0;color:{tcs};font-size:0.82rem;line-height:1.4">{sentence}</p></div></div>',
                unsafe_allow_html=True,
            )
        st.markdown(f'<p style="color:{tcs};font-size:0.78rem;margin:4px 0 0 0">Complete a full assessment to see your personalised factors.</p>', unsafe_allow_html=True)
    else:
        for item in factors:
            feat = item.get("feature", "")
            direction = item.get("direction", "")
            color = "#ef4444" if direction == "increases" else "#10b981"
            arrow = "↑" if direction == "increases" else "→"
            sentence = _build_factor_sentence(feat, direction == "increases")
            st.markdown(
                f'<div style="display:flex;align-items:flex-start;gap:12px;'
                f'padding:12px 14px;background:rgba(0,0,0,0.04);border-radius:10px;margin-bottom:8px">'
                f'<div style="width:32px;height:32px;border-radius:8px;background:{color}18;'
                f'display:flex;align-items:center;justify-content:center;flex-shrink:0">'
                f'<span style="color:{color};font-size:0.9rem">{arrow}</span></div>'
                f'<p style="margin:0;color:{tc};font-size:0.88rem;line-height:1.4">'
                f"{sentence}</p></div>",
                unsafe_allow_html=True,
            )
        if len(all_factors) > 3:
            st.markdown(f'<p style="color:{tcs};font-size:0.8rem;margin:4px 0 0 0">+ {len(all_factors) - 3} more factors</p>', unsafe_allow_html=True)
            for item in all_factors[3:]:
                feat = item.get("feature", "")
                direction = item.get("direction", "")
                color = "#ef4444" if direction == "increases" else "#10b981"
                arrow = "↑" if direction == "increases" else "→"
                sentence = _build_factor_sentence(feat, direction == "increases")
                st.markdown(
                    f'<div style="display:flex;align-items:flex-start;gap:12px;'
                    f'padding:12px 14px;background:rgba(0,0,0,0.04);border-radius:10px;margin-bottom:8px">'
                    f'<div style="width:32px;height:32px;border-radius:8px;background:{color}18;'
                    f'display:flex;align-items:center;justify-content:center;flex-shrink:0">'
                    f'<span style="color:{color};font-size:0.9rem">{arrow}</span></div>'
                    f'<p style="margin:0;color:{tc};font-size:0.88rem;line-height:1.4">'
                    f"{sentence}</p></div>",
                    unsafe_allow_html=True,
                )
    _collapsible_end()

    # ── Card 3 — Your trend this week ────────────────────────────────────
    _collapsible_card("📈 Your trend this week", "trend")
    _render_trend_chart(pulse_history)
    _collapsible_end()

    # ── Card 4 — What might help ─────────────────────────────────────────
    rec_feature = top_feature
    if not RESOURCES.get(rec_feature):
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

    _collapsible_card("🌱 What might help", "resources")
    if not resources:
        # Show general wellbeing steps when no SHAP-matched resources available
        general_steps = [
            ("💬 Talk to your manager", "Share how you're feeling — they can help adjust workload or priorities."),
            ("👥 Connect with your team", "Social support is one of the strongest buffers against burnout."),
            ("☕ Take regular breaks", "Short breaks throughout the day help sustain energy and focus."),
        ]
        for icon_title, desc in general_steps:
            st.markdown(
                f'<div style="display:flex;align-items:flex-start;gap:12px;'
                f'padding:14px 16px;background:rgba(0,0,0,0.04);border-radius:10px;margin-bottom:10px">'
                f'<div style="flex:1">'
                f'<p style="margin:0 0 4px 0;color:{tc};font-size:0.92rem;font-weight:600;line-height:1.3">{icon_title}</p>'
                f'<p style="margin:0;color:{tcs};font-size:0.82rem;line-height:1.4">{desc}</p></div></div>',
                unsafe_allow_html=True,
            )
        st.markdown(f'<p style="color:{tcs};font-size:0.78rem;margin:4px 0 0 0">These steps are generally helpful for everyone.</p>', unsafe_allow_html=True)
    else:
        st.markdown(
            f'<p style="color:{tcs};font-size:0.8rem;margin:0 0 12px 0">'
            f"Based on: <strong>{rec_label}</strong></p>",
            unsafe_allow_html=True,
        )
        cols = st.columns(min(len(resources[:3]), 3)) if resources else st.columns(1)
        for idx, resource in enumerate(resources[:3]):
            with (cols[idx] if len(resources) > 1 else cols[0]):
                st.markdown(
                    f'<div style="padding:14px 16px;background:rgba(0,0,0,0.04);'
                    f'border-radius:10px;margin-bottom:10px">'
                    f'<p style="margin:0 0 12px 0;color:{tc};'
                    f'font-weight:600;font-size:0.9rem;line-height:1.4">{resource}</p></div>',
                    unsafe_allow_html=True,
                )
                search_url = f"https://www.google.com/search?q={resource.replace(' ', '+')}"
                st.link_button("Read more →", search_url, use_container_width=True)
    _collapsible_end()

    # ── Peer benchmark card ──────────────────────────────────────────────
    if features and seniority_tier is not None:
        # Derive check-in dimensions from ux_answers (1-5 scale → 0-100)
        ra_response = ux_answers.get("resource_allocation")  # 1-5
        mfs_response = ux_answers.get("mental_fatigue_score")  # 1-5

        emp_workload = round((ra_response / 5.0) * 100.0, 1) if ra_response else None
        # Energy: response 1 (fully recharged) → 100, response 5 (exhausted) → 0
        emp_energy = round(((5 - mfs_response) / 4.0) * 100.0, 1) if mfs_response else None

        peer_data = get_peer_benchmark(
            seniority_tier=float(seniority_tier),
            tenure_days=features.get("tenure_days", 547.0),
            wfh_setup=features.get("wfh_setup", 1.0),
            company_type=features.get("company_type", 0.0),
            employee_workload=emp_workload,
            employee_energy=emp_energy,
        )

        _collapsible_card("🆚 How you compare to peers like you", "peer")
        bucket = peer_data.get("bucket")
        n_peers = peer_data.get("n_peers", 0)
        dims = peer_data.get("dimensions", {})

        # Build peer group label
        if bucket:
            bucket_label = f"{bucket.seniority_bucket.title()} · {bucket.tenure_bucket} tenure · {bucket.wfh_bucket.upper()}"
        else:
            bucket_label = "All employees"

        peer_n_label = f"Based on {n_peers:,} similar employees" if n_peers >= 5 else "Not enough peer data yet"
        st.markdown(
            f'<p style="color:{tcs};font-size:0.75rem;margin:0 0 14px 0">'
            f"{peer_n_label} · {bucket_label}</p>",
            unsafe_allow_html=True,
        )

        dim_configs = [
            ("Workload", "workload"),
            ("Energy", "energy"),
        ]

        for dim_label, dim_key in dim_configs:
            d = dims.get(dim_key, {})
            score = d.get("score")
            peer_avg = d.get("peer_avg", 50.0)
            delta = d.get("delta", 0)

            if score is None:
                continue

            # Bar width = score (0-100)
            bar_width = int(score)
            # Color: green if better than peer (lower workload is better; higher energy is better)
            is_better = (delta < 0) if dim_key == "workload" else (delta > 0)
            bar_color = "#10b981" if is_better else ("#f59e0b" if abs(delta) > 10 else "#0d7377")
            delta_str = f"{'+' if delta > 0 else ''}{delta:.1f}"
            delta_color = "#10b981" if is_better else ("#ef4444" if abs(delta) > 10 else "#9ca3af")

            # Peer avg marker position (0-100 scale)
            peer_marker = int(peer_avg)

            st.markdown(
                f'<div style="margin-bottom:14px">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px">'
                f'<span style="color:{tc};font-size:0.88rem;font-weight:600">{dim_label}</span>'
                f'<span style="color:{tc};font-size:0.88rem;font-weight:700">{score:.0f}'
                f'<span style="color:{tcs};font-size:0.78rem;font-weight:400"> / {peer_avg:.0f} avg  '
                f'<span style="color:{delta_color};font-size:0.78rem">({delta_str})</span></span>'
                f'</div>'
                f'<div style="position:relative;height:10px;background:rgba(0,0,0,0.06);'
                f'border-radius:5px;overflow:hidden">'
                f'<div style="position:absolute;left:0;top:0;height:100%;width:{bar_width}%;'
                f'background:{bar_color};border-radius:5px"></div>'
                f'<div style="position:absolute;left:{peer_marker}%;top:-2px;'
                f'width:2px;height:14px;background:#374151;border-radius:1px"></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

        _collapsible_end()

    # ── Card 5 — Wellbeing dimensions ───────────────────────────────────
    _collapsible_card("🧠 Your wellbeing dimensions", "dimensions")
    st.markdown(
        f'<p style="color:{tcs};font-size:0.8rem;margin:0 0 12px 0">'
        f"Your score across five key areas of wellbeing</p>",
        unsafe_allow_html=True,
    )
    _render_dimensions_chart(radar_values, tier)
    _collapsible_end()


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
        # Inject check-in answers into features before scoring
        # ux_answers: resource_allocation (1-5) and mental_fatigue_score (1-5) from check-in
        # Model expects: resource_allocation (0-10) and mental_fatigue_score (1-10)
        ux = st.session_state.get("ux_answers", {})
        scoring_features = dict(features)
        if "resource_allocation" in ux:
            ra = float(ux["resource_allocation"])
            # Map 1-5 → 2-10 (keep well above 0 to avoid "missing" flag)
            scoring_features["resource_allocation"] = round((ra - 1) / 4 * 8 + 2, 1)
        if "mental_fatigue_score" in ux:
            mfs = float(ux["mental_fatigue_score"])
            # Map 1-5 → 2-10 (1 = fully recharged, 5 = exhausted)
            scoring_features["mental_fatigue_score"] = round((mfs - 1) / 4 * 8 + 2, 1)
            # Keep tenure interaction features consistent
            scoring_features["tenure_fatigue"] = scoring_features["mental_fatigue_score"]
            scoring_features["tenure_workload"] = scoring_features.get("resource_allocation", scoring_features["tenure_workload"])

        try:
            result = score_employee(
                employee_id=employee_id,
                features=scoring_features,
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
        # Save completed pulse to history for longitudinal tracking
        _save_pulse(
            employee_id=employee_id,
            pulse=st.session_state.get("ux_answers", {}).get("resource_allocation", 3),
            tier=tier,
            probability=probability,
        )
        # Reload so the new entry appears in the chart
        pulse_history = _load_pulse_history(employee_id)

        _render_dashboard(
            tier=tier,
            probability=probability,
            shap_decomposition=shap_decomposition,
            radar_values=radar_values,
            pulse_history=pulse_history,
            top_feature=top_feature,
            ux_answers=st.session_state.get("ux_answers", {}),
            features=features,
            seniority_tier=seniority_tier,
        )
        st.markdown("---")
        if st.button("Check in again →", key="restart", use_container_width=True):
            for key in ["ux_screen", "ux_pulse", "ux_q_num", "ux_answers", "_ux_checkin_done"]:
                st.session_state.pop(key, None)
            st.rerun()
        return
