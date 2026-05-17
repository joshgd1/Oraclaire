"""
HRIS Adapter — pluggable interface for HR system integration.

Architecture:
- Abstract base (HrisAdapter) defines the contract
- Concrete adapters: WorkdayAdapter, BambooHRAdapter, ManualInputAdapter
- Factory function (create_hris_adapter) instantiates based on env config

Adapters are read-only: they query HR data, never write.

Seniority mapping:
  junior  → 0.0
  senior  → 1.0

Exclusion categories returned match ExclusionCategory enum values.
"""

from __future__ import annotations

import csv
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

import requests

logger = logging.getLogger(__name__)


# ── Return types ────────────────────────────────────────────────────────────────


@dataclass
class SeniorityResult:
    tier: Literal[0.0, 1.0]  # 0=junior, 1=senior
    source: Literal["hris_derived"]


@dataclass
class ExclusionResult:
    excluded: bool
    category: str | None  # ExclusionCategory enum value or None
    notes: str | None = None


@dataclass
class TeamMembershipResult:
    team_name: str
    department_name: str
    manager_employee_id: int | None = None


# ── Abstract adapter ───────────────────────────────────────────────────────────


class HrisAdapter(ABC):
    """
    Abstract HRIS adapter. All concrete adapters MUST implement every method.

    Methods return None when the HR system does not have a record for the
    employee or when the adapter is unavailable (network error, etc.).
    The caller handles None by falling back to manual input.
    """

    name: str = "abstract"

    @abstractmethod
    def get_seniority(self, employee_id: int) -> SeniorityResult | None:
        """Return seniority tier for an employee, or None if unknown."""

    @abstractmethod
    def get_exclusion_status(
        self, employee_id: int
    ) -> ExclusionResult | None:
        """
        Return exclusion status for an employee, or None if no exclusion record
        exists in the HR system.
        """

    @abstractmethod
    def get_team_membership(
        self, employee_id: int
    ) -> TeamMembershipResult | None:
        """Return team/department membership for an employee, or None."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the adapter is reachable and authenticated."""

    def close(self) -> None:
        """Optional cleanup. Default no-op."""
        pass


# ── Workday Adapter (stub) ─────────────────────────────────────────────────────


class WorkdayAdapter(HrisAdapter):
    """
    Workday REST API adapter.

    Required env vars:
      WORKDAY_API_URL   — e.g. https://wd3-impl.workday.com/ccx/api/v1/{tenant}
      WORKDAY_CLIENT_ID — OAuth2 client ID
      WORKDAY_CLIENT_SECRET — OAuth2 client secret

    Seniority heuristic: jobLevel / jobLevelType mapped to junior (1-5) / senior (6+).
    """

    name = "workday"

    def __init__(self) -> None:
        self._base_url = os.environ.get("WORKDAY_API_URL", "").rstrip("/")
        self._client_id = os.environ.get("WORKDAY_CLIENT_ID", "")
        self._client_secret = os.environ.get("WORKDAY_CLIENT_SECRET", "")
        self._token: str | None = None

    def _get_token(self) -> str | None:
        """OAuth2 client credentials flow."""
        if not self._base_url or not self._client_id or not self._client_secret:
            return None
        token_url = f"{self._base_url}/oauth2/token"
        try:
            resp = requests.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                timeout=10,
            )
            if resp.ok:
                self._token = resp.json().get("access_token")
                return self._token
        except Exception as exc:
            logger.warning("workday.token.error", error=str(exc))
        return None

    def _headers(self) -> dict[str, str]:
        token = self._token or self._get_token()
        return {"Authorization": f"Bearer {token}"} if token else {}

    def get_seniority(self, employee_id: int) -> SeniorityResult | None:
        url = f"{self._base_url}/workers/{employee_id}"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=10)
            if not resp.ok:
                return None
            data = resp.json()
            job_level = data.get("businessTitle", "")
            # Heuristic: job level extracted from job title suffix like "L5" or "Grade 6"
            import re
            m = re.search(r"\b(L\d+|Grade\s*(\d+))\b", str(job_level), re.IGNORECASE)
            if m:
                level = int(re.sub(r"[^\d]", "", m.group(0)))
                return SeniorityResult(tier=1.0 if level >= 6 else 0.0, source="hris_derived")
        except Exception as exc:
            logger.warning("workday.seniority.error", employee_id=employee_id, error=str(exc))
        return None

    def get_exclusion_status(self, employee_id: int) -> ExclusionResult | None:
        # Workday does not have a standard exclusion field; integrate with
        # specific Workday business processes (PTO, leave, incidents) as needed.
        return None

    def get_team_membership(self, employee_id: int) -> TeamMembershipResult | None:
        url = f"{self._base_url}/workers/{employee_id}"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=10)
            if not resp.ok:
                return None
            data = resp.json()
            return TeamMembershipResult(
                team_name=data.get("supervisoryOrganization", {}).get("name", ""),
                department_name=data.get("businessTitle", ""),
                manager_employee_id=None,
            )
        except Exception as exc:
            logger.warning("workday.team.error", employee_id=employee_id, error=str(exc))
        return None

    def health_check(self) -> bool:
        return self._get_token() is not None


# ── BambooHR Adapter ───────────────────────────────────────────────────────────


class BambooHRAdapter(HrisAdapter):
    """
    BambooHR REST API adapter.

    Required env vars:
      BAMBOOHR_API_KEY  — found at BambooHR → Settings → API Key
      BAMBOOHR_DOMAIN   — your company subdomain, e.g. "acme" for acme.bamboohr.com

    Seniority: mapped from the employee's "jobTitle" field. Titles containing
    "senior", "lead", "principal", "director", "vp", "chief" → senior (1.0).
    Titles containing "intern", "junior", "associate" → junior (0.0).
    Default: junior (0.0) when no heuristic matches.
    """

    name = "bamboohr"

    SENIOR_KEYWORDS = {
        "senior", "lead", "principal", "director", "vp", "chief",
        "head of", "manager", "architect", "staff",
    }
    JUNIOR_KEYWORDS = {"intern", "junior", "associate", "trainee", "entry"}

    def __init__(self) -> None:
        self._api_key = os.environ.get("BAMBOOHR_API_KEY", "")
        self._domain = os.environ.get("BAMBOOHR_DOMAIN", "")
        self._base_url = f"https://api.bamboohr.com/api/gateway.php/{self._domain}/v1"
        self._headers = {
            "Authorization": f"Basic {self._api_key}",
            "Accept": "application/json",
        }

    def _employee_url(self, employee_id: str, fields: str = "") -> str:
        path = f"/employees/{employee_id}"
        if fields:
            path += f"?fields={fields}"
        return self._base_url + path

    def _get_field(self, employee_id: str, field: str) -> str | None:
        url = self._employee_url(employee_id, fields=field)
        try:
            resp = requests.get(url, headers=self._headers, timeout=10)
            if resp.ok:
                data = resp.json()
                return data.get("field", {}).get(field) or data.get(field)
        except Exception as exc:
            logger.warning("bamboohr.field.error", employee_id=employee_id, field=field, error=str(exc))
        return None

    def _get_employees_list(self) -> list[dict] | None:
        """Fetch all employees summary — used for lookup."""
        url = self._base_url + "/employees/directory"
        try:
            resp = requests.get(url, headers=self._headers, timeout=15)
            if resp.ok:
                return resp.json().get("employees", [])
        except Exception as exc:
            logger.warning("bamboohr.directory.error", error=str(exc))
        return None

    def get_seniority(self, employee_id: int) -> SeniorityResult | None:
        title = self._get_field(str(employee_id), "jobTitle")
        if not title:
            return None
        title_lower = title.lower()
        if any(kw in title_lower for kw in self.SENIOR_KEYWORDS):
            return SeniorityResult(tier=1.0, source="hris_derived")
        if any(kw in title_lower for kw in self.JUNIOR_KEYWORDS):
            return SeniorityResult(tier=0.0, source="hris_derived")
        # Default: junior
        return SeniorityResult(tier=0.0, source="hris_derived")

    def get_exclusion_status(self, employee_id: int) -> ExclusionResult | None:
        # BambooHR does not have standard exclusion fields by default.
        # Integration with BambooHR leave/absence data can be added here.
        return None

    def get_team_membership(self, employee_id: int) -> TeamMembershipResult | None:
        department = self._get_field(employee_id, "department") or ""
        job_title = self._get_field(employee_id, "jobTitle") or ""
        # Supervisor ID could be wired here if BambooHR stores it
        return TeamMembershipResult(
            team_name=department,
            department_name=department,
            manager_employee_id=None,
        )

    def health_check(self) -> bool:
        url = self._base_url + "/employees/directory"
        try:
            resp = requests.get(url, headers=self._headers, timeout=10)
            return resp.ok
        except Exception:
            return False


# ── Manual / CSV Adapter ──────────────────────────────────────────────────────


class ManualInputAdapter(HrisAdapter):
    """
    CSV-based adapter for demo mode and manual HR data entry.

    Expects a CSV at data/hris/manual_employees.csv with columns:
      employee_id, seniority_tier, team_name, department_name, excluded, exclusion_category

    All fields optional — missing = None.

    Exclusion category values: pip, ada, fmla, workers_comp, disciplinary,
    grievance_cooldown, medical_leave, active_intervention, contractor, test_account
    """

    name = "manual"
    CSV_PATH = Path("data/hris/manual_employees.csv")

    def __init__(self) -> None:
        self._cache: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if not self.CSV_PATH.exists():
            return
        try:
            with open(self.CSV_PATH, newline="") as fh:
                for row in csv.DictReader(fh):
                    eid = row.get("employee_id", "").strip()
                    if eid:
                        self._cache[eid] = row
        except Exception as exc:
            logger.warning("manual_hris.load.error", path=str(self.CSV_PATH), error=str(exc))

    def _get_row(self, employee_id: str) -> dict | None:
        return self._cache.get(str(employee_id))

    def get_seniority(self, employee_id: int) -> SeniorityResult | None:
        row = self._get_row(str(employee_id))
        if row is None:
            return None
        tier_str = row.get("seniority_tier", "").strip().lower()
        if tier_str in ("1", "1.0", "senior"):
            return SeniorityResult(tier=1.0, source="hris_derived")
        if tier_str in ("0", "0.0", "junior"):
            return SeniorityResult(tier=0.0, source="hris_derived")
        return None

    def get_exclusion_status(self, employee_id: int) -> ExclusionResult | None:
        row = self._get_row(str(employee_id))
        if row is None:
            return None
        excluded_str = row.get("excluded", "").strip().lower()
        if excluded_str in ("true", "1", "yes", "excluded"):
            category = row.get("exclusion_category", "").strip().lower()
            return ExclusionResult(
                excluded=True,
                category=category or None,
                notes=row.get("notes", "").strip() or None,
            )
        return ExclusionResult(excluded=False, category=None)

    def get_team_membership(self, employee_id: int) -> TeamMembershipResult | None:
        row = self._get_row(str(employee_id))
        if row is None:
            return None
        return TeamMembershipResult(
            team_name=row.get("team_name", "").strip(),
            department_name=row.get("department_name", "").strip(),
            manager_employee_id=None,
        )

    def health_check(self) -> bool:
        # Manual adapter is always available (local CSV)
        return True

    def reload(self) -> None:
        """Re-read the CSV file (call after manual edits)."""
        self._cache.clear()
        self._load()


# ── Factory ────────────────────────────────────────────────────────────────────


_ADAPTERS: dict[str, type[HrisAdapter]] = {
    "workday": WorkdayAdapter,
    "bamboohr": BambooHRAdapter,
    "manual": ManualInputAdapter,
}


def create_hris_adapter(
    adapter_name: str | None = None,
) -> HrisAdapter:
    """
    Instantiate the HRIS adapter specified by ADAPTER_NAME env var
    (or the adapter_name argument).

    Falls back to ManualInputAdapter if the named adapter cannot be imported
    or has no credentials configured.
    """
    name = adapter_name or os.environ.get("ADAPTER_NAME", "manual").lower()

    cls = _ADAPTERS.get(name)
    if cls is None:
        logger.warning("hris.unknown_adapter", name=name, fallback="manual")
        return ManualInputAdapter()

    try:
        adapter = cls()
        # Verify it at least starts up (credentials present)
        if hasattr(adapter, "_api_key") and not getattr(adapter, "_api_key", ""):
            logger.warning("hris.no_credentials", adapter=name, fallback="manual")
            return ManualInputAdapter()
        return adapter
    except Exception as exc:
        logger.warning("hris.adapter_init.error", adapter=name, error=str(exc), fallback="manual")
        return ManualInputAdapter()


# ── Sentinel when no adapter configured ────────────────────────────────────────


class NoOpAdapter(HrisAdapter):
    """Returned when ORACLAIRE_HRIS_ENABLED=false."""

    name = "none"

    def get_seniority(self, employee_id: int) -> SeniorityResult | None:
        return None

    def get_exclusion_status(self, employee_id: int) -> ExclusionResult | None:
        return None

    def get_team_membership(self, employee_id: int) -> TeamMembershipResult | None:
        return None

    def health_check(self) -> bool:
        return True
