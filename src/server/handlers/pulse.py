"""
Pulse API handlers — M4-04, M4-06.

POST   /api/pulse/response               — submit a pulse response (single item)
GET    /api/employee/{id}/pulse-trend   — last N weekly pulse scores for trend chart
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.model.entities import AssessmentCycle, AssessmentResponse, Employee, CycleType, CycleStatus, Role
from src.model.entities._db import get_session_factory
from src.model.services.permission import Action, PermissionDenied, PermissionService

# Number of weeks of pulse history to return for the trend chart
PULSE_TREND_WEEKS = 12


def _require_role(user) -> Role:
    if hasattr(user, "roles") and user.roles:
        role_map = {"system_admin": Role.SYSTEM_ADMIN, "hr_admin": Role.HR_ADMIN,
                    "manager": Role.MANAGER, "employee": Role.EMPLOYEE}
        first = user.roles[0].lower()
        return role_map.get(first, Role.EMPLOYEE)
    return Role.EMPLOYEE


def _get_current_week_pulse_cycle(org_id: int, session) -> AssessmentCycle | None:
    """Find an open pulse cycle for the current week, or None."""
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=now.weekday(), hours=now.hour, minutes=now.minute)

    return session.query(AssessmentCycle).filter(
        AssessmentCycle.organisation_id == org_id,
        AssessmentCycle.cycle_type == CycleType.PULSE,
        AssessmentCycle.status == CycleStatus.OPEN,
        AssessmentCycle.started_at >= week_start,
    ).first()


def _get_or_create_pulse_cycle(org_id: int, session) -> AssessmentCycle:
    """Get the current week's open pulse cycle, creating one if absent."""
    cycle = _get_current_week_pulse_cycle(org_id, session)
    if cycle:
        return cycle

    now = datetime.now(timezone.utc)
    cycle = AssessmentCycle(
        organisation_id=org_id,
        cycle_type=CycleType.PULSE,
        started_at=now,
        status=CycleStatus.OPEN,
    )
    session.add(cycle)
    session.flush()  # get the id without committing
    return cycle


async def submit_pulse_response(request: Request) -> JSONResponse:
    """
    POST /api/pulse/response — submit the employee's pulse response for the
    current week.

    Body: {"response_value": float}  — single item, 0.0-6.0
    """
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    org_id = getattr(user, "tenant_id", None)
    if not org_id:
        return JSONResponse({"error": "no tenant context"}, status_code=400)

    employee_id = int(user.user_id)
    role = _require_role(user)

    svc = PermissionService(get_session_factory()())
    try:
        svc.check(viewer_id=user.user_id, viewer_role=role,
                   action=Action.SUBMIT_ASSESSMENT_RESPONSE,
                   target_employee_id=employee_id)
    except PermissionDenied as e:
        return JSONResponse({"error": str(e)}, status_code=403)

    body = await request.json()
    response_value = body.get("response_value")
    if not isinstance(response_value, (int, float)):
        return JSONResponse({"error": "response_value must be numeric"}, status_code=400)
    response_value = float(response_value)
    if response_value < 0.0 or response_value > 6.0:
        return JSONResponse(
            {"error": f"response_value must be in [0.0, 6.0], got {response_value}"},
            status_code=400,
        )

    factory = get_session_factory()
    session = factory()
    try:
        cycle = _get_or_create_pulse_cycle(org_id, session)

        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        # Upsert pulse response: item_index=0 always for pulse
        stmt = sqlite_insert(AssessmentResponse).values(
            cycle_id=cycle.id,
            employee_id=employee_id,
            item_index=0,
            response_value=response_value,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["cycle_id", "employee_id", "item_index"],
            set_={"response_value": response_value},
        )
        session.execute(stmt)

        # Also mark as submitted immediately (pulse is single-item, no partial state)
        from datetime import timezone
        existing = session.query(AssessmentResponse).filter(
            AssessmentResponse.cycle_id == cycle.id,
            AssessmentResponse.employee_id == employee_id,
            AssessmentResponse.item_index == 0,
        ).first()
        if existing and existing.submitted_at is None:
            existing.submitted_at = datetime.now(timezone.utc)

        session.commit()

        return JSONResponse({
            "cycle_id": cycle.id,
            "employee_id": employee_id,
            "item_index": 0,
            "response_value": response_value,
        })
    finally:
        session.close()


async def get_pulse_trend(request: Request) -> JSONResponse:
    """
    GET /api/employee/{id}/pulse-trend — return the caller's last N weekly
    pulse scores for the trend chart.

    Only the employee themselves (or HR/manager with permission) can read this.
    Each pulse cycle contributes one score: the employee's response_value for
    item_index 0, expressed as 0-100 scale.
    """
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    path_parts = request.url.path.strip("/").split("/")
    try:
        target_employee_id = int(path_parts[1])  # /api/employee/{id}/pulse-trend
    except (ValueError, IndexError):
        return JSONResponse({"error": "invalid employee id"}, status_code=400)

    org_id = getattr(user, "tenant_id", None)
    role = _require_role(user)

    # Access control: employee can only read their own pulse trend
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(viewer_id=user.user_id, viewer_role=role,
                   action=Action.READ_OWN_SCORE,
                   target_employee_id=target_employee_id)
    except PermissionDenied as e:
        return JSONResponse({"error": str(e)}, status_code=403)

    factory = get_session_factory()
    session = factory()
    try:
        # Get last N submitted pulse responses for this employee
        rows = (
            session.query(AssessmentResponse, AssessmentCycle)
            .join(AssessmentCycle, AssessmentResponse.cycle_id == AssessmentCycle.id)
            .filter(
                AssessmentResponse.employee_id == target_employee_id,
                AssessmentResponse.item_index == 0,
                AssessmentResponse.submitted_at.isnot(None),
                AssessmentCycle.cycle_type == CycleType.PULSE,
            )
            .order_by(AssessmentCycle.started_at.desc())
            .limit(PULSE_TREND_WEEKS)
            .all()
        )

        trend = []
        for resp, cycle in reversed(rows):  # oldest first for chart
            trend.append({
                "cycle_id": cycle.id,
                "week_start": cycle.started_at.isoformat(),
                "score": round(resp.response_value * (100.0 / 6.0), 1),
                "submitted_at": resp.submitted_at.isoformat() if resp.submitted_at else None,
            })

        return JSONResponse({
            "employee_id": target_employee_id,
            "weeks": PULSE_TREND_WEEKS,
            "trend": trend,
        })
    finally:
        session.close()


# Router
from fastapi import APIRouter

router = APIRouter()
router.add_api_route("/response", submit_pulse_response, methods=["POST"])
