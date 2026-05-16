"""
Notification API handlers.

GET /api/notifications           — list unread notifications for the authenticated employee
POST /api/notifications/{id}/read — mark a notification as read
"""

from __future__ import annotations

from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.model.services.notification import get_unread_notifications, mark_notification_read


async def list_notifications(request: Request) -> JSONResponse:
    """GET /api/notifications — get unread notifications for the authenticated employee."""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    org_id = getattr(user, "tenant_id", None)
    employee_id = int(user.user_id)

    notifications = get_unread_notifications(employee_id, organisation_id=org_id)

    return JSONResponse({
        "notifications": [
            {
                "notification_id": n.notification_id,
                "cycle_id": n.cycle_id,
                "notification_type": n.notification_type.value,
                "message": n.message,
                "sent_at": n.sent_at,
            }
            for n in notifications
        ],
    })


async def mark_read(request: Request) -> JSONResponse:
    """
    POST /api/notifications/{id}/read — mark a notification as read.
    """
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    path_parts = request.url.path.strip("/").split("/")
    notification_id = path_parts[-2]  # /api/notifications/{id}/read

    success = mark_notification_read(notification_id)
    if not success:
        return JSONResponse({"error": "notification not found"}, status_code=404)

    return JSONResponse({"notification_id": notification_id, "read": True})


# Router
router = APIRouter()
router.add_api_route("/", list_notifications, methods=["GET"])
router.add_api_route("/{id}/read", mark_read, methods=["POST"])
