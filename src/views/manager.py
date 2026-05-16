"""
Manager-facing team burnout risk dashboard.

Shows: team aggregate trend, tier distribution, SHAP-matched action recommendations.
Access: manager (own team only). No individual employee names or scores visible.
"""

from collections import Counter

import streamlit as st

from src.config import ORT_CEILING, TIER_COLORS, TIER_ORDER


def render_header(team_name: str):
    st.title(f"Team: {team_name}")
    st.markdown(
        "Aggregate burnout risk for your team. "
        "No individual employee data is shown."
    )


def render_tier_distribution(cycles: list[dict], current_tiers: dict[str, int]):
    """Render current cycle tier distribution as bar chart."""
    st.subheader("Current risk tier distribution")

    if not current_tiers:
        st.info("No assessment data available yet.")
        return

    total = sum(current_tiers.values())
    st.markdown(f"Based on {total} assessed team members.")

    for tier in TIER_ORDER:
        count = current_tiers.get(tier, 0)
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


def render_trend_chart(cycles: list[dict]):
    """Render High+Critical % trend over cycles as line chart."""
    if not cycles:
        return

    st.subheader("High+Critical trend")

    trend_data = [
        {
            "cycle": f"{c.get('cycle_type', 'cycle')[:3].title()} {c.get('closed_at', '')[:7]}",
            "hc_pct": c.get("high_critical_pct", 0),
        }
        for c in cycles
    ]

    chart_data = {row["cycle"]: row["hc_pct"] for row in trend_data}
    st.line_chart(chart_data)

    for row in trend_data:
        st.caption(f"{row['cycle']}: {row['hc_pct']:.0%} High+Critical")


def render_recommendations(top_factors: list[dict], resources: list[str], worst_tier: str):
    """Render SHAP-matched action recommendations."""
    st.subheader("Recommended actions")

    if not top_factors and not resources:
        st.info("No recommendations available yet.")
        return

    if worst_tier in ("critical", "high"):
        st.warning(
            f"Team has members in the **{worst_tier}** tier. "
            "Consider reaching out to discuss workload and wellbeing."
        )

    if top_factors:
        st.markdown("**Top burnout risk factors for your team:**")
        for factor in top_factors[:3]:
            feat = factor.get("feature", "")
            impact = factor.get("avg_impact", 0)
            direction = factor.get("direction", "increases")
            color = "#ef4444" if direction == "increases" else "#22c55e"
            st.markdown(
                f"- **{feat.replace('_', ' ').title()}** — "
                f"<span style='color:{color}'>{direction} risk</span> "
                f"(avg impact: {impact:.1%})",
                unsafe_allow_html=True,
            )

    if resources:
        st.markdown("**Support resources for your team:**")
        tier_prefix = {
            "moderate": "Self-guided:",
            "high": "Professional support pathways:",
            "critical": "Urgent — seek professional support:",
        }
        st.markdown(tier_prefix.get(worst_tier, "Resources:"))
        for resource in resources:
            st.markdown(f"- {resource}")
    else:
        st.markdown(
            "No specific resource recommendations based on current team SHAP factors."
        )


def render_team_trajectory(
    team_trajectory_data: dict | None,
    team_id: int,
):
    """Render team-level trajectory aggregate with member distribution."""
    st.subheader("Team trend")

    if not team_trajectory_data:
        st.info("No trajectory data available yet.")
        return

    scored = team_trajectory_data.get("scored_count", 0)
    if scored == 0:
        st.info("No team members have been scored in multiple cycles yet.")
        return

    team_traj = team_trajectory_data.get("team_trajectory")
    distribution = team_trajectory_data.get("distribution", {})
    avg_delta = team_trajectory_data.get("average_delta")
    total = sum(distribution.values()) if distribution else 0

    icons = {
        "improved": "📉",
        "worsened": "📈",
        "held": "➡️",
        "no_trajectory": "⏳",
    }
    colors = {
        "improved": "#22c55e",
        "worsened": "#ef4444",
        "held": "#f59e0b",
        "no_trajectory": "#888",
    }
    labels = {
        "improved": "Improving",
        "worsened": "Worsening",
        "held": "Holding steady",
        "no_trajectory": "Not enough history",
    }

    if team_traj and team_traj != "no_trajectory":
        color = colors.get(team_traj, "#888")
        icon = icons.get(team_traj, "")
        label = labels.get(team_traj, team_traj)

        delta_display = ""
        if avg_delta is not None:
            sign = "+" if avg_delta > 0 else ""
            delta_display = f" · avg burnout change: {sign}{avg_delta:.1%}"

        st.markdown(
            f'<div style="padding:16px;border-radius:8px;background:{color}22;'
            f'border-left:4px solid {color};margin-bottom:16px">'
            f'<span style="font-size:24px">{icon}</span> '
            f'<strong style="color:{color};font-size:18px">{label}</strong>'
            f'<p style="margin:4px 0 0 0;color:#555">'
            f'Based on {scored} team members with enough assessment history{delta_display}'
            f'</p></div>',
            unsafe_allow_html=True,
        )
    elif team_traj == "no_trajectory":
        st.info(
            "Not enough team members have completed two or more assessment cycles "
            "to show a team-level trend."
        )
    else:
        st.info("No trajectory data available yet.")

    # Distribution breakdown
    st.markdown("**Member breakdown:**")
    for cat in ["improved", "held", "worsened", "no_trajectory"]:
        count = distribution.get(cat, 0)
        pct = count / total if total > 0 else 0
        color = colors.get(cat, "#888")
        icon = icons.get(cat, "")
        bar_w = int(pct * 200)
        st.markdown(
            f'<div style="margin-bottom:4px;color:#555">'
            f'{icon} {labels.get(cat, cat)}: {count} ({pct:.0%})'
            f'<div style="height:6px;width:{bar_w}px;background:{color};'
            f'border-radius:3px;margin-top:2px"></div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def render_ort_status(
    high_critical_pct: float | None,
    consecutive_weeks_elevated: int,
    team_size: int,
    ort_ceiling: float,
):
    """Render ORT alert status for the team."""
    st.subheader("Team Risk Status")

    if high_critical_pct is None:
        return

    if high_critical_pct > ort_ceiling and consecutive_weeks_elevated >= 2:
        st.warning(
            f"Your team has been at **{high_critical_pct:.0%}** "
            f"High+Critical for {consecutive_weeks_elevated} consecutive weeks, "
            f"which exceeds the **{ort_ceiling:.0%}** threshold. "
            "Individual alerts are suppressed; an organisational risk report "
            "has been sent to HR."
        )
    elif high_critical_pct > ort_ceiling:
        st.info(
            f"Team High+Critical rate is **{high_critical_pct:.0%}**, "
            f"above the **{ort_ceiling:.0%}** threshold. "
            "Continued elevation will trigger organisational risk reporting."
        )
    else:
        st.success(
            f"Team High+Critical rate ({high_critical_pct:.0%}) "
            f"is within acceptable range (below {ort_ceiling:.0%})."
        )


def render_manager_view(
    team_id: int,
    team_name: str,
    team_size: int,
    suppressed: bool,
    suppression_reason: str | None,
    visibility_locked: bool,
    cycles: list[dict],
    tier_distribution: dict[str, int],
    high_critical_pct: float | None,
    consecutive_weeks_elevated: int,
    top_factors: list[dict],
    recommendations: list[str],
    worst_tier: str,
    ort_ceiling: float,
    team_trajectory_data: dict | None = None,
):
    """Render the full manager dashboard for one team."""
    render_header(team_name)

    if suppressed:
        st.warning(
            f"⚠️ Team aggregate is not available: {suppression_reason or 'team too small'}."
        )
        return

    if visibility_locked:
        st.info(
            "Results are temporarily hidden while employees have first access "
            "to their scores (24h after cycle close)."
        )
        return

    # Tier distribution (latest cycle = last in cycles list)
    current_tiers = {}
    if cycles:
        current_tiers = cycles[-1].get("tiers", {})

    render_tier_distribution(cycles, current_tiers)
    render_trend_chart(cycles)
    render_ort_status(high_critical_pct, consecutive_weeks_elevated, team_size, ort_ceiling)
    render_recommendations(top_factors, recommendations, worst_tier)

    if not suppressed and not visibility_locked:
        render_team_trajectory(team_trajectory_data, team_id)
