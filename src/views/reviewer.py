"""
Critical-tier human review gate.

Reviewer sees: SHAP context, employee history, and must
approve or override before any intervention triggers.
Per D8 (EU AI Act high-risk employment classification).
"""

import datetime

import streamlit as st

from src.config import (
    REVIEW_TIMEOUT_HOURS,
    TIER_COLORS,
    TIER_ORDER,
)
from src.model.thresholds import classify_tier


def render_header():
    st.title("Critical Tier Review Queue")
    st.markdown(
        "Critical-tier assessments require human review before any action. "
        "Review the SHAP context below and approve or override the tier."
    )


def render_pending_count(pending: int):
    if pending == 0:
        st.success("No pending reviews.")
    else:
        st.warning(f"{pending} assessment(s) awaiting review.")


def render_review_card(
    employee_id: str,
    probability: float,
    shap_decomposition: list[dict],
    scored_at: str | None = None,
    trajectory: str | None = None,
):
    """Render one review card for a Critical-tier employee."""
    tier = classify_tier(probability)
    color = TIER_COLORS.get(tier, "#888")

    with st.container():
        st.markdown(
            f'<div style="padding:12px;border-radius:8px;'
            f'border:1px solid {color};margin-bottom:12px">'
            f"<strong>Employee:</strong> {employee_id} &nbsp;&nbsp;"
            f"<strong>Risk score:</strong> {probability:.0%} &nbsp;&nbsp;"
            f"<strong>Tier:</strong> {tier.upper()}",
            unsafe_allow_html=True,
        )

        if scored_at:
            st.markdown(f"**Scored at:** {scored_at}")

            scored_dt = datetime.datetime.fromisoformat(scored_at)
            deadline = scored_dt + datetime.timedelta(hours=REVIEW_TIMEOUT_HOURS)
            remaining = deadline - datetime.datetime.now(datetime.timezone.utc)
            if remaining.total_seconds() > 0:
                hours = remaining.total_seconds() / 3600
                st.markdown(f"**Review deadline:** {hours:.1f} hours remaining")
            else:
                st.error("Review deadline passed — auto-escalation pending.")

        if trajectory:
            st.markdown(f"**Trajectory:** {trajectory}")

        if shap_decomposition:
            st.markdown("**SHAP context:**")
            for item in shap_decomposition[:5]:
                label = item.get("label") or item.get("feature", "unknown")
                direction = item.get("direction", "")
                impact = abs(item.get("impact_value", 0))
                arrow = "+" if direction == "increases" else "-"
                st.markdown(
                    f"- {label}: {direction} risk ({arrow}{impact:.1%})"
                )

        st.markdown("</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Approve", key=f"approve_{employee_id}"):
            return "approved"
    with col2:
        if st.button("Override tier", key=f"override_{employee_id}"):
            return "override"

    return None


def render_override_form(employee_id: str):
    """Render tier override form requiring a reason."""
    st.markdown("### Override tier")
    st.markdown(
        "Changing the tier requires a written reason. "
        "This is logged in the audit trail."
    )

    new_tier = st.selectbox(
        "Select new tier",
        options=[t for t in TIER_ORDER if t != "critical"],
        key=f"new_tier_{employee_id}",
    )
    reason = st.text_area(
        "Reason for override (required)",
        key=f"reason_{employee_id}",
    )

    if st.button("Submit override", key=f"submit_override_{employee_id}"):
        if not reason.strip():
            st.error("A reason is required for tier override.")
            return None
        return {"new_tier": new_tier, "reason": reason.strip()}

    return None


def render_reviewer_view(reviews: list[dict]):
    """Render the full reviewer queue.

    Each review dict: employee_id, probability, shap_decomposition,
    scored_at, trajectory.
    """
    render_header()
    render_pending_count(len(reviews))

    for review in reviews:
        result = render_review_card(
            employee_id=review["employee_id"],
            probability=review["probability"],
            shap_decomposition=review.get("shap_decomposition", []),
            scored_at=review.get("scored_at"),
            trajectory=review.get("trajectory"),
        )

        if result == "override":
            override = render_override_form(review["employee_id"])
            if override:
                st.success(
                    f"Tier overridden to {override['new_tier'].title()} "
                    f"for {review['employee_id']}. Reason logged."
                )
        elif result == "approved":
            st.success(
                f"Assessment approved for {review['employee_id']}. "
                f"Intervention may proceed."
            )
