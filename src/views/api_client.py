"""
Oraclaire API client for Streamlit frontend.

Handles JWT authentication and calls to the Nexus API running at API_BASE_URL.
"""

from __future__ import annotations

import json
import os
from typing import Any

import requests

API_BASE_URL = os.environ.get("NEXUS_API_BASE_URL", "http://localhost:8000")
TIMEOUT = 10.0


class ApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _unwrap(resp: requests.Response) -> dict[str, Any]:
    """Unwrap Nexus response envelope if present."""
    envelope = resp.json()
    raw = envelope.get("data", {}).get("content", envelope)
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


def _headers(token: str | None = None) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def login(employee_id: str) -> dict[str, Any]:
    """
    POST /api/auth/login with employee_id.
    Returns the full auth response dict including 'token' key on success.
    Raises ApiError on failure.
    """
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/auth/login",
            json={"employee_id": employee_id},
            timeout=TIMEOUT,
        )
    except requests.ConnectionError as exc:
        raise ApiError(f"Could not connect to API at {API_BASE_URL}") from exc

    if not resp.ok:
        raise ApiError(f"Login failed: {resp.text}", status_code=resp.status_code)

    data = _unwrap(resp)
    token = data.get("token")
    if not token:
        raise ApiError("No token in auth response", status_code=500)
    return data


def get_pending_reviews(token: str, cycle_id: int | None = None) -> dict[str, Any]:
    """
    GET /api/reviews/pending?cycle_id={cycle_id}
    Returns {"pending_reviews": [...], "count": N}.
    Raises ApiError on failure.
    """
    params = {}
    if cycle_id is not None:
        params["cycle_id"] = str(cycle_id)

    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/reviews/pending",
            params=params,
            headers=_headers(token),
            timeout=TIMEOUT,
        )
    except requests.ConnectionError as exc:
        raise ApiError(f"Could not connect to API at {API_BASE_URL}") from exc

    if not resp.ok:
        raise ApiError(f"Failed to fetch pending reviews: {resp.text}", status_code=resp.status_code)

    return _unwrap(resp)


def get_review_detail(token: str, review_id: int) -> dict[str, Any]:
    """
    GET /api/reviews/{review_id}
    Returns full review detail including shap_values and trajectory.
    Raises ApiError on failure.
    """
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/reviews/{review_id}",
            headers=_headers(token),
            timeout=TIMEOUT,
        )
    except requests.ConnectionError as exc:
        raise ApiError(f"Could not connect to API at {API_BASE_URL}") from exc

    if not resp.ok:
        raise ApiError(f"Failed to fetch review {review_id}: {resp.text}", status_code=resp.status_code)

    return _unwrap(resp)


def approve_review(token: str, review_id: int) -> dict[str, Any]:
    """
    POST /api/reviews/{review_id}/approve
    Returns {"review_id": ..., "status": "approved", ...}.
    Raises ApiError on failure.
    """
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/reviews/{review_id}/approve",
            json={},
            headers=_headers(token),
            timeout=TIMEOUT,
        )
    except requests.ConnectionError as exc:
        raise ApiError(f"Could not connect to API at {API_BASE_URL}") from exc

    if not resp.ok:
        raise ApiError(f"Failed to approve review {review_id}: {resp.text}", status_code=resp.status_code)

    return _unwrap(resp)


def override_review(token: str, review_id: int, new_tier: str, reason: str) -> dict[str, Any]:
    """
    POST /api/reviews/{review_id}/override
    Body: {"new_tier": new_tier, "reason": reason}
    Returns {"review_id": ..., "status": "overridden", ...}.
    Raises ApiError on failure.
    """
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/reviews/{review_id}/override",
            json={"new_tier": new_tier, "reason": reason},
            headers=_headers(token),
            timeout=TIMEOUT,
        )
    except requests.ConnectionError as exc:
        raise ApiError(f"Could not connect to API at {API_BASE_URL}") from exc

    if not resp.ok:
        raise ApiError(f"Failed to override review {review_id}: {resp.text}", status_code=resp.status_code)

    return _unwrap(resp)


# ── Employee endpoints ─────────────────────────────────────────────────────────


def get_employee_scores(token: str) -> dict[str, Any]:
    """
    GET /api/employee/me/scores — latest score for the authenticated employee.
    Returns {"scores": [{"id", "cycle_id", "numeric_score", "risk_tier",
                         "model_version", "scored_at", "resources"}]}.
    Raises ApiError on failure.
    """
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/employee/me/scores",
            headers=_headers(token),
            timeout=TIMEOUT,
        )
    except requests.ConnectionError as exc:
        raise ApiError(f"Could not connect to API at {API_BASE_URL}") from exc

    if not resp.ok:
        raise ApiError(f"Failed to fetch employee scores: {resp.text}", status_code=resp.status_code)

    return _unwrap(resp)


def get_employee_shap(token: str) -> dict[str, Any]:
    """
    GET /api/employee/me/shap — SHAP decomposition for the latest score.
    Returns {"shap_values": [...], "seniority_tier_at_score": N, "resources": [...]}.
    Raises ApiError on failure.
    """
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/employee/me/shap",
            headers=_headers(token),
            timeout=TIMEOUT,
        )
    except requests.ConnectionError as exc:
        raise ApiError(f"Could not connect to API at {API_BASE_URL}") from exc

    if not resp.ok:
        raise ApiError(f"Failed to fetch SHAP values: {resp.text}", status_code=resp.status_code)

    return _unwrap(resp)


def get_employee_trajectory(token: str) -> dict[str, Any]:
    """
    GET /api/employee/me/trajectory — trajectory classification for the authenticated employee.
    Returns {"employee_id", "trajectory", "current_score", "previous_score",
             "delta", "cycles_compared", "threshold_used"}.
    Raises ApiError on failure.
    """
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/employee/me/trajectory",
            headers=_headers(token),
            timeout=TIMEOUT,
        )
    except requests.ConnectionError as exc:
        raise ApiError(f"Could not connect to API at {API_BASE_URL}") from exc

    if not resp.ok:
        raise ApiError(f"Failed to fetch trajectory: {resp.text}", status_code=resp.status_code)

    return _unwrap(resp)


def get_employee_explanation(token: str) -> dict[str, Any]:
    """
    GET /api/employee/me/explanation — human-readable SHAP breakdown in plain language.
    Returns {"employee_id", "score", "tier", "generated_at", "summary", "factors": [...]}.
    Required for EU AI Act Art. 13 right-to-explanation.
    Raises ApiError on failure.
    """
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/employee/me/explanation",
            headers=_headers(token),
            timeout=TIMEOUT,
        )
    except requests.ConnectionError as exc:
        raise ApiError(f"Could not connect to API at {API_BASE_URL}") from exc

    if not resp.ok:
        raise ApiError(f"Failed to fetch explanation: {resp.text}", status_code=resp.status_code)

    return _unwrap(resp)


# ── Manager endpoints ────────────────────────────────────────────────────────


def get_my_team(token: str) -> dict[str, Any]:
    """
    GET /api/manager/me — the authenticated manager's own team info.
    Returns {"team_id", "team_name", "team_size"}.
    Raises ApiError on failure.
    """
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/team/me",
            headers=_headers(token),
            timeout=TIMEOUT,
        )
    except requests.ConnectionError as exc:
        raise ApiError(f"Could not connect to API at {API_BASE_URL}") from exc

    if not resp.ok:
        raise ApiError(f"Failed to fetch manager team: {resp.text}", status_code=resp.status_code)

    return _unwrap(resp)


def get_team_aggregate(token: str, team_id: int) -> dict[str, Any]:
    """
    GET /api/team/{id}/aggregate — team-level tier distribution and trend.
    Returns {"team_id", "team_name", "team_size", "suppressed", "cycles": [...],
             "tier_distribution", "high_critical_pct", "consecutive_weeks_elevated"}.
    Raises ApiError on failure.
    """
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/team/{team_id}/aggregate",
            headers=_headers(token),
            timeout=TIMEOUT,
        )
    except requests.ConnectionError as exc:
        raise ApiError(f"Could not connect to API at {API_BASE_URL}") from exc

    if not resp.ok:
        raise ApiError(f"Failed to fetch team aggregate: {resp.text}", status_code=resp.status_code)

    return _unwrap(resp)


def get_team_recommendations(token: str, team_id: int) -> dict[str, Any]:
    """
    GET /api/team/{id}/recommendations — team SHAP factors + matched resources.
    Returns {"team_id", "worst_tier", "top_factors": [...], "recommendations": [...]}.
    Raises ApiError on failure.
    """
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/team/{team_id}/recommendations",
            headers=_headers(token),
            timeout=TIMEOUT,
        )
    except requests.ConnectionError as exc:
        raise ApiError(f"Could not connect to API at {API_BASE_URL}") from exc

    if not resp.ok:
        raise ApiError(f"Failed to fetch team recommendations: {resp.text}", status_code=resp.status_code)

    return _unwrap(resp)


def get_team_trajectory(token: str, team_id: int) -> dict[str, Any]:
    """
    GET /api/team/{id}/trajectory — aggregated trajectory for all team members.
    Returns {"team_id", "team_trajectory", "distribution": {...},
             "average_delta", "scored_count", "members": [...]}.
    Raises ApiError on failure.
    """
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/team/{team_id}/trajectory",
            headers=_headers(token),
            timeout=TIMEOUT,
        )
    except requests.ConnectionError as exc:
        raise ApiError(f"Could not connect to API at {API_BASE_URL}") from exc

    if not resp.ok:
        raise ApiError(f"Failed to fetch team trajectory: {resp.text}", status_code=resp.status_code)

    return _unwrap(resp)


# ── HR Aggregate endpoints ─────────────────────────────────────────────────────


def get_trends(token: str) -> dict[str, Any]:
    """
    GET /api/hr/trends — org-wide risk tier distribution.
    Returns {"cycle_id", "total_scored", "tiers", "visibility_locked", "visibility_locked_until"}.
    Raises ApiError on failure.
    """
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/hr/trends",
            headers=_headers(token),
            timeout=TIMEOUT,
        )
    except requests.ConnectionError as exc:
        raise ApiError(f"Could not connect to API at {API_BASE_URL}") from exc

    if not resp.ok:
        raise ApiError(f"Failed to fetch HR trends: {resp.text}", status_code=resp.status_code)

    return _unwrap(resp)


def get_teams(token: str) -> dict[str, Any]:
    """
    GET /api/hr/teams — team-level aggregates.
    Returns {"teams": [...], "visibility_locked", "visibility_locked_until"}.
    Raises ApiError on failure.
    """
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/hr/teams",
            headers=_headers(token),
            timeout=TIMEOUT,
        )
    except requests.ConnectionError as exc:
        raise ApiError(f"Could not connect to API at {API_BASE_URL}") from exc

    if not resp.ok:
        raise ApiError(f"Failed to fetch HR teams: {resp.text}", status_code=resp.status_code)

    return _unwrap(resp)


def get_exclusions(token: str) -> dict[str, Any]:
    """
    GET /api/hr/exclusions — exclusion counts by category.
    Returns {"total": N, "by_category": {...}}.
    Raises ApiError on failure.
    """
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/hr/exclusions",
            headers=_headers(token),
            timeout=TIMEOUT,
        )
    except requests.ConnectionError as exc:
        raise ApiError(f"Could not connect to API at {API_BASE_URL}") from exc

    if not resp.ok:
        raise ApiError(f"Failed to fetch exclusions: {resp.text}", status_code=resp.status_code)

    return _unwrap(resp)


def get_participation(token: str) -> dict[str, Any]:
    """
    GET /api/hr/participation — participation rates per cycle.
    Returns {"cycles": [...]}.
    Raises ApiError on failure.
    """
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/hr/participation",
            headers=_headers(token),
            timeout=TIMEOUT,
        )
    except requests.ConnectionError as exc:
        raise ApiError(f"Could not connect to API at {API_BASE_URL}") from exc

    if not resp.ok:
        raise ApiError(f"Failed to fetch participation: {resp.text}", status_code=resp.status_code)

    return _unwrap(resp)


# ── GDPR / Data Rights endpoints ───────────────────────────────────────────────


def view_my_data(token: str, employee_id: int) -> dict[str, Any]:
    """
    GET /api/employee/{id}/data — all data held about this employee.
    Returns {"data": {...}}.
    Raises ApiError on failure.
    """
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/employee/{employee_id}/data",
            headers=_headers(token),
            timeout=TIMEOUT,
        )
    except requests.ConnectionError as exc:
        raise ApiError(f"Could not connect to API at {API_BASE_URL}") from exc

    if not resp.ok:
        raise ApiError(f"Failed to fetch your data: {resp.text}", status_code=resp.status_code)

    return _unwrap(resp)


def export_my_data(token: str, employee_id: int) -> dict[str, Any]:
    """
    GET /api/employee/{id}/export — JSON export of all individual data.
    Returns {"export": {...}}.
    Raises ApiError on failure.
    """
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/employee/{employee_id}/export",
            headers=_headers(token),
            timeout=TIMEOUT,
        )
    except requests.ConnectionError as exc:
        raise ApiError(f"Could not connect to API at {API_BASE_URL}") from exc

    if not resp.ok:
        raise ApiError(f"Failed to export your data: {resp.text}", status_code=resp.status_code)

    return _unwrap(resp)


def delete_my_data(token: str, employee_id: int) -> dict[str, Any]:
    """
    DELETE /api/employee/{id}/data — delete all individual data.
    Returns {"deleted": True, "employee_id": N}.
    Raises ApiError on failure.
    """
    try:
        resp = requests.delete(
            f"{API_BASE_URL}/api/employee/{employee_id}/data",
            headers=_headers(token),
            timeout=TIMEOUT,
        )
    except requests.ConnectionError as exc:
        raise ApiError(f"Could not connect to API at {API_BASE_URL}") from exc

    if not resp.ok:
        raise ApiError(f"Failed to delete your data: {resp.text}", status_code=resp.status_code)

    return _unwrap(resp)
