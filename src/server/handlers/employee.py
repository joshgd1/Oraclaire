"""
Employee data API handlers.

GET    /api/employee/me          — own profile + consent status
PATCH  /api/employee/me          — update own consent/preferences
GET    /api/employee/me/scores    — own risk scores (latest cycle)
GET    /api/employee/me/shap     — own SHAP decomposition (latest score)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from src.model.entities import Employee, RiskScore, Role
from src.model.serve import get_resources_for_score
from src.model.entities._db import get_session_factory
from src.model.services.permission import (
    Action,
    PermissionDenied,
    PermissionService,
)


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
                emp.consent_timestamp = datetime.now(timezone.utc)
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
            target_employee_id=None,
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
            target_employee_id=None,
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
    return await _trend(request)


# Router — FastAPI APIRouter
from fastapi import APIRouter

router = APIRouter()
# Paths are relative to the include_router prefix in app.py
router.add_api_route("/me", get_me, methods=["GET"])
router.add_api_route("/me", update_me, methods=["PATCH"])
router.add_api_route("/me/scores", get_my_scores, methods=["GET"])
router.add_api_route("/me/shap", get_my_shap, methods=["GET"])
router.add_api_route("/{id}/pulse-trend", get_employee_pulse_trend, methods=["GET"])
