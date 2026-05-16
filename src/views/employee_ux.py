"""
Employee-facing UX — 5-screen flow.

Screen 1: Weekly check-in (one question, five options)
Screen 2: Your result (privacy notice, plain label, one action)
Screen 3: What is affecting this (three plain sentences)
Screen 4: What might help (matched resources, max 3)
Screen 5: Your trend (simple line, no numbers)

Mobile-first. No jargon. Privacy notice visible on every result screen.
"""

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


def _big_button(label: str, key: str, primary: bool = True):
    bg = "#0d7377" if primary else THEME["card_bg"]
    color = "#ffffff" if primary else THEME["text"]
    border = "none" if primary else f"1px solid {THEME['border']}"
    st.markdown(
        f'<style>'
        f'a[data-testid="stMainBlockContainer"] button[data-testid="stMainBlockContainer"] '
        f'#{key} {{display:none}} '
        f'</style>',
        unsafe_allow_html=True,
    )
    clicked = st.button(
        label,
        key=key,
        use_container_width=True,
    )
    return clicked


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


# ── Screen 1: Weekly check-in ──────────────────────────────────────────────

def screen_checkin(on_submit) -> int | None:
    """One question. Five large tap targets. Returns pulse (1-5) or None."""
    st.markdown(
        f'<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.08em;color:{THEME["text_secondary"]};margin:0 0 4px 0">'
        f"Weekly check-in</p>",
        unsafe_allow_html=True,
    )
    st.title("How was your week?")

    # Big tap targets — one per option
    pulse_labels = [
        ("Really rough",  1, "😔"),
        ("Tough",         2, "😟"),
        ("Okay",          3, "😐"),
        ("Pretty good",   4, "🙂"),
        ("Great",         5, "😊"),
    ]

    # Stack vertically for easy mobile tapping
    for label, value, emoji in pulse_labels:
        col1, col2 = st.columns([1, 5])
        with col2:
            if st.button(
                f"{emoji}  {label}",
                key=f"pulse_{value}",
                use_container_width=True,
            ):
                on_submit(value)
                return value
        with col1:
            pass  # emoji spacer handled by column width

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


# ── Screen 5: Your trend ──────────────────────────────────────────────────

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

    else:
        if risk_tier is None:
            st.error("Provide features+seniority_tier or risk_tier.")
            return
        tier = risk_tier
        probability = burnout_probability
        shap_decomposition = shap or []
        top_feature = shap_decomposition[0].get("feature", "") if shap_decomposition else ""

    # ── State machine: which screen are we on? ─────────────────────────────
    # States: checkin → result → factors → resources → done
    if "ux_screen" not in st.session_state:
        st.session_state.ux_screen = "checkin"

    screen = st.session_state.ux_screen

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

        if screen_result(tier, probability, on_see_factors):
            return  # state updated, rerun will show next screen

        # Trend link
        if st.button("See your trend →", key="see_trend", use_container_width=True):
            st.session_state.ux_screen = "trend"
            st.rerun()

    # ── Screen 3: What is affecting this ───────────────────────────────
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
