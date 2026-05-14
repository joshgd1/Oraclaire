"""
Pure data functions for HR aggregate and reviewer views.

Extracted from Streamlit views so business logic is testable without
mocking the presentation layer. Each function receives plain data and
returns plain data — no Streamlit calls, no side effects.
"""

import json
from collections import Counter
from pathlib import Path

from src.config import (
    MIN_TEAM_SIZE,
    ORT_CEILING,
    ORT_PULSE_CONSECUTIVE_WEEKS,
    PREDICTIONS_LOG,
    TIER_ORDER,
)


def compute_tier_distribution(scores: list[dict]) -> dict:
    """Compute tier distribution from scored employee results.

    Args:
        scores: List of score dicts, each with at least "risk_tier".

    Returns:
        Dict with "total" (int), "tiers" (dict of tier -> count),
        "percentages" (dict of tier -> float 0-1), and "order" (list
        of tier names in severity order).
    """
    if not scores:
        return {"total": 0, "tiers": {}, "percentages": {}, "order": TIER_ORDER}

    tiers = Counter(s.get("risk_tier", "unknown") for s in scores)
    total = len(scores)
    percentages = {tier: count / total for tier, count in tiers.items()}

    return {
        "total": total,
        "tiers": dict(tiers),
        "percentages": percentages,
        "order": TIER_ORDER,
    }


def compute_ort_status(teams: list[dict]) -> dict:
    """Check Organisational Risk Threshold for each team.

    A team triggers an ORT alert when its High+Critical percentage
    EXCEEDS (not equals) ORT_CEILING AND it has been elevated for
    ORT_PULSE_CONSECUTIVE_WEEKS or more consecutive weeks.

    Args:
        teams: List of team dicts with "name", "high_critical_pct",
               "consecutive_weeks_elevated", "team_size".

    Returns:
        Dict with "alerts" (teams exceeding ORT), "ok_teams" (within
        threshold), "excluded_teams" (below MIN_TEAM_SIZE).
    """
    alerts = []
    ok_teams = []
    excluded = []

    for team in teams:
        if team.get("team_size", 0) < MIN_TEAM_SIZE:
            excluded.append(team["name"])
            continue
        hc_pct = team.get("high_critical_pct", 0)
        weeks = team.get("consecutive_weeks_elevated", 0)
        if hc_pct > ORT_CEILING and weeks >= ORT_PULSE_CONSECUTIVE_WEEKS:
            alerts.append(team)
        else:
            ok_teams.append(team)

    return {
        "alerts": alerts,
        "ok_teams": ok_teams,
        "excluded_teams": excluded,
    }


def compute_exclusion_summary(exclusions: dict[str, int]) -> list[dict]:
    """Sort exclusion counts by count descending.

    Args:
        exclusions: Dict mapping category name to count.

    Returns:
        List of {"category": str, "count": int} sorted by count desc.
    """
    return [
        {"category": cat, "count": count}
        for cat, count in sorted(exclusions.items(), key=lambda x: -x[1])
    ]


def get_pending_critical_flags(
    predictions_log: str = PREDICTIONS_LOG,
) -> list[dict]:
    """Read predictions log and return unreviewed Critical-tier entries.

    Args:
        predictions_log: Path to predictions.jsonl audit trail.

    Returns:
        List of dicts with employee_id, burnout_probability, timestamp,
        reviewer_id, review_status for Critical-tier pending review.
    """
    path = Path(predictions_log)
    if not path.exists():
        return []

    pending = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if (
                entry.get("risk_tier") == "critical"
                and entry.get("review_status") == "pending"
            ):
                pending.append({
                    "employee_id": entry["employee_id"],
                    "burnout_probability": entry["burnout_probability"],
                    "risk_tier": entry["risk_tier"],
                    "timestamp": entry["timestamp"],
                    "reviewer_id": entry.get("reviewer_id"),
                    "review_status": entry.get("review_status"),
                    "shap_values": entry.get("shap_values", {}),
                })

    return pending
