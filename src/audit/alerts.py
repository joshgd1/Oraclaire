"""
C3a health alert audit trail — append-only JSONL.

POSTed to by cycle_health.py after scoring.  Read by the PO dashboard
(list_alerts handler) and by create_cycle() as the alert gate.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


ALERTS_LOG = Path("data/audit/alerts.jsonl")
ACKNOWLEDGMENTS_LOG = Path("data/audit/acknowledgments.jsonl")


class AlertStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"


class AlertDecision(str, Enum):
    RETRAIN = "RETRAIN"
    THRESHOLD_ADJUST = "THRESHOLD_ADJUST"
    RESUME_CONFIRMED = "RESUME_CONFIRMED"


class AlertRecord(BaseModel):
    alert_id: str
    cycle_id: int
    organisation_id: int
    alert_type: str = "CRITICAL_CEILING_EXCEEDED"
    critical_fraction: float
    ceiling: float = 0.05
    participation_rate: float | None = None  # only for PARTICIPATION_DROP
    affected_count: int
    total_count: int
    timestamp: str
    status: AlertStatus = AlertStatus.ACTIVE
    team_id: int | None = None        # only for ORT_THRESHOLD_EXCEEDED
    team_name: str | None = None      # only for ORT_THRESHOLD_EXCEEDED


class AcknowledgmentRecord(BaseModel):
    alert_id: str
    acknowledger_id: str = Field(..., min_length=1)
    acknowledged_at: str
    note: str = Field(..., min_length=1, max_length=1000)
    decision: AlertDecision


# ── private helpers ────────────────────────────────────────────────────────────


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _append(path: Path, record: BaseModel) -> None:
    _ensure_dir(path)
    with open(path, "a") as fh:
        fh.write(record.model_dump_json() + "\n")


def _read(path: Path) -> list[BaseModel]:
    if not path.exists():
        return []
    records = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


# ── alert write / read ────────────────────────────────────────────────────────


def write_alert(
    cycle_id: int,
    organisation_id: int,
    critical_fraction: float,
    affected_count: int,
    total_count: int,
    ceiling: float = 0.05,
    participation_rate: float | None = None,
    alert_type: str = "CRITICAL_CEILING_EXCEEDED",
    team_id: int | None = None,
    team_name: str | None = None,
) -> str:
    """Write an alert record; returns the generated alert_id."""
    alert_id = str(uuid.uuid4())
    record = AlertRecord(
        alert_id=alert_id,
        cycle_id=cycle_id,
        organisation_id=organisation_id,
        alert_type=alert_type,
        critical_fraction=critical_fraction,
        ceiling=ceiling,
        participation_rate=participation_rate,
        affected_count=affected_count,
        total_count=total_count,
        timestamp=datetime.now(timezone.utc).isoformat(),
        status=AlertStatus.ACTIVE,
        team_id=team_id,
        team_name=team_name,
    )
    _append(ALERTS_LOG, record)
    return alert_id


def write_acknowledgment(
    alert_id: str,
    acknowledger_id: str,
    note: str,
    decision: AlertDecision,
) -> str:
    """Append an acknowledgment and update the alert's status to ACKNOWLEDGED."""
    ts = datetime.now(timezone.utc).isoformat()

    ack = AcknowledgmentRecord(
        alert_id=alert_id,
        acknowledger_id=acknowledger_id,
        acknowledged_at=ts,
        note=note,
        decision=decision,
    )
    _append(ACKNOWLEDGMENTS_LOG, ack)

    # Rewrite the alert record with ACKNOWLEDGED status
    alerts = _read(ALERTS_LOG)
    _ensure_dir(ALERTS_LOG)
    with open(ALERTS_LOG, "w") as fh:
        for raw in alerts:
            rec = AlertRecord(**raw)
            if rec.alert_id == alert_id:
                rec = AlertRecord(
                    alert_id=rec.alert_id,
                    cycle_id=rec.cycle_id,
                    organisation_id=rec.organisation_id,
                    alert_type=rec.alert_type,
                    critical_fraction=rec.critical_fraction,
                    ceiling=rec.ceiling,
                    participation_rate=rec.participation_rate,
                    affected_count=rec.affected_count,
                    total_count=rec.total_count,
                    timestamp=rec.timestamp,
                    status=AlertStatus.ACKNOWLEDGED,
                    team_id=rec.team_id,
                    team_name=rec.team_name,
                )
            fh.write(rec.model_dump_json() + "\n")

    return ts


def get_active_alerts(organisation_id: Optional[int] = None) -> list[AlertRecord]:
    """Return all ACTIVE alert records, optionally filtered by organisation."""
    raw = _read(ALERTS_LOG)
    records = [AlertRecord(**r) for r in raw]
    active = [r for r in records if r.status == AlertStatus.ACTIVE]
    if organisation_id is not None:
        active = [r for r in active if r.organisation_id == organisation_id]
    return active


def get_alert_by_id(alert_id: str) -> Optional[AlertRecord]:
    """Return the alert record with the given id, or None if not found."""
    raw = _read(ALERTS_LOG)
    for r in raw:
        if r.get("alert_id") == alert_id:
            return AlertRecord(**r)
    return None
