"""
HR aggregate API handlers.

GET /api/hr/trends          — org-wide risk distribution (hr_admin)
GET /api/hr/exclusions      — exclusion counts by category (hr_admin)
GET /api/hr/teams           — team-level aggregates (hr_admin, manager with team)
GET /api/hr/participation   — participation rates by cycle (hr_admin)

M6-08: Employee-first 24h visibility gate — risk distribution and team-level
scores are withheld from HR until 24h after cycle close, giving employees
the first window to view their own scores.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.config import MIN_TEAM_SIZE
from src.model.entities import (
    AssessmentCycle,
    AssessmentResponse,
    CycleStatus,
    Employee,
    RiskScore,
    Role,
    Team,
)
from src.model.entities._db import get_session_factory
from src.model.services.deployment_parameter import DeploymentParameterService
from src.model.services.permission import (
    Action,
    PermissionDenied,
    PermissionService,
)

# M6-08: employee-first visibility window
_GATE_HOURS = 24


def _is_gate_active(cycle) -> bool:
    """Return True if the cycle is still within the 24h employee-first window."""
    if cycle.closed_at is None:
        return True
    now = datetime.now(UTC)
    closed_at = cycle.closed_at
    # Normalise to UTC-aware: if naive, assume UTC; if already aware, convert
    if closed_at.tzinfo is None:
        closed_utc = closed_at.replace(tzinfo=UTC)
    else:
        closed_utc = closed_at.astimezone(UTC)
    gate_end = closed_utc + timedelta(hours=_GATE_HOURS)
    return now < gate_end


def _gate_response_fields(cycle):
    """Return visibility metadata for a cycle."""
    closed = cycle.closed_at
    if closed is None:
        return {"visibility_locked": True, "visibility_locked_until": None}
    if closed.tzinfo is None:
        closed_utc = closed.replace(tzinfo=UTC)
    else:
        closed_utc = closed.astimezone(UTC)
    locked_until = closed_utc + timedelta(hours=_GATE_HOURS)
    return {
        "visibility_locked": _is_gate_active(cycle),
        "visibility_locked_until": locked_until.isoformat(),
    }


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


async def get_trends(request: Request) -> JSONResponse:
    """GET /api/hr/trends — org-wide risk tier distribution."""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    org_id = getattr(user, "tenant_id", None)
    role = _role_from_user(user)
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(viewer_id=user.user_id, viewer_role=role,
                   action=Action.READ_ORG_TRENDS, target_org_id=org_id)
    except PermissionDenied as e:
        return JSONResponse({"error": str(e)}, status_code=403)

    factory = get_session_factory()
    session = factory()
    try:
        # Latest closed cycle
        latest_cycle = session.query(AssessmentCycle).filter(
            AssessmentCycle.organisation_id == org_id,
            AssessmentCycle.status == CycleStatus.CLOSED,
        ).order_by(AssessmentCycle.closed_at.desc()).first()

        if not latest_cycle:
            return JSONResponse({"trends": [], "cycle_id": None, "visibility_locked": False})

        # M6-08: 24h employee-first gate — withhold risk distribution from HR
        gate_fields = _gate_response_fields(latest_cycle)
        if gate_fields["visibility_locked"]:
            return JSONResponse({
                "cycle_id": latest_cycle.id,
                "total_scored": 0,
                "tiers": {"low": 0, "moderate": 0, "high": 0, "critical": 0},
                **gate_fields,
            })

        scores = session.query(RiskScore).filter(
            RiskScore.cycle_id == latest_cycle.id
        ).all()

        tiers = {"low": 0, "moderate": 0, "high": 0, "critical": 0}
        for s in scores:
            tiers[s.risk_tier] = tiers.get(s.risk_tier, 0) + 1

        return JSONResponse({
            "cycle_id": latest_cycle.id,
            "total_scored": len(scores),
            "tiers": tiers,
            **gate_fields,
        })
    finally:
        session.close()


async def get_exclusions(request: Request) -> JSONResponse:
    """GET /api/hr/exclusions — exclusion counts by category."""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    org_id = getattr(user, "tenant_id", None)
    role = _role_from_user(user)
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(viewer_id=user.user_id, viewer_role=role,
                   action=Action.READ_EXCLUSION_COUNTS, target_org_id=org_id)
    except PermissionDenied as e:
        return JSONResponse({"error": str(e)}, status_code=403)

    factory = get_session_factory()
    session = factory()
    try:
        excluded = session.query(Employee).filter(
            Employee.organisation_id == org_id,
            Employee.exclusion_status == True,  # noqa: E712
        ).all()

        by_category: dict[str, int] = {}
        for emp in excluded:
            cat = emp.exclusion_category.value if emp.exclusion_category else "unknown"
            by_category[cat] = by_category.get(cat, 0) + 1

        return JSONResponse({
            "total": len(excluded),
            "by_category": by_category,
        })
    finally:
        session.close()


async def get_teams(request: Request) -> JSONResponse:
    """GET /api/hr/teams — team-level aggregates (gated 24h post-cycle-close)."""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    org_id = getattr(user, "tenant_id", None)
    role = _role_from_user(user)
    svc = PermissionService(get_session_factory()())

    # HR_ADMIN sees all teams; MANAGER sees only their team
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
        # Latest closed cycle for gate check
        latest_cycle = session.query(AssessmentCycle).filter(
            AssessmentCycle.organisation_id == org_id,
            AssessmentCycle.status == CycleStatus.CLOSED,
        ).order_by(AssessmentCycle.closed_at.desc()).first()

        gate_fields = _gate_response_fields(latest_cycle) if latest_cycle else {
            "visibility_locked": True, "visibility_locked_until": None}

        dp_svc = DeploymentParameterService(session)
        teams = session.query(Team).filter(Team.organisation_id == org_id).all()
        result = []
        for team in teams:
            if team.member_count < MIN_TEAM_SIZE:
                continue
            entry = {
                "id": team.id,
                "name": team.name,
                "member_count": team.member_count,
            }
            # M6-08: ORT data withheld until 24h employee-first window passes
            if not gate_fields["visibility_locked"]:
                hc_count = session.query(RiskScore).join(
                    Employee, RiskScore.employee_id == Employee.id
                ).filter(
                    RiskScore.cycle_id == latest_cycle.id,
                    RiskScore.risk_tier.in_(("high", "critical")),
                    Employee.team_id == team.id,
                    Employee.organisation_id == org_id,
                    Employee.consent_status != "withdrawn",
                    Employee.exclusion_status == False,  # noqa: E712
                ).count()
                total = session.query(Employee).filter(
                    Employee.team_id == team.id,
                    Employee.organisation_id == org_id,
                    Employee.consent_status != "withdrawn",
                    Employee.exclusion_status == False,  # noqa: E712
                ).count()
                hc_pct = round(hc_count / total, 4) if total > 0 else 0.0
                entry["high_critical_pct"] = hc_pct
                entry["consecutive_weeks_elevated"] = (
                    dp_svc.get_typed(org_id, f"ort_consecutive_{team.id}") or 0
                )
            result.append(entry)

        return JSONResponse({"teams": result, **gate_fields})
    finally:
        session.close()


async def get_participation(request: Request) -> JSONResponse:
    """GET /api/hr/participation — participation rates per cycle."""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    org_id = getattr(user, "tenant_id", None)
    role = _role_from_user(user)
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(viewer_id=user.user_id, viewer_role=role,
                   action=Action.READ_ORG_TRENDS, target_org_id=org_id)
    except PermissionDenied as e:
        return JSONResponse({"error": str(e)}, status_code=403)

    factory = get_session_factory()
    session = factory()
    try:
        cycles = session.query(AssessmentCycle).filter(
            AssessmentCycle.organisation_id == org_id,
        ).order_by(AssessmentCycle.started_at.desc()).limit(12).all()

        total_employees = session.query(Employee).filter(
            Employee.organisation_id == org_id,
            Employee.exclusion_status == False,  # noqa: E712
        ).count()

        result = []
        for cycle in cycles:
            responded = session.query(AssessmentResponse).filter(
                AssessmentResponse.cycle_id == cycle.id,
            ).count()
            result.append({
                "cycle_id": cycle.id,
                "cycle_type": cycle.cycle_type.value,
                "status": cycle.status.value,
                "total_eligible": total_employees,
                "responded": responded,
                "participation_pct": (
                    round(responded / total_employees * 100, 1)
                    if total_employees > 0 else 0
                ),
            })
        return JSONResponse({"cycles": result})
    finally:
        session.close()


# Router — FastAPI APIRouter
router = APIRouter()
router.add_api_route("/trends", get_trends, methods=["GET"])
router.add_api_route("/exclusions", get_exclusions, methods=["GET"])
router.add_api_route("/teams", get_teams, methods=["GET"])
router.add_api_route("/participation", get_participation, methods=["GET"])
