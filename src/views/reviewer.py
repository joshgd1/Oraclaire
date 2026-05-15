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
from src.views.api_client import (
    ApiError,
    approve_review,
    get_pending_reviews,
    get_review_detail,
    override_review,
)


def _shap_from_api(shap_values: list[dict]) -> list[dict]:
    """Convert API shap_values to the decomposition format expected by render_shap_breakdown."""
    FEATURE_LABELS = {
        "company_type": "Company type",
        "wfh_setup": "Work-from-home setup",
        "resource_allocation": "Resource allocation",
        "mental_fatigue_score": "Energy levels",
        "missing_ra": "Missing resource allocation",
        "missing_mfs": "Missing energy score",
        "seniority_tier": "Seniority level",
        "tenure_days": "Time in this role",
        "tenure_fatigue": "Tenure-adjusted fatigue",
        "tenure_workload": "Tenure workload factor",
    }
    result = []
    for item in (shap_values or [])[:5]:
        feature = item.get("feature", "")
        value = item.get("value", 0)
        result.append({
            "feature": feature,
            "label": FEATURE_LABELS.get(feature, feature.replace("_", " ").title()),
            "impact_value": abs(value),
            "direction": "increases" if value > 0 else "decreases",
        })
    return result


def _render_header():
    st.title("Critical Tier Review Queue")
    st.markdown(
        "Critical-tier assessments require human review before any action. "
        "Review the SHAP context below and approve or override the tier."
    )


def _render_pending_count(pending: int):
    if pending == 0:
        st.success("No pending reviews.")
    else:
        st.warning(f"{pending} assessment(s) awaiting review.")


def _render_review_card(
    employee_id: str,
    review_id: int,
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
            f"<strong>Employee ID:</strong> {employee_id} &nbsp;&nbsp;"
            f"<strong>Risk score:</strong> {probability:.0%} &nbsp;&nbsp;"
            f"<strong>Tier:</strong> {tier.upper()}",
            unsafe_allow_html=True,
        )

        if scored_at:
            st.markdown(f"**Scored at:** {scored_at}")

            scored_dt = datetime.datetime.fromisoformat(scored_at.replace("Z", "+00:00"))
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
        if st.button("Approve", key=f"approve_{review_id}"):
            st.session_state[f"_pending_action_{review_id}"] = "approve"
    with col2:
        if st.button("Override tier", key=f"override_{review_id}"):
            st.session_state[f"_pending_action_{review_id}"] = "override"


def _render_override_form(token: str, employee_id: str, review_id: int):
    """Render tier override form requiring a reason. Submits on button click."""
    st.markdown("### Override tier")
    st.markdown(
        "Changing the tier requires a written reason. "
        "This is logged in the audit trail."
    )

    new_tier = st.selectbox(
        "Select new tier",
        options=[t for t in TIER_ORDER if t != "critical"],
        key=f"new_tier_{review_id}",
    )
    reason = st.text_area(
        "Reason for override (required, 10–1000 characters)",
        key=f"reason_{review_id}",
    )

    if st.button("Submit override", key=f"submit_override_{review_id}"):
        if not reason or len(reason.strip()) < 10:
            st.error("A reason of at least 10 characters is required.")
            return
        try:
            result = override_review(token, review_id, new_tier, reason.strip())
            st.session_state.pop(f"_pending_action_{review_id}", None)
            st.success(
                f"Tier overridden to {result.get('override_new_tier', new_tier).title()} "
                f"for {employee_id}. Reason logged."
            )
            st.rerun()
        except ApiError as e:
            st.error(f"Override failed: {e}")


def render_reviewer_view(*, token: str):
    """
    Render the full reviewer queue using live API data.

    Fetches pending reviews from GET /api/reviews/pending,
    fetches full detail (SHAP + trajectory) for each via GET /api/reviews/{id},
    and handles approve/override POST calls.
    """
    _render_header()

    # Handle pending approve/override actions from prior rerun
    pending_keys = [k for k in st.session_state if k.startswith("_pending_action_")]
    for key in pending_keys:
        review_id = int(key.replace("_pending_action_", ""))
        action = st.session_state.pop(key)
        if action == "approve":
            try:
                result = approve_review(token, review_id)
                st.success(
                    f"Assessment approved. Intervention may proceed."
                )
            except ApiError as e:
                st.error(f"Approve failed: {e}")
        elif action == "override":
            # Fall through to render the override form this rerun
            pass

    # Fetch pending review list
    try:
        pending_data = get_pending_reviews(token)
    except ApiError as e:
        if e.status_code == 401:
            st.error("Session expired. Please sign out and sign in again.")
            return
        st.error(f"Failed to load pending reviews: {e}")
        return

    pending_list = pending_data.get("pending_reviews", [])
    _render_pending_count(len(pending_list))

    if not pending_list:
        return

    # Fetch full detail for each pending review (for SHAP + trajectory)
    review_details: dict[int, dict] = {}
    for summary in pending_list:
        rid = summary["review_id"]
        try:
            detail = get_review_detail(token, rid)
            review_details[rid] = detail
        except ApiError as e:
            st.warning(f"Could not load detail for review {rid}: {e}")
            review_details[rid] = {"review_id": rid, "risk_score": {}}

    # Render review cards
    for summary in pending_list:
        review_id = summary["review_id"]
        detail = review_details.get(review_id, {})
        risk_score = detail.get("risk_score", {})
        employee = detail.get("employee", {})
        trajectory_list = detail.get("trajectory", [])
        shap_values = risk_score.get("shap_values", [])

        # Derive trajectory string
        trajectory_str = None
        if len(trajectory_list) >= 2:
            first = trajectory_list[-1].get("numeric_score", 0)
            last = trajectory_list[0].get("numeric_score", 0)
            if last > first + 0.05:
                trajectory_str = "worsened"
            elif last < first - 0.05:
                trajectory_str = "improved"
            else:
                trajectory_str = "stable"

        pending_action = st.session_state.get(f"_pending_action_{review_id}")

        _render_review_card(
            employee_id=str(summary.get("employee_id", employee.get("id", "?"))),
            review_id=review_id,
            probability=summary.get("numeric_score", 0.5),
            shap_decomposition=_shap_from_api(shap_values),
            scored_at=summary.get("scored_at"),
            trajectory=trajectory_str,
        )

        if pending_action == "override":
            emp_id = str(summary.get("employee_id", employee.get("id", "?")))
            _render_override_form(token, emp_id, review_id)
