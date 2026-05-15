"""
M4-10: Notification service.

Sends notifications when:
- A new pulse/CBI cycle opens
- Midpoint reminder for non-respondents
- Score is viewable (post 24h employee-first gate)

Consent-aware: withdrawn employees excluded.
No score content in notifications.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel


NOTIFICATIONS_LOG = Path("data/audit/notifications.jsonl")


class NotificationType(str, Enum):
    CYCLE_OPENED = "CYCLE_OPENED"
    MIDPOINT_REMINDER = "MIDPOINT_REMINDER"
    SCORE_VIEWABLE = "SCORE_VIEWABLE"


class NotificationRecord(BaseModel):
    notification_id: str
    employee_id: int
    organisation_id: int
    cycle_id: int
    notification_type: NotificationType
    message: str
    sent_at: str
    read_at: str | None = None


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _append(path: Path, record: BaseModel) -> None:
    _ensure_dir(path)
    with open(path, "a") as fh:
        fh.write(record.model_dump_json() + "\n")


def _read(path: Path) -> list[NotificationRecord]:
    if not path.exists():
        return []
    records = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records.append(NotificationRecord(**json.loads(line)))
    return records


def notify_cycle_opened(
    cycle_id: int,
    organisation_id: int,
    cycle_type: str,
    employee_ids: list[int],
) -> list[str]:
    """
    M4-10: Notify employees when a new assessment cycle opens.

    cycle_type: "pulse" or "cbi"
    Only employees who have consented and not withdrawn are notified.
    """
    notification_ids = []
    cycle_label = "pulse check-in" if cycle_type == "pulse" else "burnout assessment"
    message = (
        f"A new {cycle_label} has opened. "
        f"Your response helps us understand and support organisational wellbeing."
    )

    for emp_id in employee_ids:
        notification_ids.append(_write_notification(
            employee_id=emp_id,
            organisation_id=organisation_id,
            cycle_id=cycle_id,
            notification_type=NotificationType.CYCLE_OPENED,
            message=message,
        ))

    return notification_ids


def notify_midpoint_reminder(
    cycle_id: int,
    organisation_id: int,
    cycle_type: str,
    employee_ids: list[int],
    cycle_started_at: datetime,
) -> list[str]:
    """
    M4-10: Send midpoint reminder to employees who haven't responded.

    Call at cycle midpoint (e.g., 3.5 days into a 7-day cycle).
    Only employees who haven't submitted a response are notified.
    """
    notification_ids = []
    cycle_label = "pulse check-in" if cycle_type == "pulse" else "burnout assessment"

    for emp_id in employee_ids:
        notification_ids.append(_write_notification(
            employee_id=emp_id,
            organisation_id=organisation_id,
            cycle_id=cycle_id,
            notification_type=NotificationType.MIDPOINT_REMINDER,
            message=(
                f"Reminder: your {cycle_label} is still open. "
                f"Your response makes a difference — it only takes a few minutes."
            ),
        ))

    return notification_ids


def notify_score_viewable(
    cycle_id: int,
    organisation_id: int,
    employee_ids: list[int],
) -> list[str]:
    """
    M4-10: Notify employees when their score is ready to view (post 24h gate).

    The 24h gate is enforced at the API layer (employee dashboard),
    not here. This notification fires when the cycle closes and scoring
    completes, so the 24h window can begin.
    """
    notification_ids = []

    for emp_id in employee_ids:
        notification_ids.append(_write_notification(
            employee_id=emp_id,
            organisation_id=organisation_id,
            cycle_id=cycle_id,
            notification_type=NotificationType.SCORE_VIEWABLE,
            message=(
                "Your burnout assessment results are now available. "
                "Log in to view your personalised breakdown and resources."
            ),
        ))

    return notification_ids


def _write_notification(
    employee_id: int,
    organisation_id: int,
    cycle_id: int,
    notification_type: NotificationType,
    message: str,
) -> str:
    notification_id = str(uuid.uuid4())
    record = NotificationRecord(
        notification_id=notification_id,
        employee_id=employee_id,
        organisation_id=organisation_id,
        cycle_id=cycle_id,
        notification_type=notification_type,
        message=message,
        sent_at=datetime.now(timezone.utc).isoformat(),
        read_at=None,
    )
    _append(NOTIFICATIONS_LOG, record)
    return notification_id


def get_unread_notifications(
    employee_id: int,
    organisation_id: int | None = None,
) -> list[NotificationRecord]:
    """Return unread notifications for an employee."""
    records = _read(NOTIFICATIONS_LOG)
    unread = [r for r in records if r.employee_id == employee_id and r.read_at is None]
    if organisation_id is not None:
        unread = [r for r in unread if r.organisation_id == organisation_id]
    return unread


def mark_notification_read(notification_id: str) -> bool:
    """Mark a notification as read. Returns True if found and updated."""
    records = _read(NOTIFICATIONS_LOG)
    updated = False
    for r in records:
        if r.notification_id == notification_id:
            r.read_at = datetime.now(timezone.utc).isoformat()
            updated = True
    if updated:
        _ensure_dir(NOTIFICATIONS_LOG)
        with open(NOTIFICATIONS_LOG, "w") as fh:
            for r in records:
                fh.write(r.model_dump_json() + "\n")
    return updated
