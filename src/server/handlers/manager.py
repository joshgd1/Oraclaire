"""
Manager-facing team dashboard API.

GET /api/team/{id}/aggregate  — team-level tier distribution and trend
GET /api/team/{id}/recommendations — team SHAP factors + matched action resources

Access: manager (own team only), hr_admin (all teams).
"""

from __future__ import annotations

from collections import Counter
from statistics import mean

from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.config import MIN_TEAM_SIZE, ORT_CEILING
from src.model.entities import AssessmentCycle, CycleStatus, Employee, RiskScore, Team
from src.model.entities._db import get_session_factory
from src.model.serve import get_resources_for_score
from src.server.handlers.hr_aggregate import _role_from_user
from src.model.services.permission import Action, PermissionDenied, PermissionService
from src.model.services.trajectory import TrajectoryClassificationService


def _check_team_access(request: Request, team_id: int) -> tuple | None:
    """Check request has access to team team_id. Returns (user, role, org_id) or None on deny."""
    user = getattr(request.state, "user", None)
    if not user:
        return None
    org_id = getattr(user, "tenant_id", None)
    role = _role_from_user(user)
    perm_svc = PermissionService(get_session_factory()())

    # HR_ADMIN bypasses team check
    if role.value == "hr_admin":
        return (user, role, org_id)

    # MANAGER: must own the team
    if role.value == "manager":
        factory = get_session_factory()
        session = factory()
        try:
            emp = session.query(Employee).filter(
                Employee.id == int(user.user_id)
            ).first()
            if not emp or emp.team_id != team_id:
                return None
        finally:
            session.close()
        try:
            perm_svc.check(
                viewer_id=user.user_id,
                viewer_role=role,
                action=Action.READ_TEAM_AGGREGATE,
                target_team_id=team_id,
                target_org_id=org_id,
            )
        except PermissionDenied:
            return None
        return (user, role, org_id)

    return None


async def get_my_team(request: Request) -> JSONResponse:
    """GET /api/manager/me — the authenticated manager's own team info."""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    role = _role_from_user(user)
    if role.value != "manager":
        return JSONResponse(
            {"error": "not a manager"}, status_code=403,
        )

    factory = get_session_factory()
    session = factory()
    try:
        emp = session.query(Employee).filter(
            Employee.id == int(user.user_id)
        ).first()
        if not emp or not emp.team_id:
            return JSONResponse(
                {"error": "manager has no assigned team"}, status_code=404,
            )

        team = session.query(Team).filter(Team.id == emp.team_id).first()
        if not team:
            return JSONResponse(
                {"error": "team not found"}, status_code=404,
            )

        return JSONResponse({
            "team_id": team.id,
            "team_name": team.name,
            "team_size": team.member_count,
        })
    finally:
        session.close()


async def get_team_aggregate(request: Request, team_id: int) -> JSONResponse:
    """GET /api/team/{id}/aggregate — tier distribution and trend for one team."""
    access = _check_team_access(request, team_id)
    if not access:
        return JSONResponse({"error": "access denied"}, status_code=403)

    user, role, org_id = access
    factory = get_session_factory()
    session = factory()
    try:
        team = session.query(Team).filter(
            Team.id == team_id,
            Team.organisation_id == org_id,
        ).first()
        if not team:
            return JSONResponse({"error": "team not found"}, status_code=404)

        # Suppressed if team below minimum size
        suppressed = team.member_count < MIN_TEAM_SIZE
        if suppressed:
            return JSONResponse({
                "team_id": team.id,
                "team_name": team.name,
                "team_size": team.member_count,
                "suppressed": True,
                "suppression_reason": f"Team has {team.member_count} members (minimum {MIN_TEAM_SIZE})",
                "cycles": [],
                "tier_distribution": {},
            })

        # Get last 12 closed cycles for trend
        cycles = session.query(AssessmentCycle).filter(
            AssessmentCycle.organisation_id == org_id,
            AssessmentCycle.status == CycleStatus.CLOSED,
        ).order_by(AssessmentCycle.closed_at.desc()).limit(12).all()

        # 24h visibility gate: check latest cycle
        latest_cycle = cycles[0] if cycles else None
        from src.server.handlers.hr_aggregate import _is_gate_active
        gate_active = _is_gate_active(latest_cycle) if latest_cycle else True

        cycle_summaries = []
        tier_overall = Counter()

        for cycle in reversed(cycles):  # oldest first for trend display
            eligible = session.query(Employee).filter(
                Employee.team_id == team_id,
                Employee.organisation_id == org_id,
                Employee.consent_status.name != "withdrawn",
                Employee.exclusion_status == False,  # noqa: E702
            ).count()

            if eligible == 0:
                continue

            scores_in_cycle = session.query(RiskScore).filter(
                RiskScore.cycle_id == cycle.id,
                RiskScore.employee_id.in_(
                    session.query(Employee.id).filter(
                        Employee.team_id == team_id,
                        Employee.organisation_id == org_id,
                    )
                ),
            ).all()

            tiers = Counter(s.risk_tier for s in scores_in_cycle)
            tier_overall += tiers

            pct = lambda t: round(tiers.get(t, 0) / eligible, 4) if eligible > 0 else 0.0
            cycle_summaries.append({
                "cycle_id": cycle.id,
                "cycle_type": cycle.cycle_type.value,
                "closed_at": cycle.closed_at.isoformat() if cycle.closed_at else None,
                "eligible_count": eligible,
                "scored_count": len(scores_in_cycle),
                "tiers": {
                    "critical": tiers.get("critical", 0),
                    "high": tiers.get("high", 0),
                    "moderate": tiers.get("moderate", 0),
                    "low": tiers.get("low", 0),
                },
                "high_critical_pct": round(
                    (tiers.get("high", 0) + tiers.get("critical", 0)) / eligible, 4
                ) if eligible > 0 else 0.0,
            })

        # Latest cycle ORT status
        latest_hc = None
        if latest_cycle:
            latest_entry = next(
                (c for c in reversed(cycle_summaries) if c["cycle_id"] == latest_cycle.id),
                None,
            )
            if latest_entry:
                latest_hc = latest_entry["high_critical_pct"]

        # Read consecutive weeks elevated from deployment parameters
        from src.model.services.deployment_parameter import DeploymentParameterService
        dp_svc = DeploymentParameterService(session)
        consecutive_key = f"ort_consecutive_{team_id}"
        consecutive = dp_svc.get_typed(org_id, consecutive_key) or 0

        return JSONResponse({
            "team_id": team.id,
            "team_name": team.name,
            "team_size": team.member_count,
            "suppressed": False,
            "visibility_locked": gate_active,
            "high_critical_pct": latest_hc,
            "consecutive_weeks_elevated": consecutive,
            "ort_ceiling": ORT_CEILING,
            "cycles": cycle_summaries,
            "tier_distribution": dict(tier_overall),
        })
    finally:
        session.close()


async def get_team_recommendations(request: Request, team_id: int) -> JSONResponse:
    """GET /api/team/{id}/recommendations — top SHAP factors + matched resources for team."""
    access = _check_team_access(request, team_id)
    if not access:
        return JSONResponse({"error": "access denied"}, status_code=403)

    user, role, org_id = access
    factory = get_session_factory()
    session = factory()
    try:
        team = session.query(Team).filter(
            Team.id == team_id,
            Team.organisation_id == org_id,
        ).first()
        if not team:
            return JSONResponse({"error": "team not found"}, status_code=404)

        # Get latest closed cycle
        latest_cycle = session.query(AssessmentCycle).filter(
            AssessmentCycle.organisation_id == org_id,
            AssessmentCycle.status == CycleStatus.CLOSED,
        ).order_by(AssessmentCycle.closed_at.desc()).first()

        if not latest_cycle:
            return JSONResponse({"recommendations": [], "top_factors": []})

        # Aggregate SHAP values across team members
        team_employee_ids = [
            e.id for e in session.query(Employee.id).filter(
                Employee.team_id == team_id,
                Employee.organisation_id == org_id,
                Employee.consent_status.name != "withdrawn",
                Employee.exclusion_status == False,  # noqa: E702
            )
        ]

        scores = session.query(RiskScore).filter(
            RiskScore.cycle_id == latest_cycle.id,
            RiskScore.employee_id.in_(team_employee_ids),
        ).all()

        if not scores:
            return JSONResponse({"recommendations": [], "top_factors": []})

        # Aggregate shap_values: mean impact per feature across team members
        from collections import defaultdict
        feature_impacts: dict[str, list[float]] = defaultdict(list)

        for score in scores:
            if not score.shap_values:
                continue
            # score.shap_values is list[dict] with feature, impact_value
            if isinstance(score.shap_values, list):
                for item in score.shap_values:
                    feat = item.get("feature", "")
                    val = item.get("impact_value", 0)
                    if feat:
                        feature_impacts[feat].append(abs(float(val)))

        # Average impact per feature
        avg_impacts = {
            feat: round(mean(vals), 4)
            for feat, vals in feature_impacts.items()
            if vals
        }

        # Sort by average absolute impact
        ranked = sorted(avg_impacts.items(), key=lambda x: x[1], reverse=True)
        top_factors = [
            {"feature": feat, "avg_impact": impact, "direction": "increases"}
            for feat, impact in ranked[:5]
        ]

        # Map top factors to resources
        shap_list_for_resources = [
            {"feature": feat, "impact_value": impact}
            for feat, impact in ranked[:3]
        ]
        resources = get_resources_for_score(
            {item["feature"]: item["impact_value"] for item in shap_list_for_resources}
        )

        # Tier of top-scored employee (for urgency context)
        worst_tier_score = max(scores, key=lambda s: (
            {"critical": 4, "high": 3, "moderate": 2, "low": 1}.get(s.risk_tier, 0)
        ))
        worst_tier = worst_tier_score.risk_tier

        return JSONResponse({
            "team_id": team.id,
            "cycle_id": latest_cycle.id,
            "worst_tier": worst_tier,
            "scored_count": len(scores),
            "top_factors": top_factors,
            "recommendations": resources,
        })
    finally:
        session.close()


async def get_team_trajectory(request: Request, team_id: int) -> JSONResponse:
    """GET /api/team/{id}/trajectory — aggregated trajectory for all team members.

    Returns per-member trajectories + team-level aggregate (dominant trajectory,
    average delta, distribution of improved/held/worsened across members with 2+ cycles).
    Minimum 2 RiskScore records per employee to classify.
    """
    access = _check_team_access(request, team_id)
    if not access:
        return JSONResponse({"error": "access denied"}, status_code=403)

    user, role, org_id = access
    factory = get_session_factory()
    session = factory()
    try:
        team = session.query(Team).filter(
            Team.id == team_id,
            Team.organisation_id == org_id,
        ).first()
        if not team:
            return JSONResponse({"error": "team not found"}, status_code=404)

        # Get all team members with consent and not excluded
        team_employees = session.query(Employee).filter(
            Employee.team_id == team_id,
            Employee.organisation_id == org_id,
            Employee.consent_status.name != "withdrawn",
            Employee.exclusion_status == False,
        ).all()

        if not team_employees:
            return JSONResponse({
                "team_id": team.id,
                "team_size": team.member_count,
                "scored_count": 0,
                "team_trajectory": None,
                "distribution": {"improved": 0, "held": 0, "worsened": 0, "no_trajectory": 0},
                "average_delta": None,
                "members": [],
            })

        trajectory_svc = TrajectoryClassificationService(session)
        member_trajectories = []
        distribution = Counter()
        deltas = []

        for emp in team_employees:
            result = trajectory_svc.classify(
                employee_id=emp.id,
                organisation_id=org_id,
            )
            member_trajectories.append({
                "employee_id": emp.id,
                "trajectory": result.trajectory,
                "current_score": result.current_score,
                "previous_score": result.previous_score,
                "delta": result.delta,
                "cycles_compared": result.cycles_compared,
            })
            distribution[result.trajectory] += 1
            if result.delta is not None:
                deltas.append(result.delta)

        avg_delta = round(mean(deltas), 4) if deltas else None

        # Dominant trajectory = most common among members with a trajectory
        non_none = {k: v for k, v in distribution.items() if k != "no_trajectory"}
        dominant = max(non_none, key=non_none.get) if non_none else "no_trajectory"

        return JSONResponse({
            "team_id": team.id,
            "team_size": team.member_count,
            "scored_count": len(team_employees),
            "team_trajectory": dominant,
            "distribution": dict(distribution),
            "average_delta": avg_delta,
            "members": member_trajectories,
        })
    finally:
        session.close()


# Router
router = APIRouter()
router.add_api_route("/me", get_my_team, methods=["GET"])
router.add_api_route("/{team_id}/aggregate", get_team_aggregate, methods=["GET"])
router.add_api_route("/{team_id}/recommendations", get_team_recommendations, methods=["GET"])
router.add_api_route("/{team_id}/trajectory", get_team_trajectory, methods=["GET"])
