"""
Integration tests for API handlers: visibility gate, employee score API,
manager endpoints, and data rights.

Uses SQLite in-memory database with a real session_factory.
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from starlette.requests import Request

from src.model.entities import (
    AssessmentCycle,
    Employee,
    RiskScore,
    Role,
    Team,
)
from src.model.entities._db import get_engine, get_session_factory
from src.server.handlers import data_rights, employee, hr_aggregate, manager


# ── In-memory SQLite test database ────────────────────────────────────────────

_ORG_ID = 1
_TEAM_ID = 1


@pytest.fixture(autouse=True)
def _reset_db():
    """Use in-memory SQLite with NullPool for all handler tests."""
    import sqlalchemy
    from sqlalchemy.pool import StaticPool
    from src.model.entities import Base
    from src.model.entities._db import get_session_factory

    db_url = "sqlite:///:memory:"

    # Use StaticPool + single connection to ensure data visibility
    # StaticPool reuses one connection, avoiding isolation issues
    engine = sqlalchemy.create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        pool_pre_ping=True,
    )
    Base.metadata.create_all(engine)

    # Patch into _db module globals so get_session_factory() returns sessions
    # attached to OUR engine
    import src.model.entities._db as _db_mod
    _db_mod._engine = engine
    _db_mod._session_factory = None  # force recreation with our engine

    # Also patch config so any other code that reads DATABASE_URL gets our URL
    import src.config
    _original_db_url = src.config.DATABASE_URL
    src.config.DATABASE_URL = db_url

    yield

    # Restore
    src.config.DATABASE_URL = _original_db_url
    _db_mod._engine = None
    _db_mod._session_factory = None
    engine.dispose()


def _run_async(coro):
    """Run an async handler in a synchronous test."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop:
        # Already in async context — create a new task
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    return asyncio.run(coro)


def _make_employee(session, employee_id: int, team_id: int = _TEAM_ID, role: Role = Role.EMPLOYEE) -> Employee:
    from src.model.entities import ConsentStatus, SenioritySource
    emp = Employee(
        id=employee_id,
        organisation_id=_ORG_ID,
        team_id=team_id,
        role=role,
        consent_status=ConsentStatus.CONSENTED,
        seniority_tier=0,
        seniority_source=SenioritySource.HRIS_DERIVED,
        exclusion_status=False,
    )
    session.add(emp)
    session.commit()
    return emp


def _make_team(session, team_id: int, org_id: int = _ORG_ID, member_count: int = 5) -> Team:
    team = Team(id=team_id, name=f"Team {team_id}", organisation_id=org_id, member_count=member_count)
    session.add(team)
    session.commit()
    return team


def _make_cycle(
    session,
    cycle_id: int,
    org_id: int = _ORG_ID,
    status: str = "CLOSED",
    hours_ago: int = 48,
) -> AssessmentCycle:
    """Create a cycle, optionally closed N hours ago for visibility gate testing."""
    now = datetime.now(UTC)
    cycle = AssessmentCycle(
        id=cycle_id,
        organisation_id=org_id,
        cycle_type="PULSE",
        status=status,
        started_at=now - timedelta(hours=hours_ago + 1) if hours_ago else now,
    )
    if status == "CLOSED" and hours_ago is not None:
        cycle.closed_at = now - timedelta(hours=hours_ago)
    session.add(cycle)
    session.commit()
    return cycle


def _make_risk_score(
    session,
    employee_id: int,
    cycle_id: int,
    tier: str = "moderate",
    numeric_score: float = 0.25,
) -> RiskScore:
    score = RiskScore(
        employee_id=employee_id,
        cycle_id=cycle_id,
        numeric_score=numeric_score,
        risk_tier=tier,
        model_version="sprint-1-rf",
        scored_at=datetime.now(UTC),
        shap_values=[{"feature": "mental_fatigue_score", "impact_value": 0.1}],
    )
    session.add(score)
    session.commit()
    return score


def _mock_request(user_id: str, roles: list[str] | None = None, tenant_id: int = _ORG_ID):
    """Build a mock Starlette Request with user state."""
    user = MagicMock()
    user.user_id = user_id
    user.roles = roles or ["employee"]
    user.tenant_id = tenant_id
    request = MagicMock(spec=Request)
    request.state.user = user
    request.state.tenant_id = tenant_id
    return request


def _body_json(response):
    """Extract JSON body from a response (sync helper for use in sync test methods)."""
    import json
    return json.loads(response.body)


# ── Visibility Gate Tests ──────────────────────────────────────────────────────

class TestVisibilityGate:
    """M6-08: 24h employee-first visibility gate."""

    def test_trends_withheld_within_24h(self):
        """When latest cycle closed < 24h ago, HR trends returns zeros with visibility_locked=True."""
        session = get_session_factory()()
        try:
            # 1h ago — gate should be active
            cycle = _make_cycle(session, 1, hours_ago=1)
            _make_employee(session, 1)

            request = _mock_request("1", roles=["hr_admin"])
            response = _run_async(hr_aggregate.get_trends(request))

            body = _body_json(response)
            # Verify cycle was committed and engine is same
            found = session.query(AssessmentCycle).filter(AssessmentCycle.id == 1).first()
            print(f"DEBUG: cycle found={found is not None}, closed_at={getattr(found, 'closed_at', None) if found else None}")
            print(f"DEBUG engine id: {id(get_engine())}")
            print(f"DEBUG trends response: {body}")
            assert body["total_scored"] == 0
            assert body["tiers"] == {"low": 0, "moderate": 0, "high": 0, "critical": 0}
        finally:
            session.close()

    def test_trends_visible_after_24h(self):
        """When latest cycle closed > 24h ago, HR trends returns actual data."""
        session = get_session_factory()()
        try:
            # 25h ago — gate should have passed
            cycle = _make_cycle(session, 1, hours_ago=25)
            emp = _make_employee(session, 1)
            _make_risk_score(session, employee_id=1, cycle_id=1, tier="moderate")

            request = _mock_request("1", roles=["hr_admin"])
            response = _run_async(hr_aggregate.get_trends(request))

            body = _body_json(response)
            assert body["visibility_locked"] is False
            assert body["total_scored"] == 1
            assert body["tiers"]["moderate"] == 1
        finally:
            session.close()

    def test_teams_withheld_within_24h(self):
        """Team aggregates (HC%) are withheld within the 24h window."""
        session = get_session_factory()()
        try:
            _make_cycle(session, 1, hours_ago=1)
            _make_team(session, _TEAM_ID, member_count=5)
            _make_employee(session, 1, team_id=_TEAM_ID)

            request = _mock_request("1", roles=["hr_admin"])
            response = _run_async(hr_aggregate.get_teams(request))

            body = _body_json(response)
            # visibility_locked_until should be set
            assert body["visibility_locked"] is True
            # High/critical pct should NOT appear in team entries
            for team in body["teams"]:
                assert "high_critical_pct" not in team
        finally:
            session.close()


# ── Employee Score API Tests ──────────────────────────────────────────────────

class TestEmployeeScoreAPI:
    """Employee self-service score endpoints."""

    def test_get_my_scores_returns_latest(self):
        """GET /api/employee/me/scores returns the most recent score."""
        session = get_session_factory()()
        try:
            emp = _make_employee(session, 1)
            # Two cycles
            _make_cycle(session, 1, hours_ago=48)
            _make_cycle(session, 2, hours_ago=25)
            _make_risk_score(session, employee_id=1, cycle_id=1, tier="low")
            _make_risk_score(session, employee_id=1, cycle_id=2, tier="moderate")

            request = _mock_request("1")
            response = _run_async(employee.get_my_scores(request))

            body = _body_json(response)
            assert len(body["scores"]) == 1
            assert body["scores"][0]["risk_tier"] == "moderate"
        finally:
            session.close()

    def test_get_my_scores_empty_when_no_score(self):
        """Returns empty list when employee has no scores."""
        session = get_session_factory()()
        try:
            _make_employee(session, 1)
            request = _mock_request("1")
            response = _run_async(employee.get_my_scores(request))
            assert _body_json(response) == {"scores": []}
        finally:
            session.close()

    def test_get_my_shap_returns_decomposition(self):
        """GET /api/employee/me/shap returns SHAP values and resources."""
        session = get_session_factory()()
        try:
            _make_employee(session, 1)
            _make_cycle(session, 1, hours_ago=25)
            _make_risk_score(session, employee_id=1, cycle_id=1)

            request = _mock_request("1")
            response = _run_async(employee.get_my_shap(request))

            body = _body_json(response)
            assert "shap_values" in body
            assert "resources" in body
            assert isinstance(body["shap_values"], list)
        finally:
            session.close()

    def test_get_my_explanation_returns_human_readable(self):
        """GET /api/employee/me/explanation returns summary + factors."""
        session = get_session_factory()()
        try:
            _make_employee(session, 1)
            _make_cycle(session, 1, hours_ago=25)
            _make_risk_score(session, employee_id=1, cycle_id=1, tier="moderate")

            request = _mock_request("1")
            response = _run_async(employee.get_my_explanation(request))

            body = _body_json(response)
            assert "summary" in body
            assert "factors" in body
            assert len(body["factors"]) > 0
            # Factors should have required fields
            factor = body["factors"][0]
            assert "label" in factor
            assert "direction" in factor
            assert "impact_pct" in factor
        finally:
            session.close()

    def test_explanation_returns_404_when_no_score(self):
        """Returns 404 when employee has no score to explain."""
        session = get_session_factory()()
        try:
            _make_employee(session, 1)
            request = _mock_request("1")
            response = _run_async(employee.get_my_explanation(request))
            assert response.status_code == 404
        finally:
            session.close()


# ── Manager Endpoint Tests ─────────────────────────────────────────────────────

class TestManagerEndpoints:
    """Manager team aggregate access."""

    def test_manager_can_access_own_team(self):
        """Manager can access their own team's aggregate."""
        session = get_session_factory()()
        try:
            _make_cycle(session, 1, hours_ago=25)
            _make_team(session, _TEAM_ID, member_count=5)
            _make_employee(session, 10, team_id=_TEAM_ID, role=Role.MANAGER)
            _make_employee(session, 1, team_id=_TEAM_ID)

            request = _mock_request("10", roles=["manager"])
            response = _run_async(manager.get_team_aggregate(request, _TEAM_ID))

            assert response.status_code == 200
            body = _body_json(response)
            assert body["team_id"] == _TEAM_ID
            assert body["suppressed"] is False
        finally:
            session.close()

    def test_manager_cannot_access_other_team(self):
        """Manager cannot access another team's aggregate."""
        session = get_session_factory()()
        try:
            _make_employee(session, 10, team_id=2, role=Role.MANAGER)
            _make_team(session, 1, member_count=5)
            _make_team(session, 2, member_count=5)

            request = _mock_request("10", roles=["manager"])
            response = _run_async(manager.get_team_aggregate(request, _TEAM_ID))
            assert response.status_code == 403
        finally:
            session.close()

    def test_team_aggregate_suppressed_below_min_size(self):
        """Team aggregate is suppressed when team < MIN_TEAM_SIZE."""
        session = get_session_factory()()
        try:
            _make_cycle(session, 1, hours_ago=25)
            _make_team(session, _TEAM_ID, member_count=2)  # below MIN_TEAM_SIZE
            _make_employee(session, 10, team_id=_TEAM_ID, role=Role.MANAGER)
            _make_employee(session, 1, team_id=_TEAM_ID)

            request = _mock_request("10", roles=["manager"])
            response = _run_async(manager.get_team_aggregate(request, _TEAM_ID))

            body = _body_json(response)
            assert body["suppressed"] is True
            assert "suppression_reason" in body
        finally:
            session.close()

    def test_team_trajectory_returns_aggregated_trajectories(self):
        """GET /api/team/{id}/trajectory returns per-member trajectories + team aggregate."""
        session = get_session_factory()()
        try:
            _make_cycle(session, 1, hours_ago=50)
            _make_cycle(session, 2, hours_ago=25)
            _make_team(session, _TEAM_ID, member_count=5)
            manager_emp = _make_employee(session, 10, team_id=_TEAM_ID, role=Role.MANAGER)

            # Give 3 employees 2 scores each (enough for trajectory)
            for emp_id in [1, 2, 3]:
                _make_employee(session, emp_id, team_id=_TEAM_ID)
                # cycle 1 score: lower, cycle 2 score: higher → "worsened"
                s1 = _make_risk_score(session, employee_id=emp_id, cycle_id=1, tier="low")
                s1.numeric_score = 0.20
                s2 = _make_risk_score(session, employee_id=emp_id, cycle_id=2, tier="high")
                s2.numeric_score = 0.50
                session.commit()

            # Employee 4 has only 1 score → "no_trajectory"
            _make_employee(session, 4, team_id=_TEAM_ID)
            _make_risk_score(session, employee_id=4, cycle_id=2, tier="low")

            request = _mock_request("10", roles=["manager"])
            response = _run_async(manager.get_team_trajectory(request, _TEAM_ID))

            assert response.status_code == 200
            body = _body_json(response)
            assert body["team_id"] == _TEAM_ID
            assert body["team_size"] == 5
            assert body["scored_count"] == 5  # all 5 team employees
            assert "team_trajectory" in body
            assert "distribution" in body
            assert "average_delta" in body
            assert "members" in body
            # 3 worsened, 2 no_trajectory (employee 4 with 1 score + manager 10 with 0 scores)
            assert body["distribution"].get("worsened", 0) == 3
            assert body["distribution"].get("no_trajectory", 0) == 2
            # Each member has their own trajectory entry
            assert len(body["members"]) == 5
        finally:
            session.close()

    def test_team_trajectory_no_scores_returns_empty(self):
        """Returns empty distribution when no team members have scores."""
        session = get_session_factory()()
        try:
            _make_team(session, _TEAM_ID, member_count=5)
            _make_employee(session, 10, team_id=_TEAM_ID, role=Role.MANAGER)
            _make_employee(session, 1, team_id=_TEAM_ID)

            request = _mock_request("10", roles=["manager"])
            response = _run_async(manager.get_team_trajectory(request, _TEAM_ID))

            assert response.status_code == 200
            body = _body_json(response)
            assert body["scored_count"] == 2  # 2 employees (1 and 10), no scores
            assert body["team_trajectory"] == "no_trajectory"  # all employees have no_trajectory
            assert body["average_delta"] is None
            assert body["distribution"].get("no_trajectory", 0) == 2
        finally:
            session.close()


# ── Data Rights API Tests ─────────────────────────────────────────────────────

class TestDataRightsAPI:
    """GDPR data subject rights endpoints."""

    def test_employee_can_access_own_data(self):
        """Employee can view all data held about themselves."""
        session = get_session_factory()()
        try:
            emp = _make_employee(session, 1)
            _make_cycle(session, 1, hours_ago=25)
            _make_risk_score(session, employee_id=1, cycle_id=1)

            request = _mock_request("1")
            response = _run_async(data_rights.get_employee_data(request, 1))

            assert response.status_code == 200
            body = _body_json(response)
            assert "employee" in body["data"]
            assert "risk_scores" in body["data"]
            assert len(body["data"]["risk_scores"]) == 1
        finally:
            session.close()

    def test_employee_cannot_access_other_data(self):
        """Employee cannot view another employee's data without HR_ADMIN permission."""
        session = get_session_factory()()
        try:
            _make_employee(session, 1)
            _make_employee(session, 2)

            request = _mock_request("1")  # employee 1 trying to access employee 2
            response = _run_async(data_rights.get_employee_data(request, 2))
            assert response.status_code == 403
        finally:
            session.close()

    def test_export_returns_serialisable_payload(self):
        """GET /export returns a complete serialisable payload."""
        session = get_session_factory()()
        try:
            _make_employee(session, 1)
            _make_cycle(session, 1, hours_ago=25)
            _make_risk_score(session, employee_id=1, cycle_id=1)

            request = _mock_request("1")
            response = _run_async(data_rights.export_employee_data(request, 1))

            assert response.status_code == 200
            body = _body_json(response)
            assert "export" in body
            assert body["export"]["employee_id"] == 1
            assert "exported_at" in body["export"]
        finally:
            session.close()

    def test_delete_removes_employee_and_related_records(self):
        """DELETE /data removes employee, scores, and responses."""
        session = get_session_factory()()
        try:
            _make_employee(session, 1)
            _make_cycle(session, 1, hours_ago=25)
            _make_risk_score(session, employee_id=1, cycle_id=1)

            request = _mock_request("1")
            response = _run_async(data_rights.delete_employee_data(request, 1))
            assert response.status_code == 200

            # Employee is gone
            emp = session.query(Employee).filter(Employee.id == 1).first()
            assert emp is None

            # Scores are gone
            scores = session.query(RiskScore).filter(RiskScore.employee_id == 1).all()
            assert len(scores) == 0
        finally:
            session.close()

    def test_delete_requires_hr_admin_for_other_employee(self):
        """Employee cannot delete another employee's data unless HR_ADMIN."""
        session = get_session_factory()()
        try:
            _make_employee(session, 1)
            _make_employee(session, 2)

            # Employee 1 trying to delete employee 2
            request = _mock_request("1")
            response = _run_async(data_rights.delete_employee_data(request, 2))
            assert response.status_code == 403
        finally:
            session.close()
