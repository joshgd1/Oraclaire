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
    AuthExpiredError,
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
    st.markdown(
        '<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.08em;color:#6c757d;margin:0">Review Queue</p>',
        unsafe_allow_html=True,
    )
    st.title("Critical Tier Reviews")
    st.caption(
        "Critical-tier assessments require human review before any action is taken. "
        f"All reviews must be completed within {REVIEW_TIMEOUT_HOURS} hours of scoring."
    )


def _render_pending_count(pending: int):
    if pending == 0:
        st.success("No pending reviews — all caught up.")
    else:
        st.warning(f"**{pending}** assessment(s) awaiting review.")


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
    color_map = {
        "low": "#10b981",
        "moderate": "#f59e0b",
        "high": "#f97316",
        "critical": "#ef4444",
    }
    color = color_map.get(tier.lower(), "#888")

    deadline_html = ""
    if scored_at:
        scored_dt = datetime.datetime.fromisoformat(scored_at.replace("Z", "+00:00"))
        deadline = scored_dt + datetime.timedelta(hours=REVIEW_TIMEOUT_HOURS)
        remaining = deadline - datetime.datetime.now(datetime.timezone.utc)
        if remaining.total_seconds() > 0:
            hours = remaining.total_seconds() / 3600
            deadline_html = (
                f'<span style="color:#6c757d;font-size:0.85rem">'
                f'Review by: <strong>{hours:.1f}h remaining</strong></span>'
            )
        else:
            deadline_html = (
                f'<span style="color:#ef4444;font-size:0.85rem;font-weight:600">'
                f'Deadline passed — auto-escalation pending</span>'
            )

    trajectory_html = ""
    if trajectory:
        traj_color = {"worsened": "#ef4444", "improved": "#10b981", "stable": "#f59e0b"}.get(
            trajectory, "#6c757d"
        )
        trajectory_html = (
            f'<span style="margin-left:16px;color:{traj_color};font-size:0.85rem">'
            f'Trend: <strong>{trajectory}</strong></span>'
        )

    shap_rows = ""
    if shap_decomposition:
        for item in (shap_decomposition[:5] or []):
            label = item.get("label") or item.get("feature", "unknown")
            direction = item.get("direction", "")
            impact = abs(item.get("impact_value", 0))
            arrow = "↑" if direction == "increases" else "↓"
            d_color = "#ef4444" if direction == "increases" else "#10b981"
            shap_rows += (
                f'<div style="display:flex;justify-content:space-between;padding:6px 0;'
                f'border-bottom:1px solid #f3f4f6;color:#374151;font-size:0.88rem">'
                f'<span>{label}</span>'
                f'<span style="color:{d_color};font-weight:600">{arrow} {impact:.0%}</span>'
                f'</div>'
            )

    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #dee2e6;'
        f'border-radius:14px;padding:24px;margin-bottom:20px;'
        f'box-shadow:0 1px 4px rgba(0,0,0,0.06)">'

        # Header row
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">'
        f'<span style="font-size:0.78rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.06em;color:{color};background:{color}18;'
        f'padding:4px 10px;border-radius:6px">{tier.upper()}</span>'
        f'<strong style="font-size:1rem;color:#1a1a2e">Employee {employee_id}</strong>'
        f'<span style="margin-left:auto;color:#6c757d;font-size:0.9rem">'
        f'Score: <strong>{probability:.1%}</strong></span>'
        f'{trajectory_html}</div>'

        # Deadline
        f'{deadline_html}'

        # SHAP factors
        f'{shap_rows}'

        f'</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        if pending_action == "approve":
            st.warning(
                f"**Confirm approval** for Employee **{employee_id}**? "
                "This will allow the intervention to proceed."
            )
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button(
                    "✓  Yes, approve",
                    key=f"confirm_approve_{review_id}",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state[f"_pending_action_{review_id}"] = "confirmed_approve"
                    st.rerun()
            with col_no:
                if st.button(
                    "✕  Cancel",
                    key=f"cancel_approve_{review_id}",
                    use_container_width=True,
                ):
                    st.session_state.pop(f"_pending_action_{review_id}", None)
                    st.rerun()
        else:
            st.button(
                "✓  Approve",
                key=f"approve_{review_id}",
                use_container_width=True,
            )
            if st.session_state.get(f"approve_{review_id}", False):
                st.session_state[f"_pending_action_{review_id}"] = "approve"
    with col2:
        st.button(
            "↻  Override tier",
            key=f"override_{review_id}",
            use_container_width=True,
        )
        if st.session_state.get(f"override_{review_id}", False):
            st.session_state[f"_pending_action_{review_id}"] = "override"


def _render_override_form(token: str, employee_id: str, review_id: int):
    """Render tier override form with reason and confirmation step."""
    st.markdown("##### Override tier")
    st.caption(
        "Changing the tier requires a written reason, logged in the audit trail. "
        "This action cannot be undone."
    )

    new_tier = st.selectbox(
        "New tier",
        options=[t for t in TIER_ORDER if t != "critical"],
        key=f"new_tier_{review_id}",
    )
    reason = st.text_area(
        "Reason (required — min 10 characters)",
        key=f"reason_{review_id}",
        placeholder="Describe the context for this override...",
    )

    confirm_key = f"_override_confirm_{review_id}"

    if not st.session_state.get(confirm_key, False):
        if reason and len(reason.strip()) < 10:
            st.warning("Please write at least 10 characters to describe the reason.")
        if st.button("Continue to confirmation", key=f"step1_{review_id}"):
            if not reason or len(reason.strip()) < 10:
                st.warning("A reason of at least 10 characters is required.")
            else:
                st.session_state[confirm_key] = True
                st.rerun()
    else:
        st.warning(
            f"You're about to override Employee **{employee_id}**'s tier to "
            f"**{new_tier.upper()}**. This cannot be undone."
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, override tier", key=f"confirm_override_{review_id}", type="primary"):
                try:
                    result = override_review(token, review_id, new_tier, reason.strip())
                    st.session_state.pop(f"_pending_action_{review_id}", None)
                    st.session_state.pop(confirm_key, None)
                    st.success(
                        f"Tier overridden to {result.get('override_new_tier', new_tier).title()} "
                        f"for {employee_id}. Reason logged."
                    )
                    st.rerun()
                except AuthExpiredError:
                    raise
                except ApiError as e:
                    st.error(f"Override failed: {e}")
        with col2:
            if st.button("Cancel", key=f"cancel_override_{review_id}"):
                st.session_state.pop(confirm_key, None)
                st.session_state.pop(f"_pending_action_{review_id}", None)
                st.rerun()


def render_reviewer_view(*, token: str):
    """Render the full reviewer queue using live API data."""
    _render_header()

    # Handle pending approve/override actions from prior rerun
    for key in [k for k in st.session_state if k.startswith("_pending_action_")]:
        review_id = int(key.replace("_pending_action_", ""))
        action = st.session_state.pop(key)
        if action == "confirmed_approve":
            try:
                approve_review(token, review_id)
                st.success("Assessment approved. Intervention may proceed.")
            except AuthExpiredError:
                raise
            except ApiError as e:
                st.error(f"Approve failed: {e}")
        elif action == "override":
            pass  # Fall through to render the override form

    # Fetch pending review list
    try:
        pending_data = get_pending_reviews(token)
    except AuthExpiredError:
        raise  # Bubble up to page_reviewer() wrapper for session clear + rerun
    except ApiError as e:
        st.error(f"Failed to load pending reviews: {e}")
        return

    pending_list = pending_data.get("pending_reviews", [])
    _render_pending_count(len(pending_list))

    if not pending_list:
        return

    # Fetch full detail for each pending review
    review_details: dict[int, dict] = {}
    for summary in pending_list:
        rid = summary["review_id"]
        try:
            detail = get_review_detail(token, rid)
            review_details[rid] = detail
        except AuthExpiredError:
            raise  # Bubble up to page_reviewer() wrapper
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
