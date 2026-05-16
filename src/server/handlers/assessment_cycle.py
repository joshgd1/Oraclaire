"""
Assessment cycle API handlers.

POST   /api/cycle              — create a new cycle (hr_admin, manager)
GET    /api/cycle              — list cycles (authenticated)
POST   /api/cycle/{id}/close   — close a cycle and trigger scoring (hr_admin, manager)
"""

from __future__ import annotations

import asyncio
import structlog
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.audit.alerts import get_active_alerts
from src.model.entities import AssessmentCycle, CycleStatus, CycleType, Role
from src.model.entities._db import get_session_factory
from src.model.services.permission import Action, PermissionDenied, PermissionService

logger = structlog.get_logger(__name__)


async def _trigger_scoring_on_close(cycle_id: int, organisation_id: int) -> None:
    """
    M2-05: Fire-and-forget scoring dispatch after a cycle closes.

    Reuses the async scoring pipeline from scoring.py. Scoring errors are
    logged by _run_scoring_async and do not roll back the cycle close.
    """
    from src.server.handlers.scoring import _run_scoring_async

    await _run_scoring_async(cycle_id, organisation_id)


def _trigger_retention_on_close(organisation_id: int) -> None:
    """
    M8-02: Fire-and-forget retention purge after a cycle closes.

    Checks whether any cycles have passed the retention threshold for this
    organisation and purges expired individual-level records.
    """
    import threading

    def _run():
        try:
            from src.model.services.retention import RetentionEngine
            result = RetentionEngine.for_organisation(organisation_id)
            logger.info("retention.cycle_close_trigger", organisation_id=organisation_id, result=result)
        except Exception:
            logger.exception("retention.cycle_close_failed", organisation_id=organisation_id)

    t = threading.Thread(target=_run, daemon=True)
    t.start()


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
            started_at=datetime.now(UTC),
            status=CycleStatus.OPEN,
        )
        session.add(cycle)
        session.commit()
        session.refresh(cycle)

        # M2-07: sync HRIS exclusions and apply to employee records (M1-10)
        exclusion_result = _sync_exclusions_on_cycle_start(org_id)

        # M4-10: notify eligible employees that a new cycle has opened
        try:
            notification_result = _notify_eligible_employees(
                cycle.id, org_id, cycle.cycle_type.value
            )
        except Exception:
            notification_result = {"error": "notification dispatch failed"}

        return JSONResponse({
            "id": cycle.id,
            "cycle_type": cycle.cycle_type.value,
            "status": cycle.status.value,
            "started_at": cycle.started_at.isoformat(),
            "exclusion_sync": exclusion_result,
            "notifications": notification_result,
        }, status_code=201)
    finally:
        session.close()


def _notify_eligible_employees(cycle_id: int, organisation_id: int, cycle_type: str) -> dict:
    """
    M4-10: Notify all eligible employees when a new cycle opens.

    Eligible: consented, not withdrawn, not excluded.
    Consent-aware: withdrawn employees are excluded.
    No score content in the notification.
    """
    from src.model.entities import ConsentStatus, Employee, Team
    from src.model.services.notification import notify_cycle_opened

    factory = get_session_factory()
    session = factory()
    try:
        eligible = (
            session.query(Employee.id)
            .join(Team, Employee.team_id == Team.id)
            .filter(
                Employee.organisation_id == organisation_id,
                Employee.consent_status == ConsentStatus.CONSENTED,
                Employee.exclusion_status == False,  # noqa: E712
                Team.member_count >= 5,
            )
            .all()
        )
        employee_ids = [e.id for e in eligible]
        if employee_ids:
            notify_cycle_opened(
                cycle_id=cycle_id,
                organisation_id=organisation_id,
                cycle_type=cycle_type,
                employee_ids=employee_ids,
            )
        return {"notified_count": len(employee_ids)}
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
        cycle.closed_at = datetime.now(UTC)
        session.commit()

        # M2-05: auto-trigger async scoring after cycle closes
        asyncio.create_task(_trigger_scoring_on_close(cycle.id, org_id))

        # M8-02: fire-and-forget retention purge after cycle closes
        _trigger_retention_on_close(org_id)

        return JSONResponse({
            "id": cycle.id,
            "status": cycle.status.value,
            "closed_at": cycle.closed_at.isoformat(),
        })
    finally:
        session.close()


async def submit_cycle_response(request: Request) -> JSONResponse:
    """
    POST /api/cycle/{id}/response — store one or more item responses for the
    authenticated employee on this cycle.

    Body: {
        "responses": [{"item_index": int, "response_value": float}, ...]
    }

    item_index: 0-18 for CBI (19 items), 0 for pulse (single item)
    response_value: float in [0.0, 6.0]

    Uses upsert: updates existing row if (cycle_id, employee_id, item_index)
    already exists (supports save-on-each-response for partial completion).
    """
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    path_parts = request.url.path.strip("/").split("/")
    try:
        cycle_id = int(path_parts[1])  # /api/cycle/{id}/response
    except (ValueError, IndexError):
        return JSONResponse({"error": "invalid cycle id"}, status_code=400)

    org_id = getattr(user, "tenant_id", None)
    employee_id = int(user.user_id)

    body = await request.json()
    responses = body.get("responses", [])
    if not isinstance(responses, list) or not responses:
        return JSONResponse({"error": "responses must be a non-empty list"}, status_code=400)

    role = _require_role(user)
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(viewer_id=user.user_id, viewer_role=role,
                   action=Action.SUBMIT_ASSESSMENT_RESPONSE,
                   target_employee_id=employee_id)
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
        if cycle.status != CycleStatus.OPEN:
            return JSONResponse({"error": "cycle is not open"}, status_code=409)
        if cycle.organisation_id != org_id:
            return JSONResponse({"error": "cycle not in your organisation"}, status_code=403)

        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        from src.model.entities import AssessmentResponse

        stored = 0
        for item in responses:
            if not isinstance(item, dict):
                return JSONResponse({"error": "each response must be an object"}, status_code=400)
            item_index = item.get("item_index")
            response_value = item.get("response_value")
            if not isinstance(item_index, int) or not isinstance(response_value, (int, float)):
                return JSONResponse({"error": "item_index must be int, response_value must be numeric"}, status_code=400)
            if response_value < 0.0 or response_value > 6.0:
                return JSONResponse(
                    {"error": f"response_value must be in [0.0, 6.0], got {response_value}"},
                    status_code=400,
                )

            # Upsert: update if exists, insert if not
            stmt = sqlite_insert(AssessmentResponse).values(
                cycle_id=cycle_id,
                employee_id=employee_id,
                item_index=item_index,
                response_value=float(response_value),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["cycle_id", "employee_id", "item_index"],
                set_={"response_value": float(response_value)},
            )
            session.execute(stmt)
            stored += 1

        session.commit()

        return JSONResponse({
            "cycle_id": cycle_id,
            "employee_id": employee_id,
            "items_stored": stored,
        })
    finally:
        session.close()


async def submit_cycle(request: Request) -> JSONResponse:
    """
    POST /api/cycle/{id}/submit — mark all responses for this employee on
    this cycle as submitted. Called when the employee completes their assessment.

    Triggers participation tracking update.
    """
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    path_parts = request.url.path.strip("/").split("/")
    try:
        cycle_id = int(path_parts[1])  # /api/cycle/{id}/submit
    except (ValueError, IndexError):
        return JSONResponse({"error": "invalid cycle id"}, status_code=400)

    org_id = getattr(user, "tenant_id", None)
    employee_id = int(user.user_id)

    role = _require_role(user)
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(viewer_id=user.user_id, viewer_role=role,
                   action=Action.SUBMIT_ASSESSMENT_RESPONSE,
                   target_employee_id=employee_id)
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
        if cycle.status != CycleStatus.OPEN:
            return JSONResponse({"error": "cycle is not open"}, status_code=409)
        if cycle.organisation_id != org_id:
            return JSONResponse({"error": "cycle not in your organisation"}, status_code=403)


        from src.model.entities import AssessmentResponse

        # Mark all unsubmitted responses for this employee/cycle as submitted
        updated = session.query(AssessmentResponse).filter(
            AssessmentResponse.cycle_id == cycle_id,
            AssessmentResponse.employee_id == employee_id,
            AssessmentResponse.submitted_at.is_(None),
        ).update(
            {"submitted_at": datetime.now(UTC)},
            synchronize_session=False,
        )
        session.commit()

        # M4-07: update participation tracking (fire-and-forget)
        asyncio.create_task(_update_participation(cycle_id, org_id))

        return JSONResponse({
            "cycle_id": cycle_id,
            "employee_id": employee_id,
            "responses_submitted": updated,
        })
    finally:
        session.close()


async def _update_participation(cycle_id: int, organisation_id: int) -> None:
    """M4-07: Update participation tracking after a response submission."""
    try:
        from src.model.services.participation import update_participation_for_cycle
        update_participation_for_cycle(cycle_id, organisation_id)
    except Exception:
        # Fire-and-forget: participation tracking errors do not block the submit
        import structlog
        log = structlog.get_logger()
        log.warning("participation_update_failed", cycle_id=cycle_id)


async def send_midpoint_reminder(request: Request) -> JSONResponse:
    """
    POST /api/cycle/{id}/remind — send midpoint reminder to non-respondents.

    M4-10: HR admin can trigger this manually, or a scheduled job calls it
    at the cycle midpoint (~3.5 days into a 7-day cycle).
    Only employees who have not submitted a response are notified.
    """
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    path_parts = request.url.path.strip("/").split("/")
    try:
        cycle_id = int(path_parts[1])
    except (ValueError, IndexError):
        return JSONResponse({"error": "invalid cycle id"}, status_code=400)

    org_id = getattr(user, "tenant_id", None)
    role = _require_role(user)
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(viewer_id=user.user_id, viewer_role=role,
                   action=Action.MANAGE_CYCLE, target_org_id=org_id)
    except PermissionDenied as e:
        return JSONResponse({"error": str(e)}, status_code=403)

    factory = get_session_factory()
    session = factory()
    try:
        cycle = session.query(AssessmentCycle).filter(
            AssessmentCycle.id == cycle_id,
            AssessmentCycle.organisation_id == org_id,
        ).first()
        if not cycle:
            return JSONResponse({"error": "cycle not found"}, status_code=404)
        if cycle.status != CycleStatus.OPEN:
            return JSONResponse({"error": "cycle is not open"}, status_code=409)
    finally:
        session.close()

    # Identify non-respondents
    try:
        result = _send_midpoint_reminder(cycle_id, org_id, cycle.cycle_type.value)
        return JSONResponse(result)
    except Exception as exc:
        import structlog
        structlog.get_logger().error("midpoint_reminder.failed", cycle_id=cycle_id, error=str(exc))
        return JSONResponse({"error": "reminder dispatch failed"}, status_code=500)


def _send_midpoint_reminder(cycle_id: int, organisation_id: int, cycle_type: str) -> dict:
    """
    M4-10: Send midpoint reminders to employees who haven't responded.

    Called by the reminder endpoint handler. Identifies eligible non-respondents
    and sends notifications.
    """
    from src.model.entities import AssessmentResponse, ConsentStatus, Employee, Team
    from src.model.services.notification import notify_midpoint_reminder

    factory = get_session_factory()
    session = factory()
    try:
        # Eligible employees: consented, not excluded, in sufficiently-sized team
        eligible = (
            session.query(Employee.id)
            .join(Team, Employee.team_id == Team.id)
            .filter(
                Employee.organisation_id == organisation_id,
                Employee.consent_status == ConsentStatus.CONSENTED,
                Employee.exclusion_status == False,  # noqa: E712
                Team.member_count >= 5,
            )
            .all()
        )
        eligible_ids = {e.id for e in eligible}

        # Employees who have submitted at least one response
        responded = (
            session.query(AssessmentResponse.employee_id)
            .filter(
                AssessmentResponse.cycle_id == cycle_id,
                AssessmentResponse.submitted_at.isnot(None),
            )
            .distinct()
            .all()
        )
        responded_ids = {r[0] for r in responded}

        # Non-respondents: eligible but haven't submitted
        non_respondent_ids = list(eligible_ids - responded_ids)

        if non_respondent_ids:
            notify_midpoint_reminder(
                cycle_id=cycle_id,
                organisation_id=organisation_id,
                cycle_type=cycle_type,
                employee_ids=non_respondent_ids,
                cycle_started_at=datetime.now(UTC),
            )

        return {"reminder_sent_count": len(non_respondent_ids)}
    finally:
        session.close()


# Router — FastAPI APIRouter
router = APIRouter()
router.add_api_route("/", list_cycles, methods=["GET"])
router.add_api_route("/", create_cycle, methods=["POST"])
router.add_api_route("/{id}/close", close_cycle, methods=["POST"])
router.add_api_route("/{id}/response", submit_cycle_response, methods=["POST"])
router.add_api_route("/{id}/submit", submit_cycle, methods=["POST"])
router.add_api_route("/{id}/remind", send_midpoint_reminder, methods=["POST"])
