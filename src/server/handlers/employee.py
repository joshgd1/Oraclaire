"""
Employee data API handlers.

GET    /api/employee/me          — own profile + consent status
PATCH  /api/employee/me          — update own consent/preferences
GET    /api/employee/me/scores    — own risk scores (latest cycle)
GET    /api/employee/me/shap     — own SHAP decomposition (latest score)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.config import FEATURE_LABELS
from src.model.entities import AuditLog, Employee, RiskScore, Role
from src.model.entities._db import get_session_factory
from src.model.serve import get_resources_for_score
from src.model.services.permission import (
    Action,
    PermissionDenied,
    PermissionService,
)
from src.model.services.trajectory import TrajectoryClassificationService


def _role_from_user(user: Any) -> Role:
    if hasattr(user, "roles") and user.roles:
        role_map = {
            "system_admin": Role.SYSTEM_ADMIN,
            "hr_admin": Role.HR_ADMIN,
            "manager": Role.MANAGER,
            "employee": Role.EMPLOYEE,
        }
        return role_map.get(user.roles[0].lower(), Role.EMPLOYEE)
    return Role.EMPLOYEE


async def get_me(request: Request) -> JSONResponse:
    """GET /api/employee/me — return the authenticated employee's own record."""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    role = _role_from_user(user)
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(
            viewer_id=user.user_id,
            viewer_role=role,
            action=Action.READ_EMPLOYEE_DATA,
            target_employee_id=None,
        )
    except PermissionDenied as e:
        return JSONResponse({"error": str(e)}, status_code=403)

    factory = get_session_factory()
    session = factory()
    try:
        emp = session.query(Employee).filter(
            Employee.id == int(user.user_id)
        ).first()
        if not emp:
            return JSONResponse({"error": "employee not found"}, status_code=404)
        return JSONResponse({
            "id": emp.id,
            "consent_status": emp.consent_status.value,
            "consent_timestamp": (
                emp.consent_timestamp.isoformat() if emp.consent_timestamp else None
            ),
            "role": emp.role.value,
            "seniority_tier": emp.seniority_tier,
            "exclusion_status": emp.exclusion_status,
            "exclusion_category": (
                emp.exclusion_category.value if emp.exclusion_category else None
            ),
            "team_id": emp.team_id,
        })
    finally:
        session.close()


async def update_me(request: Request) -> JSONResponse:
    """PATCH /api/employee/me — update own consent/preferences."""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    role = _role_from_user(user)
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(
            viewer_id=user.user_id,
            viewer_role=role,
            action=Action.UPDATE_EMPLOYEE_DATA,
            target_employee_id=None,
        )
    except PermissionDenied as e:
        return JSONResponse({"error": str(e)}, status_code=403)

    body = await request.json()

    factory = get_session_factory()
    session = factory()
    try:
        emp = session.query(Employee).filter(
            Employee.id == int(user.user_id)
        ).first()
        if not emp:
            return JSONResponse({"error": "employee not found"}, status_code=404)

        # Only allow updating certain fields
        if "consent_status" in body:
            from src.model.entities import ConsentStatus
            try:
                emp.consent_status = ConsentStatus(body["consent_status"])
                emp.consent_timestamp = datetime.now(UTC)
            except ValueError:
                return JSONResponse(
                    {"error": f"invalid consent_status: {body['consent_status']}"},
                    status_code=400,
                )
        if "seniority_tier" in body:
            emp.seniority_tier = int(body["seniority_tier"])

        session.commit()
        return JSONResponse({"id": emp.id, "updated": True})
    finally:
        session.close()


async def get_my_scores(request: Request) -> JSONResponse:
    """GET /api/employee/me/scores — latest score for the authenticated employee."""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    role = _role_from_user(user)
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(
            viewer_id=user.user_id,
            viewer_role=role,
            action=Action.READ_OWN_SCORE,
            target_employee_id=int(user.user_id),
        )
    except PermissionDenied as e:
        return JSONResponse({"error": str(e)}, status_code=403)

    factory = get_session_factory()
    session = factory()
    try:
        score = session.query(RiskScore).filter(
            RiskScore.employee_id == int(user.user_id)
        ).order_by(RiskScore.scored_at.desc()).first()
        if not score:
            return JSONResponse({"scores": []})
        resources = get_resources_for_score(score.shap_values)
        return JSONResponse({
            "scores": [{
                "id": score.id,
                "cycle_id": score.cycle_id,
                "numeric_score": score.numeric_score,
                "risk_tier": score.risk_tier,
                "model_version": score.model_version,
                "scored_at": score.scored_at.isoformat(),
                "resources": resources,
            }]
        })
    finally:
        session.close()


async def get_my_shap(request: Request) -> JSONResponse:
    """GET /api/employee/me/shap — SHAP decomposition for the latest score."""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    role = _role_from_user(user)
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(
            viewer_id=user.user_id,
            viewer_role=role,
            action=Action.READ_OWN_SCORE,
            target_employee_id=int(user.user_id),
        )
    except PermissionDenied as e:
        return JSONResponse({"error": str(e)}, status_code=403)

    factory = get_session_factory()
    session = factory()
    try:
        score = session.query(RiskScore).filter(
            RiskScore.employee_id == int(user.user_id)
        ).order_by(RiskScore.scored_at.desc()).first()
        if not score:
            return JSONResponse({"shap_values": []})
        resources = get_resources_for_score(score.shap_values)
        return JSONResponse({
            "shap_values": score.shap_values,
            "seniority_tier_at_score": score.seniority_tier_at_score,
            "resources": resources,
        })
    finally:
        session.close()


# M4-06: GET /api/employee/{id}/pulse-trend — delegated to pulse.py
async def get_employee_pulse_trend(request: Request) -> JSONResponse:
    """GET /api/employee/{id}/pulse-trend — forward to pulse module."""
    from src.server.handlers.pulse import get_pulse_trend as _trend

    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    role = _role_from_user(user)
    path_params = request.path_params
    target_id = path_params.get("id") if path_params else None

    # M8-04: HRIS Export Guard — employees can only access their own pulse trend
    if role == Role.EMPLOYEE and target_id and str(target_id) != str(user.user_id):
        return JSONResponse(
            {
                "error": "BLOCKED_HRIS_EXPORT",
                "code": "BLOCKED_HRIS_EXPORT",
                "message": "Employees can only access their own pulse trend data.",
            },
            status_code=403,
        )

    # Managers cannot access individual employee trend data
    if role == Role.MANAGER:
        return JSONResponse(
            {
                "error": "BLOCKED_HRIS_EXPORT",
                "code": "BLOCKED_HRIS_EXPORT",
                "message": "Managers cannot access individual employee pulse trend data. Use team aggregate endpoints.",
            },
            status_code=403,
        )

    return await _trend(request)


async def get_my_explanation(request: Request) -> JSONResponse:
    """
    GET /api/employee/me/explanation — human-readable SHAP breakdown in plain language.

    Returns: {"employee_id", "score", "tier", "generated_at",
              "summary": "Your score was driven primarily by X...",
              "factors": [{"label": "...", "direction": "...", "impact_pct": N}]}
    Required for EU AI Act Art. 13 right-to-explanation.
    Audit log entry on every invocation (M1-11).
    """
    from src.config import FEATURE_LABELS as FL  # local to avoid top-level config load

    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    role = _role_from_user(user)
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(
            viewer_id=user.user_id,
            viewer_role=role,
            action=Action.READ_OWN_SCORE,
            target_employee_id=int(user.user_id),
        )
    except PermissionDenied as e:
        return JSONResponse({"error": str(e)}, status_code=403)

    factory = get_session_factory()
    session = factory()
    try:
        emp = session.query(Employee).filter(
            Employee.id == int(user.user_id)
        ).first()
        if not emp:
            return JSONResponse({"error": "employee not found"}, status_code=404)

        score = session.query(RiskScore).filter(
            RiskScore.employee_id == emp.id
        ).order_by(RiskScore.scored_at.desc()).first()
        if not score:
            return JSONResponse({"error": "no score available"}, status_code=404)

        # Audit log entry (M1-11 + M8-06)
        audit = AuditLog(
            actor_id=str(user.user_id),
            action="employee.explanation_requested",
            target_entity_type="risk_score",
            target_entity_id=str(score.id),
            timestamp=datetime.now(UTC),
            metadata_json={
                "employee_id": emp.id,
                "cycle_id": score.cycle_id,
            },
        )
        session.add(audit)
        session.commit()

        # Build human-readable explanation from SHAP values
        shap_list = score.shap_values or []
        if not shap_list:
            return JSONResponse({
                "employee_id": emp.id,
                "score": round(score.numeric_score, 4),
                "tier": score.risk_tier,
                "generated_at": datetime.now(UTC).isoformat(),
                "summary": (
                    "Your burnout risk score was calculated but detailed "
                    "factor information is not available for this assessment."
                ),
                "factors": [],
            })

        # Sort by absolute impact (shap_list is list[dict] with feature, impact_value keys)
        sorted_factors = sorted(
            shap_list,
            key=lambda x: abs(x.get("impact_value", 0)),
            reverse=True,
        )

        total_abs = sum(abs(x.get("impact_value", 0)) for x in shap_list) or 1.0
        factors = []
        for item in sorted_factors[:5]:
            feat = item.get("feature", "")
            raw_impact = item.get("impact_value", 0)
            label = FL.get(feat, feat.replace("_", " ").title())
            direction = "increases" if raw_impact > 0 else "decreases"
            impact_pct = round(abs(raw_impact) / total_abs * 100, 1)
            factors.append({
                "label": label,
                "feature": feat,
                "direction": direction,
                "impact_pct": impact_pct,
            })

        top = factors[0] if factors else None
        if top:
            summary = (
                f"Your burnout risk score was driven primarily by **{top['label']}**. "
                f"This factor {'increased' if top['direction'] == 'increases' else 'decreased'} your risk. "
                f"The top contributing factors were: "
                + ", ".join(f["label"] for f in factors[:3])
                + "."
            )
        else:
            summary = "Your burnout risk score was calculated across multiple factors."

        return JSONResponse({
            "employee_id": emp.id,
            "score": round(score.numeric_score, 4),
            "tier": score.risk_tier,
            "generated_at": datetime.now(UTC).isoformat(),
            "summary": summary,
            "factors": factors,
        })
    finally:
        session.close()


async def get_my_trajectory(request: Request) -> JSONResponse:
    """GET /api/employee/me/trajectory — trajectory classification for the authenticated employee."""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    role = _role_from_user(user)
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(
            viewer_id=user.user_id,
            viewer_role=role,
            action=Action.READ_OWN_SCORE,
            target_employee_id=int(user.user_id),
        )
    except PermissionDenied as e:
        return JSONResponse({"error": str(e)}, status_code=403)

    factory = get_session_factory()
    session = factory()
    try:
        emp = session.query(Employee).filter(
            Employee.id == int(user.user_id)
        ).first()
        if not emp:
            return JSONResponse({"error": "employee not found"}, status_code=404)

        result = TrajectoryClassificationService(session).classify(
            employee_id=emp.id,
            organisation_id=emp.organisation_id,
        )
        return JSONResponse({
            "employee_id": result.employee_id,
            "trajectory": result.trajectory,
            "current_score": result.current_score,
            "previous_score": result.previous_score,
            "delta": result.delta,
            "cycles_compared": result.cycles_compared,
            "threshold_used": result.threshold_used,
        })
    finally:
        session.close()


# Router — FastAPI APIRouter
router = APIRouter()
# Paths are relative to the include_router prefix in app.py
router.add_api_route("/me", get_me, methods=["GET"])
router.add_api_route("/me", update_me, methods=["PATCH"])
router.add_api_route("/me/scores", get_my_scores, methods=["GET"])
router.add_api_route("/me/shap", get_my_shap, methods=["GET"])
router.add_api_route("/me/trajectory", get_my_trajectory, methods=["GET"])
router.add_api_route("/me/explanation", get_my_explanation, methods=["GET"])
router.add_api_route("/{id}/pulse-trend", get_employee_pulse_trend, methods=["GET"])
