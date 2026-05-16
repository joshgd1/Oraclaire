"""
PermissionService — access control for Oraclaire.

Implements the access control matrix from G-1:
  - employee  : own data only (scores, SHAP, recommendations, own withdrawal)
  - manager   : team aggregates only (min 5 members); no individual scores
  - hr_admin  : org-wide trends + exclusion counts; no individual-level scores
  - system_admin: unrestricted — used for internal job accounts

Middleware integration (Nexus):
    from src.model.services.permission import require_permission

    @app.get("/api/employee/{eid}/scores")
    @require_permission("read_score")
    def get_scores(request): ...

Or as a direct service call:
    svc = PermissionService(session)
    svc.check(viewer_id="emp_42", viewer_role=Role.MANAGER,
               action="read_team_aggregate", target_team_id=7)
    # raises PermissionDenied if not allowed
"""


from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session

from src.model.entities import Employee, Role, Team
from src.model.entities._db import get_session_factory


class Action(Enum):
    READ_OWN_SCORE = "read_own_score"
    READ_TEAM_AGGREGATE = "read_team_aggregate"
    READ_ORG_TRENDS = "read_org_trends"
    READ_EXCLUSION_COUNTS = "read_exclusion_counts"
    READ_EMPLOYEE_DATA = "read_employee_data"  # GDPR data access
    UPDATE_EMPLOYEE_DATA = "update_employee_data"  # GDPR rectification
    DELETE_EMPLOYEE_DATA = "delete_employee_data"  # GDPR erasure
    READ_REVIEW = "read_review"
    APPROVE_REVIEW = "approve_review"
    OVERRIDE_REVIEW = "override_review"
    MANAGE_CYCLE = "manage_cycle"
    SUBMIT_ASSESSMENT_RESPONSE = "submit_assessment_response"
    READ_HEALTH_ALERTS = "read_health_alerts"
    ACKNOWLEDGE_HEALTH_ALERT = "acknowledge_health_alert"


@dataclass(frozen=True)
class Permission:
    """A granted permission — caller is authorized for the action."""

    action: Action
    viewer_id: str
    target: str  # e.g. "employee:42" or "team:7" or "org:1"


class PermissionDenied(Exception):
    """Raised when a permission check fails."""

    def __init__(self, viewer_id: str, action: Action, reason: str):
        self.viewer_id = viewer_id
        self.action = action
        self.reason = reason
        super().__init__(f"Permission denied: {viewer_id} cannot {action.value} ({reason})")


class PermissionService:
    """
    Access control checks for Oraclaire.

    All checks raise ``PermissionDenied`` on failure.
    Use ``check`` for enforcement or ``can_view`` for conditional logic.
    """

    MIN_TEAM_SIZE_FOR_MANAGER_VIEW = 5

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── public check API ───────────────────────────────────────────────────

    def check(
        self,
        *,
        viewer_id: str,
        viewer_role: Role,
        action: Action,
        target_employee_id: int | None = None,
        target_team_id: int | None = None,
        target_org_id: int | None = None,
    ) -> Permission:
        """Enforce a permission check. Raises PermissionDenied on failure."""
        if not self._check(
            viewer_id=viewer_id,
            viewer_role=viewer_role,
            action=action,
            target_employee_id=target_employee_id,
            target_team_id=target_team_id,
            target_org_id=target_org_id,
        ):
            reason = self._deny_reason(
                viewer_id=viewer_id,
                viewer_role=viewer_role,
                action=action,
                target_employee_id=target_employee_id,
                target_team_id=target_team_id,
                target_org_id=target_org_id,
            )
            raise PermissionDenied(viewer_id, action, reason)
        return Permission(
            action=action,
            viewer_id=viewer_id,
            target=self._target_str(
                target_employee_id=target_employee_id,
                target_team_id=target_team_id,
                target_org_id=target_org_id,
            ),
        )

    def can_view(
        self,
        *,
        viewer_id: str,
        viewer_role: Role,
        action: Action,
        target_employee_id: int | None = None,
        target_team_id: int | None = None,
        target_org_id: int | None = None,
    ) -> bool:
        """Return True if the viewer can perform the action, False otherwise."""
        return self._check(
            viewer_id=viewer_id,
            viewer_role=viewer_role,
            action=action,
            target_employee_id=target_employee_id,
            target_team_id=target_team_id,
            target_org_id=target_org_id,
        )

    # ── internal rules ─────────────────────────────────────────────────────

    def _check(
        self,
        *,
        viewer_id: str,
        viewer_role: Role,
        action: Action,
        target_employee_id: int | None,
        target_team_id: int | None,
        target_org_id: int | None,
    ) -> bool:
        # system_admin bypasses all checks
        if viewer_role == Role.SYSTEM_ADMIN:
            return True

        if viewer_role == Role.EMPLOYEE:
            return self._employee_check(
                viewer_id, action, target_employee_id, target_team_id
            )
        if viewer_role == Role.MANAGER:
            return self._manager_check(
                viewer_id, action, target_employee_id, target_team_id, target_org_id
            )
        if viewer_role == Role.HR_ADMIN:
            return self._hr_admin_check(
                viewer_id, action, target_employee_id, target_org_id
            )
        if viewer_role == Role.PRODUCT_OWNER:
            return self._product_owner_check(viewer_id, action, target_org_id)
        return False

    def _employee_check(
        self,
        viewer_id: str,
        action: Action,
        target_employee_id: int | None,
        target_team_id: int | None,
    ) -> bool:
        # Employees can only access their own records
        if target_employee_id is not None:
            emp = self._get_employee(target_employee_id)
            if emp is None:
                return False
            # Own data
            if str(emp.id) == viewer_id:
                return action in (
                    Action.READ_OWN_SCORE,
                    Action.READ_EMPLOYEE_DATA,
                    Action.UPDATE_EMPLOYEE_DATA,
                    Action.DELETE_EMPLOYEE_DATA,
                    Action.SUBMIT_ASSESSMENT_RESPONSE,
                )
            return False
        # Team-level for own team context (employees don't read team aggregates
        # from this service, but the dashboard may query via this path)
        if target_team_id is not None:
            emp = self._get_employee_by_external_id(viewer_id)
            if emp is not None and emp.team_id == target_team_id:
                return action == Action.READ_TEAM_AGGREGATE
            return False
        return False

    def _manager_check(
        self,
        viewer_id: str,
        action: Action,
        target_employee_id: int | None,
        target_team_id: int | None,
        target_org_id: int | None,
    ) -> bool:
        # Managers: team aggregates only (own team)
        if target_team_id is not None:
            team = self._get_team(target_team_id)
            if team is None:
                return False
            # Team-size suppression is handled at the handler level, not here
            if action == Action.READ_TEAM_AGGREGATE:
                return True
            # Managers cannot see individual employee data via this path
            if action in (
                Action.READ_OWN_SCORE,
                Action.READ_EMPLOYEE_DATA,
            ):
                # A manager can read their own score as an employee
                emp = self._get_employee_by_external_id(viewer_id)
                if (
                    emp is not None
                    and emp.team_id == target_team_id
                    and str(emp.id) == viewer_id
                    and action == Action.READ_OWN_SCORE
                ):
                    return True
                return False
            return False
        # Managers cannot access org-wide trends or exclusion counts
        if action in (Action.READ_ORG_TRENDS, Action.READ_EXCLUSION_COUNTS):
            return False
        return False

    def _hr_admin_check(
        self,
        viewer_id: str,
        action: Action,
        target_employee_id: int | None,
        target_org_id: int | None,
    ) -> bool:
        # HR admins: org-wide trends and exclusion counts only
        # They cannot see individual scores or employee data (G-1, G-4)
        # Exception: an HR admin can read their own score
        if target_employee_id is not None:
            emp = self._get_employee(target_employee_id)
            is_self = emp is not None and str(emp.id) == viewer_id
            if action == Action.READ_OWN_SCORE and is_self:
                return True
            # HR cannot access other employees' individual data (G-1)
            if action in (
                Action.READ_OWN_SCORE,
                Action.READ_EMPLOYEE_DATA,
                Action.UPDATE_EMPLOYEE_DATA,
                Action.DELETE_EMPLOYEE_DATA,
            ):
                return False
        if action == Action.READ_EXCLUSION_COUNTS:
            return True
        if action == Action.READ_ORG_TRENDS:
            return True
        if action == Action.READ_REVIEW:
            return True
        if action in (Action.APPROVE_REVIEW, Action.OVERRIDE_REVIEW):
            return True
        if action == Action.MANAGE_CYCLE:
            return True
        return False

    def _product_owner_check(
        self,
        viewer_id: str,
        action: Action,
        target_org_id: int | None,
    ) -> bool:
        # Product owners: health alert read + acknowledge only
        if target_org_id is None:
            return False
        if action in (Action.READ_HEALTH_ALERTS, Action.ACKNOWLEDGE_HEALTH_ALERT):
            return True
        return False

    # ── helpers ──────────────────────────────────────────────────────────

    def _get_employee(self, employee_id: int) -> Employee | None:
        return (
            self._session.query(Employee)
            .filter(Employee.id == employee_id)
            .first()
        )

    def _get_employee_by_external_id(self, external_id: str) -> Employee | None:
        """Look up employee by their external ID (the viewer_id string)."""
        try:
            emp_id = int(external_id)
            return self._get_employee(emp_id)
        except (ValueError, TypeError):
            return None

    def _get_team(self, team_id: int) -> Team | None:
        return (
            self._session.query(Team)
            .filter(Team.id == team_id)
            .first()
        )

    def _deny_reason(
        self,
        viewer_id: str,
        viewer_role: Role,
        action: Action,
        target_employee_id: int | None,
        target_team_id: int | None,
        target_org_id: int | None,
    ) -> str:
        if viewer_role == Role.EMPLOYEE:
            if action == Action.READ_OWN_SCORE:
                return "employees can only read their own score"
            return "employees cannot access this resource"
        if viewer_role == Role.MANAGER:
            if target_team_id is not None:
                team = self._get_team(target_team_id)
                if team is not None and team.member_count < self.MIN_TEAM_SIZE_FOR_MANAGER_VIEW:
                    return f"team has {team.member_count} members (minimum {self.MIN_TEAM_SIZE_FOR_MANAGER_VIEW})"
            if action in (Action.READ_ORG_TRENDS, Action.READ_EXCLUSION_COUNTS):
                return "managers cannot access org-wide data"
            return "manager role cannot perform this action"
        if viewer_role == Role.HR_ADMIN:
            if action in (
                Action.READ_EMPLOYEE_DATA,
                Action.UPDATE_EMPLOYEE_DATA,
                Action.DELETE_EMPLOYEE_DATA,
            ):
                return "HR admins cannot access individual employee data per G-1"
            if action == Action.READ_OWN_SCORE:
                emp = self._get_employee(target_employee_id) if target_employee_id else None
                if emp is None or str(emp.id) != viewer_id:
                    return "HR admins cannot access other employees' scores per G-1"
                # Self-case handled above; this shouldn't fire
            return "HR admin role cannot perform this action"
        if viewer_role == Role.PRODUCT_OWNER:
            if action in (Action.READ_HEALTH_ALERTS, Action.ACKNOWLEDGE_HEALTH_ALERT):
                return "product owner can only access health alerts"
            return "product owner role cannot perform this action"
        return "unknown role"

    @staticmethod
    def _target_str(
        target_employee_id: int | None,
        target_team_id: int | None,
        target_org_id: int | None,
    ) -> str:
        if target_employee_id is not None:
            return f"employee:{target_employee_id}"
        if target_team_id is not None:
            return f"team:{target_team_id}"
        if target_org_id is not None:
            return f"org:{target_org_id}"
        return "unknown"

    # ── context manager ────────────────────────────────────────────────────

    @classmethod
    def using(cls) -> "PermissionService":
        factory = get_session_factory()
        return cls(factory())

    def close(self) -> None:
        self._session.close()
