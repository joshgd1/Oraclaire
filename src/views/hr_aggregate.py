"""
HR aggregate burnout risk dashboard.

Shows: org-wide tier distribution, participation tracking,
Organisational Risk Threshold alerts, exclusion summary.
Access: HR admin only. No individual employee data.
"""

from collections import Counter

import streamlit as st

from src.config import (
    MIN_TEAM_SIZE,
    ORT_CEILING,
    ORT_PULSE_CONSECUTIVE_WEEKS,
    ORT_TRIGGER_QUARTERLY,
    TIER_COLORS,
    TIER_ORDER,
)


TIER_THEME = {
    "low": "#10b981",
    "moderate": "#f59e0b",
    "high": "#f97316",
    "critical": "#ef4444",
}

THEME_HR = {
    "card_bg": "#2a2a3e",
    "border": "#3d3d5c",
    "text": "#e5e7eb",
    "text_secondary": "#9ca3af",
    "bg": "#1e1e2e",
}


def _wrap_card():
    return st.container()


def render_header():
    st.markdown(
        f'<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.08em;color:{THEME_HR["text_secondary"]};margin:0">HR Admin</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<h1 style="font-size:1.5rem;font-weight:700;color:{THEME_HR["text"]};margin:0 0 4px 0;'
        f'line-height:1.3">Organisational Burnout Overview</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="color:{THEME_HR["text_secondary"]};font-size:0.875rem;margin:0 0 20px 0">'
        f"Aggregate risk across the organisation &mdash; no individual scores are shown.</p>",
        unsafe_allow_html=True,
    )


def render_tier_distribution(scores: list[dict]):
    """Render tier distribution bar chart from list of scored results."""
    if not scores:
        st.warning("No assessment data available yet.")
        return

    tiers = Counter(s.get("risk_tier", "unknown") for s in scores)
    total = len(scores)

    st.markdown("#### Risk tier distribution")
    st.caption(f"Based on {total} employees who completed an assessment.")

    cols = st.columns(4)
    tier_icons = {
        "low": "✓",
        "moderate": "∼",
        "high": "⚠",
        "critical": "✕",
    }
    for idx, tier in enumerate(TIER_ORDER):
        count = tiers.get(tier, 0)
        pct = count / total if total > 0 else 0
        color = TIER_THEME.get(tier, "#888")
        icon = tier_icons.get(tier, "")
        with cols[idx]:
            st.markdown(
                f'<div style="text-align:center;padding:20px 12px;background:{THEME_HR["card_bg"]};'
                f'border:1px solid {THEME_HR["border"]};border-radius:12px;margin-bottom:12px;'
                f'box-shadow:0 1px 4px rgba(0,0,0,0.2)">'
                f'<div style="font-size:1.8rem;margin-bottom:4px">{icon}</div>'
                f'<div style="font-size:1.6rem;font-weight:800;color:{color}">{pct:.0%}</div>'
                f'<div style="color:{THEME_HR["text_secondary"]};font-size:0.8rem;text-transform:uppercase;'
                f'letter-spacing:0.04em">{tier}</div>'
                f'<div style="color:#9ca3af;font-size:0.78rem;margin-top:4px">{count} people</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def render_ort_status(teams: list[dict]):
    """Check Organisational Risk Threshold for each team."""
    st.markdown("#### Team Risk Status")

    if not teams:
        st.info("No team data available.")
        return

    alert_teams = [
        t for t in teams
        if t.get("team_size", 0) >= MIN_TEAM_SIZE
        and t.get("high_critical_pct", 0) > ORT_CEILING
        and t.get("consecutive_weeks_elevated", 0) >= ORT_PULSE_CONSECUTIVE_WEEKS
    ]

    if alert_teams:
        st.warning(
            f"**{len(alert_teams)} team(s)** exceed the {ORT_CEILING:.0%} "
            f"High+Critical ceiling for {ORT_PULSE_CONSECUTIVE_WEEKS}+ consecutive weeks. "
            "Individual alerts suppressed; organisational risk report generated."
        )
        for team in alert_teams:
            st.markdown(
                f"- **{team['name']}**: {team['high_critical_pct']:.0%} High+Critical "
                f"({team.get('consecutive_weeks_elevated', 0)} weeks)"
            )
    else:
        st.success("All teams are within acceptable risk thresholds.")


def render_participation(
    scoreable: int,
    responded: int,
    target_sprint1: float = 0.20,
    target_architecture: float = 0.40,
):
    """Render participation rate against Sprint 1 and architecture targets."""
    st.markdown("#### Participation")

    rate = responded / scoreable if scoreable > 0 else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Eligible", str(scoreable))
    with col2:
        st.metric("Completed", str(responded))
    with col3:
        st.metric("Rate", f"{rate:.0%}")

    st.caption(
        "Eligible = employees who consented and are not under exclusion "
        "(ADA, FMLA, formal review, etc.). Completed = submitted assessment."
    )

    if rate >= target_sprint1:
        st.success(f"Sprint 1 target ({target_sprint1:.0%}) reached.")
    else:
        st.warning(
            f"Participation at {rate:.0%} — below Sprint 1 target of {target_sprint1:.0%}."
        )

    if rate < target_architecture:
        st.info(f"Architecture target ({target_architecture:.0%}) not yet reached.")


def render_exclusion_summary(exclusions: dict[str, int]):
    """Render exclusion counts by category."""
    st.markdown("#### Exclusions")

    if not exclusions:
        st.info("No excluded employees.")
        return

    total = sum(exclusions.values())
    st.caption(f"{total} employees outside the scoring window:")
    n = len(exclusions)
    cols = st.columns(n or 1)
    for idx, (category, count) in enumerate(
        sorted(exclusions.items(), key=lambda x: -x[1])
    ):
        label = category.replace("_", " ").title()
        with cols[idx if idx < n else 0]:
            st.markdown(
                f'<div style="padding:16px;text-align:center;background:{THEME_HR["card_bg"]};'
                f'border:1px solid {THEME_HR["border"]};border-radius:10px;margin-bottom:8px;'
                f'box-shadow:0 1px 3px rgba(0,0,0,0.2)">'
                f'<div style="font-size:1.5rem;font-weight:800;color:{THEME_HR["text"]}">{count}</div>'
                f'<div style="color:{THEME_HR["text_secondary"]};font-size:0.78rem;text-transform:uppercase;'
                f'letter-spacing:0.04em">{label}</div></div>',
                unsafe_allow_html=True,
            )


def render_hr_view(
    scores: list[dict],
    teams: list[dict],
    exclusions: dict[str, int],
    scoreable: int,
    responded: int,
):
    """Render the full HR aggregate dashboard."""
    render_header()

    for section_fn in [
        lambda: render_tier_distribution(scores),
        lambda: render_ort_status(teams),
        lambda: render_participation(scoreable, responded),
        lambda: render_exclusion_summary(exclusions),
    ]:
        st.markdown(
            f'<div style="background:{THEME_HR["card_bg"]};border:1px solid {THEME_HR["border"]};'
            'border-radius:14px;padding:24px;margin-bottom:20px;'
            'box-shadow:0 1px 4px rgba(0,0,0,0.2)">',
            unsafe_allow_html=True,
        )
        section_fn()
        st.markdown("</div>", unsafe_allow_html=True)
