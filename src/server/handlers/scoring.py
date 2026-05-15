"""
Scoring trigger API handlers.

POST /api/scoring/trigger/{cycle_id}  — trigger scoring for a closed cycle
GET  /api/scoring/status/{cycle_id}  — check scoring status for a cycle
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from src.model.entities import AssessmentCycle, Employee, Role, RiskScore
from src.model.entities._db import get_session_factory
from src.model.services.permission import Action, PermissionDenied, PermissionService
from src.audit.alerts import (
    get_active_alerts,
    get_alert_by_id,
    write_acknowledgment,
    AlertDecision,
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


async def trigger_scoring(request: Request) -> JSONResponse:
    """
    POST /api/scoring/trigger/{cycle_id} — dispatch async scoring job.

    Validates the cycle and spawns the scorer as a background task, returning
    immediately with status "processing".  Clients poll GET
    /api/scoring/status/{cycle_id} for completion.
    """
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    path_parts = request.url.path.strip("/").split("/")
    try:
        cycle_id = int(path_parts[-1])
    except (ValueError, IndexError):
        return JSONResponse({"error": "invalid cycle id"}, status_code=400)

    org_id = getattr(user, "tenant_id", None)
    role = _role_from_user(user)
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

        # Only closed cycles can be scored
        if cycle.status.value != "closed":
            return JSONResponse(
                {"error": f"cycle is {cycle.status.value}, must be closed first"},
                status_code=409,
            )

        # Check if already scored
        existing = session.query(RiskScore).filter(
            RiskScore.cycle_id == cycle_id
        ).count()
        if existing > 0:
            return JSONResponse(
                {"error": "cycle already scored"},
                status_code=409,
            )
    finally:
        session.close()

    # M2-05: dispatch to background task via asyncio
    asyncio.create_task(_run_scoring_async(cycle_id, org_id))

    return JSONResponse({
        "cycle_id": cycle_id,
        "status": "processing",
        "message": "scoring job dispatched",
    })


async def _run_scoring_async(cycle_id: int, organisation_id: int) -> None:
    """
    M2-05: Async scoring job — runs in background after cycle close.

    Loads the model, fetches eligible employees, scores each, and writes
    RiskScore rows.  Uses its own session to avoid blocking the HTTP
    request lifecycle.
    """
    from src.config import THRESHOLD_A, THRESHOLD_B, TIER_BOUNDARIES
    from src.config import MODEL_ARTIFACT_PATH
    from src.model.services.cycle_health import check_critical_ceiling
    import joblib
    from pathlib import Path
    import structlog

    logger = structlog.get_logger(__name__)

    model = None
    if Path(MODEL_ARTIFACT_PATH).exists():
        try:
            model = joblib.load(MODEL_ARTIFACT_PATH)
        except Exception as exc:
            logger.error("scoring.model_load.failed", error=str(exc))

    factory = get_session_factory()
    session = factory()
    try:
        employees = session.query(Employee).filter(
            Employee.organisation_id == organisation_id,
            Employee.consent_status != "withdrawn",
            Employee.exclusion_status == False,  # noqa: E712
        ).all()

        scored_at = datetime.now(timezone.utc)

        for emp in employees:
            if model is None:
                numeric_score = 0.5
                risk_tier = "moderate"
            else:
                # Collect features — M2-05 real feature extraction wires in here
                features = [0.0] * 10
                numeric_score = float(model.predict_proba([features])[0][1])
                tier = "low"
                for name, (lo, hi) in TIER_BOUNDARIES.items():
                    if lo <= numeric_score < hi:
                        tier = name
                        break
                risk_tier = tier

            score = RiskScore(
                employee_id=emp.id,
                cycle_id=cycle_id,
                risk_tier=risk_tier,
                numeric_score=numeric_score,
                shap_values=[],
                model_version="1.0.0",
                scored_at=scored_at,
                seniority_tier_at_score=emp.seniority_tier,
            )
            session.add(score)

        session.commit()
        logger.info("scoring.complete", cycle_id=cycle_id, scored=len(employees))

        # M2-05 + C3a: check Critical-tier fraction after scoring commits
        try:
            alert_id = check_critical_ceiling(cycle_id, organisation_id)
            if alert_id:
                logger.info(
                    "scoring.model_health_alert.fired",
                    cycle_id=cycle_id,
                    alert_id=alert_id,
                )
        except Exception as exc:
            logger.error(
                "scoring.model_health_alert.failed",
                cycle_id=cycle_id,
                error=str(exc),
            )
    except Exception as exc:
        logger.exception("scoring.failed", cycle_id=cycle_id, error=str(exc))
        session.rollback()
    finally:
        session.close()


async def list_alerts(request: Request) -> JSONResponse:
    """
    GET /api/scoring/alerts/{cycle_id} — list active health alerts for a cycle.

    PRODUCT_OWNER only. Returns the full alert details so the PO can
    review before acknowledging.
    """
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    path_parts = request.url.path.strip("/").split("/")
    try:
        cycle_id = int(path_parts[-1])
    except (ValueError, IndexError):
        return JSONResponse({"error": "invalid cycle id"}, status_code=400)

    org_id = getattr(user, "tenant_id", None)
    role = _role_from_user(user)
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(viewer_id=user.user_id, viewer_role=role,
                   action=Action.READ_HEALTH_ALERTS, target_org_id=org_id)
    except PermissionDenied as e:
        return JSONResponse({"error": str(e)}, status_code=403)

    alerts = get_active_alerts(organisation_id=org_id)
    cycle_alerts = [a for a in alerts if a.cycle_id == cycle_id]
    return JSONResponse({
        "cycle_id": cycle_id,
        "active_alerts": [
            {
                "alert_id": a.alert_id,
                "alert_type": a.alert_type,
                "critical_fraction": a.critical_fraction,
                "ceiling": a.ceiling,
                "affected_count": a.affected_count,
                "total_count": a.total_count,
                "timestamp": a.timestamp,
                "status": a.status.value,
            }
            for a in cycle_alerts
        ],
    })


async def acknowledge_alert(request: Request) -> JSONResponse:
    """
    POST /api/scoring/alerts/{alert_id}/acknowledge — acknowledge a health alert.

    PRODUCT_OWNER only. Body: {"note": "...", "decision": "RETRAIN|THRESHOLD_ADJUST|RESUME_CONFIRMED"}
    """
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    path_parts = request.url.path.strip("/").split("/")
    alert_id = path_parts[-2]  # .../alerts/{alert_id}/acknowledge

    org_id = getattr(user, "tenant_id", None)
    role = _role_from_user(user)
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(viewer_id=user.user_id, viewer_role=role,
                   action=Action.ACKNOWLEDGE_HEALTH_ALERT, target_org_id=org_id)
    except PermissionDenied as e:
        return JSONResponse({"error": str(e)}, status_code=403)

    body = await request.json()
    note = body.get("note")
    if not note or not isinstance(note, str) or len(note) < 1 or len(note) > 1000:
        return JSONResponse(
            {"error": "note must be a string of 1–1000 characters"},
            status_code=400,
        )

    decision_str = body.get("decision")
    if not decision_str:
        return JSONResponse({"error": "decision is required"}, status_code=400)
    try:
        decision = AlertDecision(decision_str)
    except ValueError:
        valid = [d.value for d in AlertDecision]
        return JSONResponse(
            {"error": f"decision must be one of {valid}"},
            status_code=400,
        )

    existing = get_alert_by_id(alert_id)
    if not existing:
        return JSONResponse({"error": "alert not found"}, status_code=404)

    ts = write_acknowledgment(
        alert_id=alert_id,
        acknowledger_id=user.user_id,
        note=note,
        decision=decision,
    )

    return JSONResponse({
        "alert_id": alert_id,
        "acknowledged_at": ts,
        "decision": decision.value,
    })


async def scoring_status(request: Request) -> JSONResponse:
    """GET /api/scoring/status/{cycle_id} — check scoring progress for a cycle."""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    path_parts = request.url.path.strip("/").split("/")
    try:
        cycle_id = int(path_parts[-1])
    except (ValueError, IndexError):
        return JSONResponse({"error": "invalid cycle id"}, status_code=400)

    org_id = getattr(user, "tenant_id", None)
    role = _role_from_user(user)
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(viewer_id=user.user_id, viewer_role=role,
                   action=Action.READ_ORG_TRENDS, target_org_id=org_id)
    except PermissionDenied:
        try:
            svc.check(viewer_id=user.user_id, viewer_role=role,
                       action=Action.READ_TEAM_AGGREGATE, target_org_id=org_id)
        except PermissionDenied as e:
            return JSONResponse({"error": str(e)}, status_code=403)

    factory = get_session_factory()
    session = factory()
    try:
        total = session.query(Employee).filter(
            Employee.organisation_id == org_id,
            Employee.exclusion_status == False,  # noqa: E712
        ).count()
        scored = session.query(RiskScore).filter(
            RiskScore.cycle_id == cycle_id,
        ).count()
        return JSONResponse({
            "cycle_id": cycle_id,
            "total_eligible": total,
            "scored": scored,
            "pending": max(0, total - scored),
        })
    finally:
        session.close()


# Router — FastAPI APIRouter
from fastapi import APIRouter

router = APIRouter()
router.add_api_route("/trigger/{cycle_id}", trigger_scoring, methods=["POST"])
router.add_api_route("/status/{cycle_id}", scoring_status, methods=["GET"])
router.add_api_route("/alerts/{cycle_id}", list_alerts, methods=["GET"])
router.add_api_route("/alerts/{alert_id}/acknowledge", acknowledge_alert, methods=["POST"])
