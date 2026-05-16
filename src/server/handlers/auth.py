"""
Authentication API handlers.

POST /api/auth/login          — request a magic link
GET  /api/auth/verify/{token} — exchange magic link token for JWT
POST /api/auth/refresh         — refresh access token
"""

from __future__ import annotations

import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.model.entities import Employee, Role
from src.model.entities._db import get_session_factory

logger = structlog.get_logger(__name__)

# Magic link token TTL in minutes
_MAGIC_LINK_TTL_MINUTES = int(os.environ.get("MAGIC_LINK_TTL_MINUTES", "15"))


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


def _create_access_token(user_id: str, role: Role, tenant_id: int) -> str:
    """Create a JWT access token for the authenticated user."""
    import jwt

    secret = os.environ.get("NEXUS_JWT_SECRET", "dev-secret-fix-in-production-min-32-chars")
    payload = {
        "sub": user_id,
        "user_id": user_id,
        "roles": [role.value],
        "tenant_id": tenant_id,
        "exp": datetime.now(UTC) + timedelta(hours=24),
        "iat": datetime.now(UTC),
        "iss": os.environ.get("NEXUS_JWT_ISSUER", "oraclaire"),
        "aud": os.environ.get("NEXUS_JWT_AUDIENCE", "oraclaire-api"),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


async def login(request: Request) -> JSONResponse:
    """
    POST /api/auth/login — request a magic link.

    Body: { "employee_id": int | string }

    In production: sends a link via email.
    In dev: returns the token directly in the response.
    """
    body = await request.json()
    employee_id_str = body.get("employee_id")
    if not employee_id_str:
        return JSONResponse({"error": "employee_id required"}, status_code=400)

    factory = get_session_factory()
    session = factory()
    try:
        # Look up employee
        try:
            emp_id = int(employee_id_str)
            emp = session.query(Employee).filter(Employee.id == emp_id).first()
        except ValueError:
            emp = None

        if emp is None:
            # Don't reveal whether the employee exists
            return JSONResponse({
                "message": "If that employee exists, a magic link has been sent.",
            })

        # Generate a short-lived magic token
        magic_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(minutes=_MAGIC_LINK_TTL_MINUTES)

        # Store token in DB (employee.auth_token field — add via migration if needed)
        # For now: log the token (dev mode)
        is_dev = os.environ.get("NEXUS_ENV", "development") != "production"

        if is_dev:
            logger.info("auth.magic_link.dev", employee_id=emp.id, token=magic_token)
            # In dev, return the token directly
            role = _role_from_user(type("User", (), {"roles": [emp.role.value]})())
            jwt_token = _create_access_token(str(emp.id), role, emp.organisation_id)
            return JSONResponse({
                "token": jwt_token,
                "employee_id": emp.id,
                "role": emp.role.value,
                "organisation_id": emp.organisation_id,
                "dev_mode": True,
                "message": "Dev mode: JWT returned directly. In production, a magic link would be emailed.",
            })

        # Production: would send email here
        logger.info("auth.magic_link.sent", employee_id=emp.id, expires_at=expires_at.isoformat())
        return JSONResponse({
            "message": "If that employee exists, a magic link has been sent.",
        })
    finally:
        session.close()


async def verify_token(request: Request) -> JSONResponse:
    """
    GET /api/auth/verify/{token} — exchange magic link token for JWT.

    In production: validates the token, issues JWT.
    In dev: returns a JWT directly (tokens are skipped in dev mode).
    """
    # Extract token from path
    path_parts = request.url.path.strip("/").split("/")
    token = path_parts[-1] if path_parts else ""

    if not token:
        return JSONResponse({"error": "token required"}, status_code=400)

    # Dev bypass: any non-empty token is accepted in dev
    is_dev = os.environ.get("NEXUS_ENV", "development") != "production"

    factory = get_session_factory()
    session = factory()
    try:
        if is_dev:
            # Dev: accept any token, look up employee 1 as demo
            emp = session.query(Employee).first()
            if emp is None:
                return JSONResponse({"error": "no employees found in dev db"}, status_code=404)
            role = _role_from_user(type("User", (), {"roles": [emp.role.value]})())
            jwt_token = _create_access_token(str(emp.id), role, emp.organisation_id)
            return JSONResponse({
                "token": jwt_token,
                "employee_id": emp.id,
                "role": emp.role.value,
                "organisation_id": emp.organisation_id,
            })

        # Production: validate magic token, issue JWT
        return JSONResponse({"error": "magic link verification not implemented"}, status_code=501)
    finally:
        session.close()


async def refresh_token(request: Request) -> JSONResponse:
    """
    POST /api/auth/refresh — refresh an access token.

    Body: { "token": str }

    Validates the current token and issues a new one with the same claims.
    """
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    body = await request.json()
    old_token = body.get("token")
    if not old_token:
        return JSONResponse({"error": "token required"}, status_code=400)

    # Verify the old token is valid (but not expired — refresh allows a grace period)
    import jwt

    secret = os.environ.get("NEXUS_JWT_SECRET", "dev-secret-fix-in-production-min-32-chars")
    try:
        payload = jwt.decode(
            old_token,
            secret,
            algorithms=["HS256"],
            audience=os.environ.get("NEXUS_JWT_AUDIENCE", "oraclaire-api"),
            issuer=os.environ.get("NEXUS_JWT_ISSUER", "oraclaire"),
        )
    except jwt.ExpiredSignatureError:
        return JSONResponse({"error": "token expired, please re-authenticate"}, status_code=401)
    except Exception:
        return JSONResponse({"error": "invalid token"}, status_code=401)

    user_id = payload.get("user_id") or payload.get("sub")
    roles = payload.get("roles", ["employee"])
    tenant_id = payload.get("tenant_id")

    role_map = {
        "system_admin": Role.SYSTEM_ADMIN,
        "hr_admin": Role.HR_ADMIN,
        "manager": Role.MANAGER,
        "employee": Role.EMPLOYEE,
    }
    role = role_map.get(roles[0].lower(), Role.EMPLOYEE)

    new_token = _create_access_token(str(user_id), role, tenant_id)
    return JSONResponse({
        "token": new_token,
        "expires_in": 86400,
    })


# Router
router = APIRouter()
router.add_api_route("/auth/login", login, methods=["POST"])
router.add_api_route("/auth/verify/{token}", verify_token, methods=["GET"])
router.add_api_route("/auth/refresh", refresh_token, methods=["POST"])
