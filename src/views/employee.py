"""
Employee-facing burnout risk dashboard.

Shows: risk tier, SHAP breakdown, curated resources, trajectory.
Access: own data only. No HR/manager visibility.
"""

import streamlit as st

from src.config import (
    EMPLOYEE_FIRST_GATE_HOURS,
    FEATURE_LABELS,
    RESOURCES,
    TIER_COLORS,
    TIER_ORDER,
)
from src.model.serve import score_employee


def render_header():
    st.title("Your Burnout Risk Assessment")
    st.markdown(
        "This shows your current burnout risk classification based on your "
        "most recent assessment. Your results are private — only you can see them."
    )


def render_tier_badge(tier: str, probability: float):
    color = TIER_COLORS.get(tier, "#888")
    st.markdown(
        f'<div style="padding:16px;border-radius:8px;background:{color}22;'
        f'border-left:4px solid {color};margin-bottom:16px">'
        f'<h2 style="margin:0;color:{color}">{tier.upper()}</h2>'
        f'<p style="margin:4px 0 0 0;color:#555">Risk score: {probability:.1%}</p>'
        f"</div>",
        unsafe_allow_html=True,
    )


def render_tier_explanation(tier: str):
    explanations = {
        "low": "Your current burnout risk is low. No action needed.",
        "moderate": (
            "Some burnout indicators are present. The resources below may help "
            "you maintain your wellbeing."
        ),
        "high": (
            "Significant burnout indicators are present. Consider reaching out "
            "to the resources below. Your organisation may receive an anonymised "
            "aggregate signal at team level."
        ),
        "critical": (
            "Severe burnout indicators detected. A human review is required "
            "before any action is taken. You will be contacted by a reviewer "
            "who will discuss support options with you."
        ),
    }
    st.info(explanations.get(tier, ""))


def render_shap_breakdown(shap_decomposition: list[dict]):
    if not shap_decomposition:
        st.write("No detailed breakdown available for this assessment.")
        return

    st.subheader("What's driving your score")
    st.markdown(
        "These are the main factors contributing to your assessment result. "
        "Each shows how much it increased or decreased your risk level."
    )

    for item in shap_decomposition:
        label = item.get("label") or item.get("feature", "")
        if not label:
            continue
        direction = item.get("direction", "")
        impact = abs(item.get("impact_value", 0))
        bar_width = min(int(impact * 200), 200)
        color = "#ef4444" if direction == "increases" else "#22c55e"
        arrow = "+" if direction == "increases" else "-"

        st.markdown(
            f'<div style="margin-bottom:8px">'
            f"<strong>{label}</strong> — {direction} risk "
            f'<span style="color:{color};font-weight:bold">{arrow}{impact:.1%}</span>'
            f'<div style="height:8px;width:{bar_width}px;background:{color};'
            f'border-radius:4px;margin-top:4px"></div>'
            f"</div>",
            unsafe_allow_html=True,
        )


def render_resources(shap_decomposition: list[dict], tier: str):
    if tier == "low":
        return

    if not shap_decomposition:
        return

    top_feature = shap_decomposition[0].get("feature", "")
    resources = RESOURCES.get(top_feature, [])

    if not resources:
        return

    st.subheader("Recommended resources")
    tier_prefix = {
        "moderate": "Self-guided resources:",
        "high": "Professional support pathways:",
        "critical": "Urgent support — a reviewer will discuss options with you:",
    }
    st.markdown(tier_prefix.get(tier, "Resources:"))

    for resource in resources:
        st.markdown(f"- {resource}")


def render_data_ownership(employee_id: str, token: str | None = None):
    """Render data ownership controls. token required for authenticated mode."""
    import streamlit as st

    from src.views.api_client import ApiError, delete_my_data, export_my_data, view_my_data

    st.subheader("Your data")
    st.markdown(
        "You own your data. You can view, export, or delete your assessment "
        "data at any time under GDPR Article 17 — Right to Erasure."
    )

    if token is None:
        st.info("Sign in to access your data.")
        return

    try:
        emp_id = int(employee_id)
    except (ValueError, TypeError):
        st.warning("Invalid employee ID.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("View my data", key=f"view_{employee_id}"):
            try:
                data = view_my_data(token, emp_id)
                with st.expander("Your stored data", expanded=True):
                    import json
                    st.json(json.dumps(data.get("data", {}), indent=2, default=str))
            except ApiError as e:
                st.error(f"Could not load your data: {e}")

    with col2:
        if st.button("Export as JSON", key=f"export_{employee_id}"):
            try:
                result = export_my_data(token, emp_id)
                import json
                payload = json.dumps(result.get("export", {}), indent=2, default=str)
                st.download_button(
                    label="Download JSON",
                    data=payload,
                    file_name=f"oraclaire-data-{employee_id}.json",
                    mime="application/json",
                    key=f"dl_{employee_id}",
                )
            except ApiError as e:
                st.error(f"Could not export your data: {e}")

    with col3:
        if st.button("Delete my data", key=f"delete_{employee_id}"):
            st.session_state[f"_confirm_delete_{employee_id}"] = True

    # Delete confirmation flow
    if st.session_state.get(f"_confirm_delete_{employee_id}", False):
        st.warning("⚠️ This will permanently delete all your assessment data. This cannot be undone.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Yes, delete everything", key=f"confirm_delete_{employee_id}"):
                try:
                    delete_my_data(token, emp_id)
                    st.success(
                        "Your data has been deleted. "
                        "You will need to re-consent to appear in future assessments."
                    )
                    st.session_state.pop(f"_confirm_delete_{employee_id}", None)
                except ApiError as e:
                    st.error(f"Delete failed: {e}")
                st.rerun()
        with c2:
            if st.button("Cancel", key=f"cancel_delete_{employee_id}"):
                st.session_state.pop(f"_confirm_delete_{employee_id}", None)
                st.rerun()


def render_trajectory(trajectory_data: dict | None):
    """Render trajectory classification with visual indicator."""
    if not trajectory_data:
        return

    trajectory = trajectory_data.get("trajectory", "no_trajectory")

    st.divider()
    st.subheader("Your trend")

    if trajectory == "no_trajectory":
        st.info(
            "Not enough assessment history yet to show a trend. "
            "Complete at least two assessment cycles to see your trajectory."
        )
        return

    delta = trajectory_data.get("delta")
    current = trajectory_data.get("current_score")
    previous = trajectory_data.get("previous_score")
    threshold = trajectory_data.get("threshold_used", 0.10)

    icons = {
        "improved": "📉",
        "worsened": "📈",
        "held": "➡️",
    }
    colors = {
        "improved": "#22c55e",
        "worsened": "#ef4444",
        "held": "#f59e0b",
    }
    labels = {
        "improved": "Improving",
        "worsened": "Worsening",
        "held": "Holding steady",
    }

    icon = icons.get(trajectory, "")
    color = colors.get(trajectory, "#888")
    label = labels.get(trajectory, trajectory.title())

    delta_abs = abs(delta) if delta is not None else 0

    st.markdown(
        f'<div style="padding:16px;border-radius:8px;background:{color}22;'
        f'border-left:4px solid {color};margin-bottom:16px">'
        f'<span style="font-size:24px">{icon}</span> '
        f'<strong style="color:{color};font-size:18px">{label}</strong>'
        f'<p style="margin:4px 0 0 0;color:#555">'
        f'Burnout score changed by <strong>{delta_abs:.1%}</strong> '
        f'(from {previous:.0%} to {current:.0%}, threshold ±{threshold:.0%})'
        f'</p></div>',
        unsafe_allow_html=True,
    )


def render_employee_view(
    employee_id: str,
    features: dict | None = None,
    seniority_tier: int | None = None,
    model_path: str | None = None,
    *,
    risk_tier: str | None = None,
    burnout_probability: float | None = None,
    shap: list[dict] | None = None,
    resources: list[str] | None = None,
    trajectory_data: dict | None = None,
    auth_token: str | None = None,
):
    """Render the full employee dashboard.

    Two modes:
    - Local scoring: pass features + seniority_tier (calls score_employee)
    - API-backed: pass risk_tier + burnout_probability + shap + resources
    """
    render_header()

    if features is not None and seniority_tier is not None:
        # Local scoring path (demo mode)
        try:
            kwargs: dict = {
                "employee_id": employee_id,
                "features": features,
                "seniority_tier": seniority_tier,
            }
            if model_path:
                kwargs["model_path"] = model_path
            result = score_employee(**kwargs)
        except FileNotFoundError:
            st.error(
                "Model not found. Run the training pipeline first: "
                "`python -m src.model.train`"
            )
            return
        except ValueError as e:
            st.error(f"Input validation error: {e}")
            return
        tier = result["risk_tier"]
        probability = result["burnout_probability"]
        shap_decomposition = result["shap"]
        resources_out = result.get("resources", [])
    else:
        # API-backed path
        if risk_tier is None or burnout_probability is None:
            st.error("Either provide features+seniority_tier or risk_tier+burnout_probability.")
            return
        tier = risk_tier
        probability = burnout_probability
        shap_decomposition = shap or []
        resources_out = resources or []

    render_tier_badge(tier, probability)
    render_tier_explanation(tier)
    render_shap_breakdown(shap_decomposition)
    render_resources(shap_decomposition, tier)

    st.divider()
    render_data_ownership(employee_id, token=auth_token)
    render_trajectory(trajectory_data)
