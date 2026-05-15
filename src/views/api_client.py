"""
Oraclaire API client for Streamlit frontend.

Handles JWT authentication and calls to the Nexus API running at API_BASE_URL.
"""

from __future__ import annotations

import os
from typing import Any

import requests

API_BASE_URL = os.environ.get("NEXUS_API_BASE_URL", "http://localhost:8000")
TIMEOUT = 10.0


class ApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


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

    data = resp.json()
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

    return resp.json()


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

    return resp.json()


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

    return resp.json()


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

    return resp.json()


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

    return resp.json()


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

    return resp.json()


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

    return resp.json()


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

    return resp.json()
