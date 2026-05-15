"""Health check endpoints."""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse


async def health_check(request: Request) -> JSONResponse:
    """Liveness probe — returns 200 if the process is alive."""
    return JSONResponse({"status": "ok"})


async def ready_check(request: Request) -> JSONResponse:
    """Readiness probe — returns 200 if the server is ready to accept traffic."""
    try:
        from src.model.entities._db import get_engine

        with get_engine().connect() as conn:
            conn.execute(conn.make_ping())
    except Exception as e:
        return JSONResponse({"status": "not_ready", "error": str(e)}, status_code=503)
    return JSONResponse({"status": "ready"})
