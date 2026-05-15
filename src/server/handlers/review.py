"""
Human review gate API handlers.

M6-01: HR reviewer accesses Critical-tier scores only through this gate.
No intervention triggers for a Critical employee until HR approves or overrides.

Endpoints:
  GET  /api/reviews/pending         — list pending reviews for the caller's org
  GET  /api/reviews/{review_id}      — review detail: SHAP context + employee history
  POST /api/reviews/{review_id}/approve   — HR approves the score tier
  POST /api/reviews/{review_id}/override  — HR overrides the tier (requires reason)
"""

from __future__ import annotations

from datetime import datetime, timezone

from starlette.requests import Request
from starlette.responses import JSONResponse

from src.model.entities import (
    AssessmentCycle,
    AuditLog,
    Employee,
    HumanReview,
    RiskScore,
    Role,
)
from src.model.entities._db import get_session_factory
from src.model.services.permission import Action, PermissionDenied, PermissionService


def _role_from_user(user) -> Role:
    if hasattr(user, "roles") and user.roles:
        role_map = {
            "system_admin": Role.SYSTEM_ADMIN,
            "hr_admin": Role.HR_ADMIN,
            "manager": Role.MANAGER,
            "employee": Role.EMPLOYEE,
        }
        return role_map.get(user.roles[0].lower(), Role.EMPLOYEE)
    return Role.EMPLOYEE


# ── GET /api/reviews/pending ─────────────────────────────────────────────────


async def list_pending(request: Request) -> JSONResponse:
    """
    GET /api/reviews/pending?cycle_id={cycle_id}

    Returns all PENDING_REVIEW HumanReview records for the caller's organisation.
    If cycle_id is provided, filter to that cycle only.

    HR_ADMIN only.
    """
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    org_id = getattr(user, "tenant_id", None)
    role = _role_from_user(user)
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(
            viewer_id=user.user_id,
            viewer_role=role,
            action=Action.READ_REVIEW,
            target_org_id=org_id,
        )
    except PermissionDenied as e:
        return JSONResponse({"error": str(e)}, status_code=403)

    cycle_id_str = request.query_params.get("cycle_id")
    try:
        cycle_id = int(cycle_id_str) if cycle_id_str else None
    except ValueError:
        return JSONResponse({"error": "invalid cycle_id"}, status_code=400)

    factory = get_session_factory()
    session = factory()
    try:
        query = (
            session.query(HumanReview, RiskScore, Employee, AssessmentCycle)
            .join(RiskScore, HumanReview.risk_score_id == RiskScore.id)
            .join(Employee, HumanReview.employee_id == Employee.id)
            .join(AssessmentCycle, HumanReview.cycle_id == AssessmentCycle.id)
            .filter(
                Employee.organisation_id == org_id,
                HumanReview.review_status == "pending_review",
            )
        )
        if cycle_id is not None:
            query = query.filter(HumanReview.cycle_id == cycle_id)

        rows = query.order_by(HumanReview.created_at.desc()).all()

        return JSONResponse({
            "pending_reviews": [
                _review_summary(review, score, emp, cycle)
                for review, score, emp, cycle in rows
            ],
            "count": len(rows),
        })
    finally:
        session.close()


def _review_summary(
    review: HumanReview,
    score: RiskScore,
    emp: Employee,
    cycle: AssessmentCycle,
) -> dict:
    return {
        "review_id": review.id,
        "employee_id": emp.id,
        "employee_name": None,  # PII — HR does not see name at list level
        "cycle_id": cycle.id,
        "cycle_type": cycle.cycle_type.value,
        "risk_tier": score.risk_tier,
        "numeric_score": score.numeric_score,
        "seniority_tier": score.seniority_tier_at_score,
        "scored_at": score.scored_at.isoformat() if score.scored_at else None,
        "pending_since": review.created_at.isoformat(),
    }


# ── GET /api/reviews/{review_id} ─────────────────────────────────────────────


async def get_review(request: Request) -> JSONResponse:
    """
    GET /api/reviews/{review_id}

    Returns full review detail: SHAP decomposition, employee trajectory,
    cycle context. HR_ADMIN only.

    Returns 404 if review not found or not in caller's org.
    """
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    org_id = getattr(user, "tenant_id", None)
    role = _role_from_user(user)
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(
            viewer_id=user.user_id,
            viewer_role=role,
            action=Action.READ_REVIEW,
            target_org_id=org_id,
        )
    except PermissionDenied as e:
        return JSONResponse({"error": str(e)}, status_code=403)

    path_parts = request.url.path.strip("/").split("/")
    try:
        review_id = int(path_parts[-1])
    except (ValueError, IndexError):
        return JSONResponse({"error": "invalid review id"}, status_code=400)

    factory = get_session_factory()
    session = factory()
    try:
        review = session.query(HumanReview).filter(
            HumanReview.id == review_id
        ).first()
        if not review:
            return JSONResponse({"error": "review not found"}, status_code=404)

        # Load joined data
        score = session.query(RiskScore).filter(
            RiskScore.id == review.risk_score_id
        ).first()
        emp = session.query(Employee).filter(
            Employee.id == review.employee_id
        ).first()
        cycle = session.query(AssessmentCycle).filter(
            AssessmentCycle.id == review.cycle_id
        ).first()

        if not (score and emp and cycle):
            return JSONResponse({"error": "review has dangling references"}, status_code=404)

        # Verify org matches
        if emp.organisation_id != org_id:
            return JSONResponse({"error": "review not found"}, status_code=404)

        # Fetch prior scores for trajectory context
        prior_scores = (
            session.query(RiskScore)
            .filter(
                RiskScore.employee_id == emp.id,
                RiskScore.id != review.risk_score_id,
            )
            .order_by(RiskScore.scored_at.desc())
            .limit(5)
            .all()
        )

        return JSONResponse({
            "review_id": review.id,
            "status": review.review_status,
            "employee": {
                "id": emp.id,
                # Name is shown at detail level only
                "seniority_tier": emp.seniority_tier,
                "team_id": emp.team_id,
                "consent_status": emp.consent_status.value,
            },
            "cycle": {
                "id": cycle.id,
                "cycle_type": cycle.cycle_type.value,
                "started_at": cycle.started_at.isoformat(),
            },
            "risk_score": {
                "numeric_score": score.numeric_score,
                "risk_tier": score.risk_tier,
                "model_version": score.model_version,
                "seniority_tier_at_score": score.seniority_tier_at_score,
                "scored_at": score.scored_at.isoformat() if score.scored_at else None,
                "shap_values": score.shap_values,
            },
            "trajectory": [
                {
                    "cycle_id": s.cycle_id,
                    "risk_tier": s.risk_tier,
                    "numeric_score": s.numeric_score,
                    "scored_at": s.scored_at.isoformat() if s.scored_at else None,
                }
                for s in prior_scores
            ],
            "pending_since": review.created_at.isoformat(),
            "reviewer_id": review.reviewer_id,
            "reviewed_at": (
                review.reviewed_at.isoformat() if review.reviewed_at else None
            ),
            "override_reason": review.override_reason,
            "override_new_tier": review.override_new_tier,
        })
    finally:
        session.close()


# ── POST /api/reviews/{review_id}/approve ────────────────────────────────────


async def approve_review(request: Request) -> JSONResponse:
    """
    POST /api/reviews/{review_id}/approve

    HR approves the Critical-tier score. This releases the review gate —
    any intervention workflow for this employee can now proceed.

    Body: {} (no fields required)
    """
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    org_id = getattr(user, "tenant_id", None)
    role = _role_from_user(user)
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(
            viewer_id=user.user_id,
            viewer_role=role,
            action=Action.APPROVE_REVIEW,
            target_org_id=org_id,
        )
    except PermissionDenied as e:
        return JSONResponse({"error": str(e)}, status_code=403)

    path_parts = request.url.path.strip("/").split("/")
    try:
        review_id = int(path_parts[-2])
    except (ValueError, IndexError):
        return JSONResponse({"error": "invalid review id"}, status_code=400)

    factory = get_session_factory()
    session = factory()
    try:
        review = session.query(HumanReview).filter(
            HumanReview.id == review_id
        ).with_for_update().first()
        if not review:
            return JSONResponse({"error": "review not found"}, status_code=404)

        if review.review_status != "pending_review":
            return JSONResponse(
                {"error": f"review is already {review.review_status}"},
                status_code=409,
            )

        # Load employee and score for org verification and audit
        emp = session.query(Employee).filter(
            Employee.id == review.employee_id
        ).first()
        if not emp or emp.organisation_id != org_id:
            return JSONResponse({"error": "review not found"}, status_code=404)

        score = session.query(RiskScore).filter(
            RiskScore.id == review.risk_score_id
        ).first()

        review.review_status = "approved"
        review.reviewer_id = int(user.user_id)
        review.reviewed_at = datetime.now(timezone.utc)

        # Audit log entry (M1-11)
        audit = AuditLog(
            actor_id=str(user.user_id),
            action="review.approved",
            target_entity_type="human_review",
            target_entity_id=str(review.id),
            timestamp=datetime.now(timezone.utc),
            metadata_json={
                "employee_id": emp.id,
                "risk_tier": score.risk_tier if score else None,
                "cycle_id": review.cycle_id,
            },
        )
        session.add(audit)
        session.commit()

        return JSONResponse({
            "review_id": review.id,
            "status": review.review_status,
            "reviewer_id": review.reviewer_id,
            "reviewed_at": review.reviewed_at.isoformat(),
            "message": "Review approved. Intervention gate released.",
        })
    except Exception as exc:
        session.rollback()
        return JSONResponse({"error": str(exc)}, status_code=500)
    finally:
        session.close()


# ── POST /api/reviews/{review_id}/override ──────────────────────────────────


async def override_review(request: Request) -> JSONResponse:
    """
    POST /api/reviews/{review_id}/override

    HR overrides the tier. Requires a new tier and a reason.
    Changes the RiskScore.risk_tier to the new value.

    Body: {"new_tier": "high", "reason": "employee recently returned from leave..."}
    new_tier must be one of: low, moderate, high, critical
    reason must be 10–1000 characters.
    """
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    org_id = getattr(user, "tenant_id", None)
    role = _role_from_user(user)
    svc = PermissionService(get_session_factory()())
    try:
        svc.check(
            viewer_id=user.user_id,
            viewer_role=role,
            action=Action.OVERRIDE_REVIEW,
            target_org_id=org_id,
        )
    except PermissionDenied as e:
        return JSONResponse({"error": str(e)}, status_code=403)

    path_parts = request.url.path.strip("/").split("/")
    try:
        review_id = int(path_parts[-2])
    except (ValueError, IndexError):
        return JSONResponse({"error": "invalid review id"}, status_code=400)

    body = await request.json()
    new_tier = body.get("new_tier")
    reason = body.get("reason")

    VALID_TIERS = {"low", "moderate", "high", "critical"}
    if new_tier not in VALID_TIERS:
        return JSONResponse(
            {"error": f"new_tier must be one of {sorted(VALID_TIERS)}"},
            status_code=400,
        )
    if not isinstance(reason, str) or len(reason) < 10 or len(reason) > 1000:
        return JSONResponse(
            {"error": "reason must be a string of 10–1000 characters"},
            status_code=400,
        )

    factory = get_session_factory()
    session = factory()
    try:
        review = session.query(HumanReview).filter(
            HumanReview.id == review_id
        ).with_for_update().first()
        if not review:
            return JSONResponse({"error": "review not found"}, status_code=404)

        if review.review_status != "pending_review":
            return JSONResponse(
                {"error": f"review is already {review.review_status}"},
                status_code=409,
            )

        emp = session.query(Employee).filter(
            Employee.id == review.employee_id
        ).first()
        if not emp or emp.organisation_id != org_id:
            return JSONResponse({"error": "review not found"}, status_code=404)

        # Update the review record
        review.review_status = "overridden"
        review.reviewer_id = int(user.user_id)
        review.reviewed_at = datetime.now(timezone.utc)
        review.override_reason = reason
        review.override_new_tier = new_tier

        # Update the risk score tier
        score = session.query(RiskScore).filter(
            RiskScore.id == review.risk_score_id
        ).with_for_update().first()
        if score:
            score.risk_tier = new_tier

        # Audit log entry (M1-11)
        audit = AuditLog(
            actor_id=str(user.user_id),
            action="review.overridden",
            target_entity_type="human_review",
            target_entity_id=str(review.id),
            timestamp=datetime.now(timezone.utc),
            metadata_json={
                "employee_id": emp.id,
                "original_tier": score.risk_tier if score else None,
                "override_new_tier": new_tier,
                "override_reason": reason,
                "cycle_id": review.cycle_id,
            },
        )
        session.add(audit)
        session.commit()

        return JSONResponse({
            "review_id": review.id,
            "status": review.review_status,
            "reviewer_id": review.reviewer_id,
            "reviewed_at": review.reviewed_at.isoformat(),
            "override_new_tier": new_tier,
            "override_reason": review.override_reason,
            "message": f"Tier overridden to {new_tier}. Intervention gate released.",
        })
    except Exception as exc:
        session.rollback()
        return JSONResponse({"error": str(exc)}, status_code=500)
    finally:
        session.close()


# Router
from fastapi import APIRouter

router = APIRouter()
router.add_api_route("/pending", list_pending, methods=["GET"])
router.add_api_route("/{review_id}", get_review, methods=["GET"])
router.add_api_route("/{review_id}/approve", approve_review, methods=["POST"])
router.add_api_route("/{review_id}/override", override_review, methods=["POST"])
