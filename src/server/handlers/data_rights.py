"""
Data Subject Rights API — M8-03.

GET  /api/employee/{id}/data     — view all data held about this employee
GET  /api/employee/{id}/export  — JSON export of all individual data
DELETE /api/employee/{id}/data  — immediate hard delete (GDPR/G-3)

Access: employee can only access their own data.
Audit log entry on every invocation.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from io import StringIO

from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.model.entities import (
    AssessmentResponse,
    AuditLog,
    Employee,
    RiskScore,
    Withdrawal,
)
from src.model.entities._db import get_session_factory
from src.model.services.permission import Action, PermissionDenied, PermissionService
from src.server.handlers.hr_aggregate import _role_from_user


async def get_employee_data(request: Request, employee_id: int) -> JSONResponse:
    """GET /api/employee/{id}/data — view all data held about this employee."""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    # Access control: employee can only view their own data
    if int(user.user_id) != employee_id:
        role = _role_from_user(user)
        perm_svc = PermissionService(get_session_factory()())
        try:
            perm_svc.check(
                viewer_id=user.user_id,
                viewer_role=role,
                action=Action.READ_EMPLOYEE_DATA,
                target_employee_id=employee_id,
            )
        except PermissionDenied as e:
            return JSONResponse({"error": str(e)}, status_code=403)

    factory = get_session_factory()
    session = factory()
    try:
        emp = session.query(Employee).filter(Employee.id == employee_id).first()
        if not emp:
            return JSONResponse({"error": "employee not found"}, status_code=404)

        # Assessment responses
        responses = session.query(AssessmentResponse).filter(
            AssessmentResponse.employee_id == employee_id
        ).all()

        # Risk scores
        scores = session.query(RiskScore).filter(
            RiskScore.employee_id == employee_id
        ).all()

        # Withdrawals
        withdrawals = session.query(Withdrawal).filter(
            Withdrawal.employee_id == employee_id
        ).all()

        data = {
            "employee": {
                "id": emp.id,
                "consent_status": emp.consent_status.value,
                "consent_timestamp": (
                    emp.consent_timestamp.isoformat()
                    if emp.consent_timestamp else None
                ),
                "seniority_tier": emp.seniority_tier,
                "seniority_source": (
                    emp.seniority_source.value if emp.seniority_source else None
                ),
                "exclusion_status": emp.exclusion_status,
                "exclusion_category": (
                    emp.exclusion_category.value if emp.exclusion_category else None
                ),
                "team_id": emp.team_id,
                "created_at": (
                    emp.created_at.isoformat() if emp.created_at else None
                ),
            },
            "assessment_responses": [
                {
                    "id": r.id,
                    "cycle_id": r.cycle_id,
                    "item_index": r.item_index,
                    "response_value": r.response_value,
                    "submitted_at": (
                        r.submitted_at.isoformat() if r.submitted_at else None
                    ),
                }
                for r in responses
            ],
            "risk_scores": [
                {
                    "id": s.id,
                    "cycle_id": s.cycle_id,
                    "risk_tier": s.risk_tier,
                    "numeric_score": s.numeric_score,
                    "scored_at": s.scored_at.isoformat() if s.scored_at else None,
                    "model_version": s.model_version,
                }
                for s in scores
            ],
            "withdrawals": [
                {
                    "id": w.id,
                    "requested_at": (
                        w.requested_at.isoformat() if w.requested_at else None
                    ),
                    "effective_at": (
                        w.effective_at.isoformat() if w.effective_at else None
                    ),
                    "cancelled_at": (
                        w.cancelled_at.isoformat() if w.cancelled_at else None
                    ),
                }
                for w in withdrawals
            ],
        }

        # Audit log
        _write_audit(session, user.user_id, "data_access", employee_id)

        return JSONResponse({"data": data})
    finally:
        session.close()


async def export_employee_data(request: Request, employee_id: int) -> JSONResponse:
    """GET /api/employee/{id}/export — JSON export of all individual data."""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    if int(user.user_id) != employee_id:
        role = _role_from_user(user)
        perm_svc = PermissionService(get_session_factory()())
        try:
            perm_svc.check(
                viewer_id=user.user_id,
                viewer_role=role,
                action=Action.READ_EMPLOYEE_DATA,
                target_employee_id=employee_id,
            )
        except PermissionDenied as e:
            return JSONResponse({"error": str(e)}, status_code=403)

    factory = get_session_factory()
    session = factory()
    try:
        emp = session.query(Employee).filter(Employee.id == employee_id).first()
        if not emp:
            return JSONResponse({"error": "employee not found"}, status_code=404)

        responses = session.query(AssessmentResponse).filter(
            AssessmentResponse.employee_id == employee_id
        ).all()
        scores = session.query(RiskScore).filter(
            RiskScore.employee_id == employee_id
        ).all()
        withdrawals = session.query(Withdrawal).filter(
            Withdrawal.employee_id == employee_id
        ).all()

        export_payload = {
            "exported_at": datetime.now(UTC).isoformat(),
            "employee_id": employee_id,
            "consent_status": emp.consent_status.value,
            "consent_timestamp": (
                emp.consent_timestamp.isoformat() if emp.consent_timestamp else None
            ),
            "seniority_tier": emp.seniority_tier,
            "seniority_source": (
                emp.seniority_source.value if emp.seniority_source else None
            ),
            "team_id": emp.team_id,
            "assessment_responses": [
                {
                    "cycle_id": r.cycle_id,
                    "item_index": r.item_index,
                    "response_value": r.response_value,
                    "submitted_at": (
                        r.submitted_at.isoformat() if r.submitted_at else None
                    ),
                }
                for r in responses
            ],
            "risk_scores": [
                {
                    "cycle_id": s.cycle_id,
                    "risk_tier": s.risk_tier,
                    "numeric_score": s.numeric_score,
                    "scored_at": s.scored_at.isoformat() if s.scored_at else None,
                    "model_version": s.model_version,
                }
                for s in scores
            ],
            "withdrawals": [
                {
                    "requested_at": (
                        w.requested_at.isoformat() if w.requested_at else None
                    ),
                    "effective_at": (
                        w.effective_at.isoformat() if w.effective_at else None
                    ),
                }
                for w in withdrawals
            ],
        }

        _write_audit(session, user.user_id, "data_export", employee_id)

        return JSONResponse({"export": export_payload})
    finally:
        session.close()


async def delete_employee_data(request: Request, employee_id: int) -> JSONResponse:
    """DELETE /api/employee/{id}/data — immediate hard delete of all individual data.

    No 48h cooling-off for delete (different from withdrawal per D15-3).
    Removes: employee record, assessment responses, risk scores, withdrawals.
    Audit log entry BEFORE deletion for traceability.
    """
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    if int(user.user_id) != employee_id:
        role = _role_from_user(user)
        perm_svc = PermissionService(get_session_factory()())
        try:
            perm_svc.check(
                viewer_id=user.user_id,
                viewer_role=role,
                action=Action.DELETE_EMPLOYEE_DATA,
                target_employee_id=employee_id,
            )
        except PermissionDenied as e:
            return JSONResponse({"error": str(e)}, status_code=403)

    factory = get_session_factory()
    session = factory()
    try:
        emp = session.query(Employee).filter(Employee.id == employee_id).first()
        if not emp:
            return JSONResponse({"error": "employee not found"}, status_code=404)

        # Audit log BEFORE deletion (we can still read the employee_id)
        _write_audit(session, user.user_id, "data_delete", employee_id)

        # Hard delete individual-level records (order matters for FK constraints)
        session.query(AssessmentResponse).filter(
            AssessmentResponse.employee_id == employee_id
        ).delete(synchronize_session=False)

        session.query(RiskScore).filter(
            RiskScore.employee_id == employee_id
        ).delete(synchronize_session=False)

        session.query(Withdrawal).filter(
            Withdrawal.employee_id == employee_id
        ).delete(synchronize_session=False)

        session.query(Employee).filter(Employee.id == employee_id).delete(
            synchronize_session=False
        )

        session.commit()
        return JSONResponse({"deleted": True, "employee_id": employee_id})
    except Exception as e:
        session.rollback()
        return JSONResponse(
            {"error": f"delete failed: {e}"},
            status_code=500,
        )
    finally:
        session.close()


def _write_audit(session, actor_id: str, action: str, target_employee_id: int) -> None:
    """Append an audit log entry for data rights operations."""
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        target_entity_type="employee",
        target_entity_id=target_employee_id,
        timestamp=datetime.now(UTC),
        metadata_json=json.dumps({"rights_request": action}),
    )
    session.add(entry)
    session.commit()


# Router
router = APIRouter()
router.add_api_route("/{employee_id}/data", get_employee_data, methods=["GET"])
router.add_api_route("/{employee_id}/export", export_employee_data, methods=["GET"])
router.add_api_route("/{employee_id}/data", delete_employee_data, methods=["DELETE"])
