"""
Tier-1 unit tests for PermissionService — PRODUCT_OWNER role and health alert actions.

Thin unit tests: mock the session, call _check directly.
No real infra; no patching of the DB at this layer.
"""

import pytest
from unittest.mock import MagicMock

from src.model.entities.employee import Role
from src.model.services.permission import PermissionService, Action


@pytest.fixture
def svc():
    """PermissionService with a mocked session."""
    mock_session = MagicMock()
    return PermissionService(mock_session)


class TestProductOwnerHealthAlerts:
    """PRODUCT_OWNER role permissions for C3a health alert actions."""

    def test_product_owner_can_read_health_alerts(self, svc):
        """PRODUCT_OWNER can READ_HEALTH_ALERTS (C3a Step 4)."""
        result = svc._check(
            viewer_id="po_42",
            viewer_role=Role.PRODUCT_OWNER,
            action=Action.READ_HEALTH_ALERTS,
            target_employee_id=None,
            target_team_id=None,
            target_org_id=1,
        )
        assert result is True

    def test_product_owner_can_acknowledge_health_alert(self, svc):
        """PRODUCT_OWNER can ACKNOWLEDGE_HEALTH_ALERT (C3a Step 5)."""
        result = svc._check(
            viewer_id="po_42",
            viewer_role=Role.PRODUCT_OWNER,
            action=Action.ACKNOWLEDGE_HEALTH_ALERT,
            target_employee_id=None,
            target_team_id=None,
            target_org_id=1,
        )
        assert result is True

    def test_manager_cannot_read_health_alerts(self, svc):
        """MANAGER cannot READ_HEALTH_ALERTS — alert read is PO-only."""
        result = svc._check(
            viewer_id="mgr_99",
            viewer_role=Role.MANAGER,
            action=Action.READ_HEALTH_ALERTS,
            target_employee_id=None,
            target_team_id=None,
            target_org_id=1,
        )
        assert result is False

    def test_hr_admin_cannot_acknowledge_health_alert(self, svc):
        """HR_ADMIN cannot ACKNOWLEDGE_HEALTH_ALERT — alert acknowledge is PO-only."""
        result = svc._check(
            viewer_id="hr_7",
            viewer_role=Role.HR_ADMIN,
            action=Action.ACKNOWLEDGE_HEALTH_ALERT,
            target_employee_id=None,
            target_team_id=None,
            target_org_id=1,
        )
        assert result is False
