"""
Oraclaire Nexus API server.

Run:
    uv run python -m src.server.app
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root on sys.path
_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from dotenv import load_dotenv

load_dotenv()

import structlog
from nexus import Nexus

from src.server.auth import JWT_CONFIG, make_auth_plugin

logger = structlog.get_logger(__name__)

# ── Port config ────────────────────────────────────────────────────────────────

API_PORT = int(os.environ.get("NEXUS_API_PORT", "8000"))

# ── App factory ───────────────────────────────────────────────────────────────


def create_app() -> Nexus:
    """Build and configure the Oraclaire Nexus application."""
    app = Nexus(
        api_port=API_PORT,
        enable_monitoring=False,
        rate_limit=200,
        cors_origins=_cors_origins(),
        cors_allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        cors_allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        cors_allow_credentials=True,
    )

    # Auth plugin (JWT + RBAC + rate limiting)
    auth = make_auth_plugin(rate_limit_requests=200)
    app.add_plugin(auth)

    # Register API routers
    _register_endpoints(app)

    return app


def _cors_origins() -> list[str]:
    origins = os.environ.get("CORS_ORIGINS", "")
    if not origins:
        return ["http://localhost:3000", "http://localhost:8501"]
    return [o.strip() for o in origins.split(",") if o.strip()]


def _register_endpoints(app: Nexus) -> None:
    """Register all API endpoint handlers."""
    # Import handlers lazily to avoid circular imports at module load
    from src.server.handlers import (
        assessment_cycle,
        auth,
        employee,
        health,
        hr_aggregate,
        notifications,
        pulse,
        scoring,
    )

    app.include_router(auth.router, prefix="/api")
    app.include_router(pulse.router, prefix="/api/pulse")
    app.include_router(employee.router, prefix="/api/employee")
    app.include_router(assessment_cycle.router, prefix="/api/cycle")
    app.include_router(hr_aggregate.router, prefix="/api/hr")
    app.include_router(scoring.router, prefix="/api/scoring")
    app.include_router(notifications.router, prefix="/api/notifications")

    # Health — no auth required (exempt in JWTConfig)
    app.register_endpoint("/health", ["GET"], health.health_check)
    app.register_endpoint("/ready", ["GET"], health.ready_check)


# ── Entrypoint ────────────────────────────────────────────────────────────────


def main() -> None:
    app = create_app()
    logger.info("oraclaire.starting", port=API_PORT)
    app.start()


if __name__ == "__main__":
    main()
