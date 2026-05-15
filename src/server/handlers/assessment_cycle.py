"""
Assessment cycle API handlers.

POST   /api/cycle              — create a new cycle (hr_admin, manager)
GET    /api/cycle              — list cycles (authenticated)
POST   /api/cycle/{id}/close   — close a cycle and trigger scoring (hr_admin, manager)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from src.model.entities import AssessmentCycle, CycleStatus, CycleType, Role
from src.model.entities._db import get_session_factory
from src.model.services.permission import Action, PermissionDenied, PermissionService
from src.audit.alerts import get_active_alerts


async def _trigger_scoring_on_close(cycle_id: int, organisation_id: int) -> None:
    """
    M2-05: Fire-and-forget scoring dispatch after a cycle closes.

    Reuses the async scoring pipeline from scoring.py. Scoring errors are
    logged by _run_scoring_async and do not roll back the cycle close.
    """
    from src.server.handlers.scoring import _run_scoring_async

    await _run_scoring_async(cycle_id, organisation_id)


def _require_role(user: Any) -> Role:
    """Infer Role from JWT claims or look up in DB."""
    # JWT payload may carry a 'role' claim set by the SSO/IdP provisioner
    if hasattr(user, "roles") and user.roles:
        # Use the first role; SYSTEM_ADMIN > HR_ADMIN > MANAGER > EMPLOYEE
        role_map = {"system_admin": Role.SYSTEM_ADMIN, "hr_admin": Role.HR_ADMIN,
                    "manager": Role.MANAGER, "employee": Role.EMPLOYEE}
        first = user.roles[0].lower()
        return role_map.get(first, Role.EMPLOYEE)
    return Role.EMPLOYEE


async def create_cycle(request: Request) -> JSONResponse:
    """POST /api/cycle — create a new assessment cycle."""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    body = await request.json()
    cycle_type_str = body.get("cycle_type", "pulse")
    try:
        cycle_type = CycleType(cycle_type_str)
    except ValueError:
        return JSONResponse({"error": f"invalid cycle_type: {cycle_type_str}"}, status_code=400)

    org_id = getattr(user, "tenant_id", None) or body.get("organisation_id")
    if not org_id:
        return JSONResponse({"error": "organisation_id required"}, status_code=400)

    role = _require_role(user)
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(viewer_id=user.user_id, viewer_role=role,
                   action=Action.MANAGE_CYCLE, target_org_id=org_id)
    except PermissionDenied as e:
        return JSONResponse({"error": str(e)}, status_code=403)

    # C3a: block new cycle creation if any active health alert exists
    active_alerts = get_active_alerts(organisation_id=org_id)
    if active_alerts:
        return JSONResponse({
            "error": "cannot create cycle while active health alerts exist",
            "code": "ACTIVE_ALERT_BLOCKS_CYCLE",
            "active_alerts": [
                {
                    "alert_id": a.alert_id,
                    "cycle_id": a.cycle_id,
                    "alert_type": a.alert_type,
                    "critical_fraction": a.critical_fraction,
                    "ceiling": a.ceiling,
                    "affected_count": a.affected_count,
                    "total_count": a.total_count,
                    "timestamp": a.timestamp,
                    "status": a.status.value,
                }
                for a in active_alerts
            ],
        }, status_code=409)

    factory = get_session_factory()
    session = factory()
    try:
        cycle = AssessmentCycle(
            organisation_id=org_id,
            cycle_type=cycle_type,
            started_at=datetime.now(timezone.utc),
            status=CycleStatus.OPEN,
        )
        session.add(cycle)
        session.commit()
        session.refresh(cycle)

        # M2-07: sync HRIS exclusions and apply to employee records (M1-10)
        exclusion_result = _sync_exclusions_on_cycle_start(org_id)

        return JSONResponse({
            "id": cycle.id,
            "cycle_type": cycle.cycle_type.value,
            "status": cycle.status.value,
            "started_at": cycle.started_at.isoformat(),
            "exclusion_sync": exclusion_result,
        }, status_code=201)
    finally:
        session.close()


def _sync_exclusions_on_cycle_start(organisation_id: int) -> dict:
    """
    M1-10 + M2-07 wiring: sync HRIS data and apply exclusion to employees.

    Called when a new cycle is opened.  Syncs from the configured HRIS
    adapter (upserts Exclusion records) then applies the resulting
    exclusion status to Employee rows so the scoring pipeline can filter
    scorable employees.
    """
    from src.hris.service import get_hris_adapter
    from src.model.services.exclusion import ExclusionEngine

    hris = get_hris_adapter()
    hris_result = hris.sync_exclusions(organisation_id)

    engine = ExclusionEngine.using(hris_available=hris.is_available())
    try:
        apply_result = engine.apply_to_employees(organisation_id=organisation_id)
    finally:
        engine.close()

    return {
        "hris_sync": hris_result,
        "employee_update": apply_result,
    }


async def list_cycles(request: Request) -> JSONResponse:
    """GET /api/cycle — list cycles for the caller's organisation."""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    org_id = getattr(user, "tenant_id", None)
    if not org_id:
        return JSONResponse({"error": "no tenant context"}, status_code=400)

    role = _require_role(user)
    svc = PermissionService(get_session_factory()())

    # Any authenticated role can list cycles for their org
    try:
        svc.check(viewer_id=user.user_id, viewer_role=role,
                   action=Action.READ_ORG_TRENDS, target_org_id=org_id)
    except PermissionDenied:
        # Fallback: employees can see open cycles for their org
        try:
            svc.check(viewer_id=user.user_id, viewer_role=role,
                       action=Action.READ_OWN_SCORE, target_org_id=org_id)
        except PermissionDenied:
            return JSONResponse({"error": "access denied"}, status_code=403)

    factory = get_session_factory()
    session = factory()
    try:
        cycles = session.query(AssessmentCycle).filter(
            AssessmentCycle.organisation_id == org_id
        ).order_by(AssessmentCycle.started_at.desc()).all()
        return JSONResponse({
            "cycles": [
                {"id": c.id, "cycle_type": c.cycle_type.value,
                 "status": c.status.value,
                 "started_at": c.started_at.isoformat(),
                 "closed_at": c.closed_at.isoformat() if c.closed_at else None}
                for c in cycles
            ]
        })
    finally:
        session.close()


async def close_cycle(request: Request) -> JSONResponse:
    """POST /api/cycle/{id}/close — close a cycle and trigger scoring."""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    # Extract cycle_id from path
    path_parts = request.url.path.strip("/").split("/")
    try:
        cycle_id = int(path_parts[-1])
    except (ValueError, IndexError):
        return JSONResponse({"error": "invalid cycle id"}, status_code=400)

    org_id = getattr(user, "tenant_id", None)
    role = _require_role(user)
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(viewer_id=user.user_id, viewer_role=role,
                   action=Action.MANAGE_CYCLE, target_org_id=org_id, target_team_id=None)
    except PermissionDenied as e:
        return JSONResponse({"error": str(e)}, status_code=403)

    factory = get_session_factory()
    session = factory()
    try:
        cycle = session.query(AssessmentCycle).filter(
            AssessmentCycle.id == cycle_id
        ).first()
        if not cycle:
            return JSONResponse({"error": "cycle not found"}, status_code=404)
        if cycle.status == CycleStatus.CLOSED:
            return JSONResponse({"error": "cycle already closed"}, status_code=409)

        cycle.status = CycleStatus.CLOSED
        cycle.closed_at = datetime.now(timezone.utc)
        session.commit()

        # M2-05: auto-trigger async scoring after cycle closes
        asyncio.create_task(_trigger_scoring_on_close(cycle.id, org_id))

        return JSONResponse({
            "id": cycle.id,
            "status": cycle.status.value,
            "closed_at": cycle.closed_at.isoformat(),
        })
    finally:
        session.close()


# Router — FastAPI APIRouter
from fastapi import APIRouter

router = APIRouter()
router.add_api_route("/", list_cycles, methods=["GET"])
router.add_api_route("/", create_cycle, methods=["POST"])
router.add_api_route("/{id}/close", close_cycle, methods=["POST"])
