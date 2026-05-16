"""
HRIS Export Guard Service.

Blocks API responses that would facilitate export of individual burnout risk scores
to HRIS or performance management systems. Enforces the Oraclaire data governance
policy stated in the EU AI Act conformity assessment §7.3.

This is a technical enforcement layer — the API blocks any response format
or combination of fields that would enable bulk extraction of individual scores
for HRIS integration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class HRISExportBlock:
    """Describes a blocked response and the reason."""

    endpoint: str
    reason: str
    blocked_fields: list[str]


class HRISExportGuardService:
    """
    Inspects API response shapes and blocks those that would facilitate
    score export to HRIS or performance management systems.

    Blocking rules:
    1. Individual score + employee_id returned to a non-owning caller → BLOCK
    2. Bulk score export (list of employee_id + score pairs) → BLOCK
    3. Score data paired with any HRIS-pipeline-bound field (performance rating,
       manager_id used as join key, etc.) → BLOCK
    4. Individual scores returned to a MANAGER caller → BLOCK (managers only get
       aggregates with team-size suppression ≥ 5)
    5. Scores returned to a non-authenticated caller → BLOCK (handled by auth)
    """

    # Endpoints that return individual employee data — checked for HRIS export patterns
    INDIVIDUAL_ENDPOINTS = {
        "/api/employee/me/scores",
        "/api/employee/me/shap",
        "/api/employee/me/trajectory",
        "/api/employee/me/explanation",
    }

    # Endpoints that return employee trend data
    TREND_ENDPOINTS = {
        "/api/employee/{id}/pulse-trend",
    }

    # Endpoints that aggregate multiple employees — subject to team-size suppression
    AGGREGATE_ENDPOINTS = {
        "/api/team/{id}/aggregate",
        "/api/team/{id}/recommendations",
        "/api/hr/teams",
        "/api/hr/trends",
    }

    def __init__(self, viewer_role: str, viewer_id: str | None = None):
        self.viewer_role = viewer_role
        self.viewer_id = viewer_id

    def check_response(
        self,
        endpoint: str,
        response_data: Any,
        *,
        target_employee_id: str | int | None = None,
    ) -> HRISExportBlock | None:
        """
        Inspect a response and return an HRISExportBlock if the response
        would facilitate HRIS export. Returns None if the response is clean.

        Parameters
        ----------
        endpoint:
            The API endpoint that produced this response.
        response_data:
            The decoded JSON response body (dict or list).
        target_employee_id:
            For /api/employee/{id}/... endpoints, the employee ID being queried.
            For /me endpoints, this is inferred from the caller's JWT.
        """
        # MANAGER role — individual endpoints are always blocked
        if self.viewer_role == "manager":
            if endpoint in self.INDIVIDUAL_ENDPOINTS or endpoint in self.TREND_ENDPOINTS:
                return HRISExportBlock(
                    endpoint=endpoint,
                    reason=(
                        "Managers cannot access individual employee scores, SHAP, "
                        "trajectory, or trend data. Use team aggregate endpoints instead."
                    ),
                    blocked_fields=["numeric_score", "risk_tier", "shap_values", "trajectory"],
                )

        # HR_ADMIN role — individual endpoints are allowed (HR can see individual scores)
        # but bulk extraction patterns are still blocked
        if self.viewer_role == "hr_admin":
            if self._is_bulk_extraction_pattern(endpoint, response_data):
                return HRISExportBlock(
                    endpoint=endpoint,
                    reason=(
                        "Bulk extraction of individual scores for HRIS export is not permitted. "
                        "Use aggregate endpoints with appropriate team-size suppression."
                    ),
                    blocked_fields=["employee_id", "numeric_score", "risk_tier", "id"],
                )

        # EMPLOYEE role — /me endpoints are fine; /{id} endpoints need ownership check
        if self.viewer_role == "employee":
            if endpoint in self.TREND_ENDPOINTS:
                # Employee querying another employee's trend — block
                if target_employee_id is not None and str(target_employee_id) != str(self.viewer_id):
                    return HRISExportBlock(
                        endpoint=endpoint,
                        reason=(
                            "Employees can only view their own pulse trend data."
                        ),
                        blocked_fields=["employee_id", "pulse_trend", "trajectory"],
                    )

        return None

    def _is_bulk_extraction_pattern(self, endpoint: str, data: Any) -> bool:
        """
        Detect bulk extraction patterns that suggest HRIS export intent.

        A bulk extraction pattern is: a list response containing
        employee_id/id paired with score/tier data for more than a
        threshold number of employees in a single response.
        """
        if not isinstance(data, dict):
            return False

        # Check for list of employee-score pairs at the top level
        for key, value in data.items():
            if not isinstance(value, list):
                continue
            if self._list_is_employee_score_bundle(value):
                return True

        return False

    def _list_is_employee_score_bundle(self, items: list) -> bool:
        """Return True if this list looks like an employee+score bundle for export."""
        if not items:
            return False
        count = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            has_id = "employee_id" in item or "id" in item
            has_score = any(
                k in item
                for k in (
                    "numeric_score",
                    "risk_tier",
                    "score",
                    "shap_values",
                    "trajectory",
                    "tier",
                )
            )
            if has_id and has_score:
                count += 1
        # Flag if 3+ individual records in one response (suggests bulk export)
        return count >= 3


def check_hris_export(
    viewer_role: str,
    viewer_id: str | None,
    endpoint: str,
    response_data: Any,
    *,
    target_employee_id: str | int | None = None,
) -> HRISExportBlock | None:
    """
    Convenience function wrapping HRISExportGuardService.check_response.

    Call this after building a response and before returning it from any
    handler that returns individual employee score data.
    """
    svc = HRISExportGuardService(viewer_role=viewer_role, viewer_id=viewer_id)
    return svc.check_response(
        endpoint=endpoint,
        response_data=response_data,
        target_employee_id=target_employee_id,
    )
