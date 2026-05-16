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

THEME = {
    "low": "#10b981",
    "moderate": "#f59e0b",
    "high": "#f97316",
    "critical": "#ef4444",
    "text": "#1a1a2e",
    "text_secondary": "#6c757d",
    "card_bg": "#ffffff",
    "border": "#dee2e6",
    "bg": "#f8f9fa",
}


def _card(title: str | None = None):
    """Context manager for a clean white card."""
    return st.container()


def render_header():
    st.markdown(
        '<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.08em;color:#6c757d;margin:0">Your Assessment</p>',
        unsafe_allow_html=True,
    )
    st.title("Burnout Risk Profile")
    st.caption(
        "Your results are private — only you can see your individual score."
    )


def render_tier_badge(tier: str, probability: float):
    color = THEME.get(tier.lower(), "#888")
    st.markdown(
        f'<div style="display:inline-flex;align-items:center;gap:16px;'
        f'padding:16px 24px;border-radius:12px;background:{color}18;'
        f'border:1px solid {color}44;margin-bottom:20px">'
        f'<span style="font-size:1.8rem;font-weight:800;color:{color};'
        f'text-transform:uppercase;letter-spacing:0.05em">{tier}</span>'
        f'<span style="color:#6c757d;font-size:0.95rem">Burnout score: '
        f'<strong style="color:#1a1a2e">{probability:.1%}</strong></span>'
        f"</div>",
        unsafe_allow_html=True,
    )


def render_tier_explanation(tier: str):
    explanations = {
        "low": "Your current burnout risk is low. No action needed — keep doing what works.",
        "moderate": (
            "Some burnout indicators are present. The resources below may help "
            "you protect your wellbeing before things escalate."
        ),
        "high": (
            "Significant burnout indicators are present. Consider reaching out "
            "to the resources below. Your organisation may receive an anonymised "
            "aggregate signal at team level to trigger support."
        ),
        "critical": (
            "Severe burnout indicators detected. A human reviewer will be in touch "
            "to discuss support options with you — no action is taken without your involvement."
        ),
    }
    msg = explanations.get(tier, "")
    if tier in ("high", "critical"):
        st.warning(msg)
    elif tier == "moderate":
        st.info(msg)
    else:
        st.success(msg)


def render_shap_breakdown(shap_decomposition: list[dict]):
    if not shap_decomposition:
        return

    st.markdown("#### What drove your score")
    st.caption(
        "The biggest factors in your assessment — showing which areas increased "
        "or decreased your burnout risk."
    )

    for item in shap_decomposition:
        label = item.get("label") or item.get("feature", "")
        if not label:
            continue
        direction = item.get("direction", "")
        impact = abs(item.get("impact_value", 0))
        bar_width = min(int(impact * 180), 180)
        color = "#ef4444" if direction == "increases" else "#10b981"
        arrow = "↑" if direction == "increases" else "↓"

        col_label, col_bar = st.columns([4, 1])
        with col_label:
            st.markdown(
                f"**{label}**  "
                f'<span style="color:{color};font-weight:600">{arrow} {impact:.0%}</span>  '
                f'<span style="color:#6c757d;font-size:0.85rem">{direction}</span>',
                unsafe_allow_html=True,
            )
        with col_bar:
            st.markdown(
                f'<div style="height:8px;width:{bar_width}px;background:{color};'
                f'border-radius:4px;margin-top:6px"></div>',
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

    tier_prefix = {
        "moderate": "Self-guided resources",
        "high": "Recommended support pathways",
        "critical": "Urgent support — a reviewer will be in touch",
    }

    st.markdown("#### Recommended resources")
    st.caption(f"Based on your top risk factor: *{top_feature.replace('_', ' ').title()}*")

    for resource in resources:
        st.markdown(
            f'<div style="padding:10px 14px;background:#f8f9fa;border-radius:8px;'
            f'border-left:3px solid #0d7377;margin-bottom:8px;color:#1a1a2e">'
            f"{resource}</div>",
            unsafe_allow_html=True,
        )


def render_data_ownership(employee_id: str, token: str | None = None):
    """Render data ownership controls. token required for authenticated mode."""
    import json as _json

    from src.views.api_client import ApiError, delete_my_data, export_my_data, view_my_data

    st.markdown("#### Your data")
    st.caption(
        "You own your assessment data. Under GDPR Article 17 (Right to Erasure), "
        "you can view, export, or delete it at any time."
    )

    if token is None:
        st.info("Sign in to access your data.")
        return

    try:
        emp_id = int(employee_id)
    except (ValueError, TypeError):
        st.warning("Invalid employee ID.")
        return

    col_view, col_export, col_delete = st.columns(3)
    with col_view:
        if st.button("View my data", use_container_width=True, key=f"view_{employee_id}"):
            try:
                data = view_my_data(token, emp_id)
                with st.expander("Your stored data", expanded=True):
                    st.json(_json.dumps(data.get("data", {}), indent=2, default=str))
            except ApiError as e:
                st.error(f"Could not load: {e}")

    with col_export:
        if st.button("Export as JSON", use_container_width=True, key=f"export_{employee_id}"):
            try:
                result = export_my_data(token, emp_id)
                payload = _json.dumps(result.get("export", {}), indent=2, default=str)
                st.download_button(
                    label="Download JSON",
                    data=payload,
                    file_name=f"oraclaire-data-{employee_id}.json",
                    mime="application/json",
                    use_container_width=True,
                    key=f"dl_{employee_id}",
                )
            except ApiError as e:
                st.error(f"Could not export: {e}")

    with col_delete:
        if st.button("Delete my data", use_container_width=True, key=f"delete_{employee_id}"):
            st.session_state[f"_confirm_delete_{employee_id}"] = True

    if st.session_state.get(f"_confirm_delete_{employee_id}", False):
        st.warning(
            "⚠️ This permanently deletes all your assessment data and cannot be undone. "
            "You will need to re-consent to appear in future assessments."
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Yes, delete everything", key=f"confirm_delete_{employee_id}"):
                try:
                    delete_my_data(token, emp_id)
                    st.success("Your data has been deleted.")
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

    st.markdown("#### Your trend")

    if trajectory == "no_trajectory":
        st.info(
            "Complete at least two assessment cycles to see your burnout trend."
        )
        return

    delta = trajectory_data.get("delta")
    current = trajectory_data.get("current_score")
    previous = trajectory_data.get("previous_score")
    threshold = trajectory_data.get("threshold_used", 0.10)

    icons = {"improved": "↓", "worsened": "↑", "held": "→"}
    colors = {"improved": "#10b981", "worsened": "#ef4444", "held": "#f59e0b"}
    labels = {"improved": "Improving", "worsened": "Worsening", "held": "Holding steady"}

    icon = icons.get(trajectory, "")
    color = colors.get(trajectory, "#888")
    label = labels.get(trajectory, trajectory.title())
    delta_abs = abs(delta) if delta is not None else 0

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:16px;'
        f'padding:16px 20px;border-radius:12px;background:{color}18;'
        f'border:1px solid {color}44;margin-bottom:16px">'
        f'<span style="font-size:1.8rem;font-weight:800;color:{color}">{icon}</span>'
        f'<div>'
        f'<strong style="color:{color};font-size:1rem">{label}</strong><br>'
        f'<span style="color:#6c757d;font-size:0.85rem">'
        f'Burnout score changed by <strong>{delta_abs:.1%}</strong> '
        f'(from {previous:.0%} to {current:.0%})'
        f'</span></div></div>',
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
                "Model not found. Run: `python -m src.model.train`"
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
        if risk_tier is None or burnout_probability is None:
            st.error("Either provide features+seniority_tier or risk_tier+burnout_probability.")
            return
        tier = risk_tier
        probability = burnout_probability
        shap_decomposition = shap or []
        resources_out = resources or []

    # Wrap in a card
    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #dee2e6;'
        f'border-radius:14px;padding:28px;margin-bottom:20px;'
        f'box-shadow:0 1px 4px rgba(0,0,0,0.06)">',
        unsafe_allow_html=True,
    )
    render_tier_badge(tier, probability)
    render_tier_explanation(tier)
    render_shap_breakdown(shap_decomposition)
    render_resources(shap_decomposition, tier)
    st.markdown("</div>", unsafe_allow_html=True)

    # GDPR data section
    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #dee2e6;'
        f'border-radius:14px;padding:24px;margin-bottom:20px;'
        f'box-shadow:0 1px 4px rgba(0,0,0,0.06)">',
        unsafe_allow_html=True,
    )
    render_data_ownership(employee_id, token=auth_token)
    st.markdown("</div>", unsafe_allow_html=True)

    # Trajectory section
    render_trajectory(trajectory_data)
