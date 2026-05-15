"""
Organisational Risk Threshold API — per-team ORT status.

GET /api/org/risk-indicators — per-team ORT status for HR dashboard.

Returns for each team:
- id, name, member_count
- high_critical_pct: High+Critical rate in the latest closed cycle
- consecutive_weeks_elevated: consecutive weeks exceeding ORT_CEILING

Access: hr_admin (all teams), manager (own team only).
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse

from src.config import MIN_TEAM_SIZE, ORT_CEILING
from src.model.entities import AssessmentCycle, Employee, RiskScore, Team
from src.model.entities._db import get_session_factory
from src.model.services.deployment_parameter import DeploymentParameterService
from src.model.services.permission import Action, PermissionDenied, PermissionService
from src.server.handlers.hr_aggregate import _role_from_user


async def get_risk_indicators(request: Request) -> JSONResponse:
    """GET /api/org/risk-indicators — per-team ORT status."""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    org_id = getattr(user, "tenant_id", None)
    role = _role_from_user(user)
    perm_svc = PermissionService(get_session_factory()())

    # HR_ADMIN sees all teams; MANAGER sees own team
    try:
        perm_svc.check(
            viewer_id=user.user_id,
            viewer_role=role,
            action=Action.READ_ORG_TRENDS,
            target_org_id=org_id,
        )
    except PermissionDenied:
        try:
            perm_svc.check(
                viewer_id=user.user_id,
                viewer_role=role,
                action=Action.READ_TEAM_AGGREGATE,
                target_org_id=org_id,
            )
        except PermissionDenied as e:
            return JSONResponse({"error": str(e)}, status_code=403)

    factory = get_session_factory()
    session = factory()
    try:
        # Latest closed cycle
        latest_cycle = session.query(AssessmentCycle).filter(
            AssessmentCycle.organisation_id == org_id,
            AssessmentCycle.status == "closed",
        ).order_by(AssessmentCycle.closed_at.desc()).first()

        dp_svc = DeploymentParameterService(session)
        teams = session.query(Team).filter(Team.organisation_id == org_id).all()

        result = []
        for team in teams:
            if team.member_count < MIN_TEAM_SIZE:
                continue

            total = session.query(Employee).filter(
                Employee.team_id == team.id,
                Employee.organisation_id == org_id,
                Employee.consent_status != "withdrawn",
                Employee.exclusion_status == False,  # noqa: E712
            ).count()

            if total == 0:
                continue

            hc_count = session.query(RiskScore).join(
                Employee, RiskScore.employee_id == Employee.id
            ).filter(
                RiskScore.cycle_id == latest_cycle.id if latest_cycle else None,
                RiskScore.risk_tier.in_(("high", "critical")),
                Employee.team_id == team.id,
                Employee.organisation_id == org_id,
                Employee.consent_status != "withdrawn",
                Employee.exclusion_status == False,  # noqa: E712
            ).count()

            hc_pct = hc_count / total if total > 0 else 0.0

            # Read consecutive weeks counter from deployment parameters
            counter_key = f"ort_consecutive_{team.id}"
            consecutive = dp_svc.get_typed(org_id, counter_key) or 0

            result.append({
                "id": team.id,
                "name": team.name,
                "member_count": team.member_count,
                "high_critical_pct": round(hc_pct, 4),
                "consecutive_weeks_elevated": consecutive,
                "ort_ceiling": ORT_CEILING,
            })

        return JSONResponse({"teams": result})
    finally:
        session.close()


# Router
from fastapi import APIRouter

router = APIRouter()
router.add_api_route("/risk-indicators", get_risk_indicators, methods=["GET"])
