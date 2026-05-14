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


def render_header():
    st.title("Organisational Burnout Overview")
    st.markdown(
        "Aggregate burnout risk across the organisation. "
        "No individual employee data is shown."
    )


def render_tier_distribution(scores: list[dict]):
    """Render tier distribution bar chart from list of scored results."""
    if not scores:
        st.warning("No assessment data available yet.")
        return

    tiers = Counter(s.get("risk_tier", "unknown") for s in scores)
    total = len(scores)

    st.subheader("Risk tier distribution")
    st.markdown(f"Based on {total} assessed employees.")

    for tier in TIER_ORDER:
        count = tiers.get(tier, 0)
        pct = count / total if total > 0 else 0
        color = TIER_COLORS.get(tier, "#888")
        bar_width = int(pct * 300)

        st.markdown(
            f'<div style="margin-bottom:6px">'
            f"<strong>{tier.title()}</strong>: {count} ({pct:.0%})"
            f'<div style="height:12px;width:{bar_width}px;background:{color};'
            f'border-radius:4px;margin-top:2px"></div>'
            f"</div>",
            unsafe_allow_html=True,
        )


def render_ort_status(teams: list[dict]):
    """Check Organisational Risk Threshold for each team.

    Each team dict should have: name, high_critical_pct,
    consecutive_weeks_elevated, team_size.
    """
    st.subheader("Organisational Risk Threshold")

    if not teams:
        st.info("No team data available.")
        return

    alerts = []
    ok_teams = []

    for team in teams:
        if team.get("team_size", 0) < MIN_TEAM_SIZE:
            continue
        hc_pct = team.get("high_critical_pct", 0)
        weeks = team.get("consecutive_weeks_elevated", 0)
        if hc_pct > ORT_CEILING and weeks >= ORT_PULSE_CONSECUTIVE_WEEKS:
            alerts.append(team)
        else:
            ok_teams.append(team)

    if alerts:
        st.warning(
            f"{len(alerts)} team(s) exceed the {ORT_CEILING:.0%} "
            f"High+Critical ceiling for {ORT_PULSE_CONSECUTIVE_WEEKS}+ "
            f"consecutive weeks. Individual alerts suppressed; "
            f"organisational risk report generated."
        )
        for team in alerts:
            st.markdown(
                f"- **{team['name']}**: {team['high_critical_pct']:.0%} "
                f"High+Critical ({team.get('consecutive_weeks_elevated', 0)} "
                f"consecutive weeks)"
            )
    else:
        st.success("All teams within acceptable risk thresholds.")


def render_participation(
    scoreable: int,
    responded: int,
    target_sprint1: float = 0.20,
    target_architecture: float = 0.40,
):
    """Render participation rate against Sprint 1 and architecture targets."""
    st.subheader("Participation")
    rate = responded / scoreable if scoreable > 0 else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Scoreable population", str(scoreable))
    with col2:
        st.metric("Responded", str(responded))
    with col3:
        st.metric("Participation rate", f"{rate:.0%}")

    sprint1_met = rate >= target_sprint1
    arch_met = rate >= target_architecture

    if sprint1_met:
        st.success(f"Sprint 1 target ({target_sprint1:.0%}) reached.")
    else:
        st.warning(
            f"Participation at {rate:.0%} — below Sprint 1 target "
            f"of {target_sprint1:.0%}."
        )

    if not arch_met:
        st.info(
            f"Architecture target ({target_architecture:.0%}) not yet reached."
        )


def render_exclusion_summary(exclusions: dict[str, int]):
    """Render exclusion counts by category."""
    st.subheader("Exclusions")

    if not exclusions:
        st.info("No excluded employees.")
        return

    total = sum(exclusions.values())
    st.markdown(f"{total} employees outside scoring window:")

    for category, count in sorted(exclusions.items(), key=lambda x: -x[1]):
        st.markdown(f"- {category.replace('_', ' ').title()}: {count}")


def render_hr_view(
    scores: list[dict],
    teams: list[dict],
    exclusions: dict[str, int],
    scoreable: int,
    responded: int,
):
    """Render the full HR aggregate dashboard."""
    render_header()
    render_tier_distribution(scores)
    render_ort_status(teams)
    render_participation(scoreable, responded)
    render_exclusion_summary(exclusions)
