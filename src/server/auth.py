"""
Auth configuration for Oraclaire Nexus server.

RBAC matrix (G-1):
  - employee   : read_own_score, read_employee_data, update_employee_data,
                 delete_employee_data
  - manager    : read_team_aggregate, read_own_score, read_employee_data,
                 read_review, approve_review, override_review, manage_cycle
  - hr_admin   : read_org_trends, read_exclusion_counts, read_review,
                 approve_review, override_review, manage_cycle
  - system_admin: unbounded — full access
"""

from __future__ import annotations

import os

from kailash.trust.auth.jwt import JWTConfig
from nexus.auth.audit.config import AuditConfig
from nexus.auth.plugin import NexusAuthPlugin
from nexus.auth.rate_limit import RateLimitConfig

# ── JWT ─────────────────────────────────────────────────────────────────────────

_jwt_secret = os.environ.get("NEXUS_JWT_SECRET", "")
if not _jwt_secret:
    import secrets

    _jwt_secret = secrets.token_hex(32)
    print("WARNING: NEXUS_JWT_SECRET not set; generated ephemeral secret")

JWT_CONFIG = JWTConfig(
    secret=_jwt_secret,
    algorithm="HS256",
    issuer=os.environ.get("NEXUS_JWT_ISSUER", "oraclaire"),
    audience=os.environ.get("NEXUS_JWT_AUDIENCE", "oraclaire-api"),
    exempt_paths=["/health", "/healthz", "/ready"],
)

# ── RBAC ───────────────────────────────────────────────────────────────────────

# Maps Role names (uppercase) to list of action strings
_RBAC: dict[str, list[str]] = {
    "EMPLOYEE": [
        "read_own_score",
        "read_employee_data",
        "update_employee_data",
        "delete_employee_data",
    ],
    "MANAGER": [
        "read_team_aggregate",
        "read_own_score",
        "read_employee_data",
        "read_review",
        "approve_review",
        "override_review",
        "manage_cycle",
    ],
    "HR_ADMIN": [
        "read_org_trends",
        "read_exclusion_counts",
        "read_review",
        "approve_review",
        "override_review",
        "manage_cycle",
    ],
    "SYSTEM_ADMIN": [
        "read_own_score",
        "read_team_aggregate",
        "read_org_trends",
        "read_exclusion_counts",
        "read_employee_data",
        "update_employee_data",
        "delete_employee_data",
        "read_review",
        "approve_review",
        "override_review",
        "manage_cycle",
    ],
}


_AUDIT_CONFIG = AuditConfig(
    enabled=True,
    backend="logging",
    log_request_body=False,
    log_response_body=False,
    include_request_headers=False,
    exclude_paths=["/health", "/healthz", "/ready"],
    redact_headers=["authorization", "x-api-key", "cookie"],
    redact_replacement="[REDACTED]",
)


def make_auth_plugin(
    rate_limit_requests: int = 100,
    jwt_config: JWTConfig | None = None,
) -> NexusAuthPlugin:
    """Build the Nexus auth plugin with JWT + RBAC + rate limiting."""
    return NexusAuthPlugin(
        jwt=jwt_config or JWT_CONFIG,
        rbac=_RBAC,
        rbac_default_role="EMPLOYEE",
        rate_limit=RateLimitConfig(requests_per_minute=rate_limit_requests),
        audit=_AUDIT_CONFIG,
    )
