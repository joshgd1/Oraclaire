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
        f'<p style="margin:4px 0 0 0;color:#555">Risk score: {probability:.0%}</p>'
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


def render_data_ownership(employee_id: str):
    st.subheader("Your data")
    st.markdown(
        "You own your data. You can view, export, or delete your assessment "
        "data at any time."
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        st.button("View my data", key=f"view_{employee_id}")
    with col2:
        st.button("Export as JSON", key=f"export_{employee_id}")
    with col3:
        st.button("Delete my data", key=f"delete_{employee_id}")


def render_employee_view(
    employee_id: str,
    features: dict,
    seniority_tier: int,
    model_path: str | None = None,
):
    """Render the full employee dashboard for one scored employee."""
    render_header()

    try:
        kwargs = {
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

    render_tier_badge(result["risk_tier"], result["burnout_probability"])
    render_tier_explanation(result["risk_tier"])
    render_shap_breakdown(result["shap"])
    render_resources(result["shap"], result["risk_tier"])

    st.divider()
    render_data_ownership(employee_id)
