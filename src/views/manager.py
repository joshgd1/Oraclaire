"""
Manager-facing team burnout risk dashboard.

Shows: team aggregate trend, tier distribution, SHAP-matched action recommendations.
Access: manager (own team only). No individual employee names or scores visible.
"""

from collections import Counter

import streamlit as st

from src.config import ORT_CEILING, TIER_COLORS, TIER_ORDER


TIER_THEME_MGR = {
    "low": "#10b981",
    "moderate": "#f59e0b",
    "high": "#f97316",
    "critical": "#ef4444",
}

THEME_MGR = {
    "card_bg": "#2a2a3e",
    "border": "#3d3d5c",
    "text": "#e5e7eb",
    "text_secondary": "#9ca3af",
    "bg": "#1e1e2e",
}


def render_header(team_name: str):
    st.markdown(
        f'<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.08em;color:{THEME_MGR["text_secondary"]};margin:0">Manager</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<h1 style="font-size:1.5rem;font-weight:700;color:{THEME_MGR["text"]};margin:0 0 4px 0;'
        f'line-height:1.3">Team: {team_name}</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="color:{THEME_MGR["text_secondary"]};font-size:0.875rem;margin:0 0 20px 0">'
        f"Aggregate burnout risk for your team &mdash; no individual scores are shown.</p>",
        unsafe_allow_html=True,
    )


def render_tier_distribution(cycles: list[dict], current_tiers: dict[str, int]):
    """Render current cycle tier distribution as bar chart."""
    st.markdown("#### Current risk tier distribution")

    if not current_tiers:
        st.info("No assessment data available yet.")
        return

    total = sum(current_tiers.values())
    st.caption(f"Based on {total} assessed team members.")

    cols = st.columns(4)
    tier_icons = {"low": "✓", "moderate": "∼", "high": "⚠", "critical": "✕"}
    for idx, tier in enumerate(TIER_ORDER):
        count = current_tiers.get(tier, 0)
        pct = count / total if total > 0 else 0
        color = TIER_THEME_MGR.get(tier, "#888")
        icon = tier_icons.get(tier, "")
        with cols[idx]:
            st.markdown(
                f'<div style="text-align:center;padding:20px 12px;background:{THEME_MGR["card_bg"]};'
                f'border:1px solid {THEME_MGR["border"]};border-radius:12px;margin-bottom:12px;'
                f'box-shadow:0 1px 4px rgba(0,0,0,0.2)">'
                f'<div style="font-size:1.8rem;margin-bottom:4px">{icon}</div>'
                f'<div style="font-size:1.6rem;font-weight:800;color:{color}">{pct:.0%}</div>'
                f'<div style="color:{THEME_MGR["text_secondary"]};font-size:0.8rem;text-transform:uppercase;'
                f'letter-spacing:0.04em">{tier}</div>'
                f'<div style="color:#9ca3af;font-size:0.78rem;margin-top:4px">{count} people</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def render_trend_chart(cycles: list[dict]):
    """Render High+Critical % trend over cycles as line chart."""
    if not cycles:
        return

    st.markdown("#### High+Critical trend")

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
    st.markdown("#### Recommended actions")

    if not top_factors and not resources:
        st.info("No recommendations available yet.")
        return

    if worst_tier in ("critical", "high"):
        st.warning(
            f"Team has members in the **{worst_tier}** tier. "
            "Consider reaching out to discuss workload and wellbeing."
        )

    if top_factors:
        st.caption("Top burnout risk factors for your team:")
        for factor in top_factors[:3]:
            feat = factor.get("feature", "")
            impact = factor.get("avg_impact", 0)
            direction = factor.get("direction", "increases")
            color = "#ef4444" if direction == "increases" else "#10b981"
            st.markdown(
                f'- **{feat.replace("_", " ").title()}** — '
                f'<span style="color:{color}">{direction} risk</span> '
                f'(avg impact: {impact:.1%})',
                unsafe_allow_html=True,
            )

    if resources:
        st.markdown("**Support resources:**")
        tier_prefix = {
            "moderate": "Self-guided:",
            "high": "Professional support pathways:",
            "critical": "Urgent — seek professional support:",
        }
        st.caption(tier_prefix.get(worst_tier, "Resources:"))
        for resource in resources:
            st.markdown(
                f'<div style="padding:8px 12px;background:{THEME_MGR["bg"]};border-radius:6px;'
                f'border-left:3px solid #0d7377;margin-bottom:6px;color:{THEME_MGR["text"]}">'
                f"{resource}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption(
            "No specific resource recommendations based on current team SHAP factors."
        )


def render_team_trajectory(
    team_trajectory_data: dict | None,
    team_id: int,
):
    """Render team-level trajectory aggregate with member distribution."""
    st.markdown("#### Team trend")

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

    icons = {"improved": "↓", "worsened": "↑", "held": "→", "no_trajectory": "·"}
    colors = {
        "improved": "#10b981",
        "worsened": "#ef4444",
        "held": "#f59e0b",
        "no_trajectory": "#9ca3af",
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
            delta_display = f" · avg change: {sign}{avg_delta:.1%}"

        st.markdown(
            f'<div style="display:flex;align-items:center;gap:16px;'
            f'padding:16px 20px;border-radius:12px;background:{color}18;'
            f'border:1px solid {color}44;margin-bottom:16px">'
            f'<span style="font-size:1.8rem;font-weight:800;color:{color}">{icon}</span>'
            f'<div>'
            f'<strong style="color:{color}">{label}</strong><br>'
            f'<span style="color:{THEME_MGR["text_secondary"]};font-size:0.85rem">'
            f'{scored} team members with enough history{delta_display}</span></div></div>',
            unsafe_allow_html=True,
        )
    elif team_traj == "no_trajectory":
        st.info(
            "Not enough team members have completed two or more assessment cycles "
            "to show a team-level trend."
        )
    else:
        st.info("No trajectory data available yet.")

    if distribution:
        st.caption("**Member breakdown:**")
        for cat in ["improved", "held", "worsened", "no_trajectory"]:
            count = distribution.get(cat, 0)
            pct = count / total if total > 0 else 0
            color = colors.get(cat, "#888")
            bar_w = int(pct * 160)
            st.markdown(
                f'<div style="margin-bottom:6px;color:{THEME_MGR["text_secondary"]};font-size:0.88rem">'
                f'{labels.get(cat, cat)}: {count} ({pct:.0%})'
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
    st.markdown("#### Team Risk Status")

    if high_critical_pct is None:
        return

    if high_critical_pct > ort_ceiling and consecutive_weeks_elevated >= 2:
        st.warning(
            f"Your team has been at **{high_critical_pct:.0%}** "
            f"High+Critical for {consecutive_weeks_elevated} consecutive weeks, "
            f"exceeding the **{ort_ceiling:.0%}** threshold. "
            "Individual alerts are suppressed; an organisational risk report has been sent to HR."
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
            f"Team aggregate is not available: {suppression_reason or 'team too small'}."
        )
        return

    if visibility_locked:
        st.info(
            "Results are temporarily hidden while employees have first access "
            "to their scores (24h after cycle close)."
        )
        return

    current_tiers = {}
    if cycles:
        current_tiers = cycles[-1].get("tiers", {})

    sections = [
        lambda: render_tier_distribution(cycles, current_tiers),
        lambda: render_trend_chart(cycles),
        lambda: render_ort_status(high_critical_pct, consecutive_weeks_elevated, team_size, ort_ceiling),
        lambda: render_recommendations(top_factors, recommendations, worst_tier),
    ]
    if not suppressed and not visibility_locked:
        sections.append(lambda: render_team_trajectory(team_trajectory_data, team_id))

    for section_fn in sections:
        st.markdown(
            f'<div style="background:{THEME_MGR["card_bg"]};border:1px solid {THEME_MGR["border"]};'
            'border-radius:14px;padding:24px;margin-bottom:20px;'
            'box-shadow:0 1px 4px rgba(0,0,0,0.2)">',
            unsafe_allow_html=True,
        )
        section_fn()
        st.markdown("</div>", unsafe_allow_html=True)
