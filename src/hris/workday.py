"""
Workday HRIS adapter.

Fetches employee data via the Workday REST API (Tenant-Specific Domain).
Maps Worker IDs to Exclusion records using the abstract base interface.
"""

from __future__ import annotations

import os
from typing import Any

import structlog

from src.hris.base import EmployeeRecord, HRISAdapter

logger = structlog.get_logger(__name__)


class WorkdayAdapter(HRISAdapter):
    """
    Workday REST API adapter.

    Required environment variables:
      WORKDAY_API_URL   — e.g. https://wd2-impl-services1.workday.com/ccx/api/v1/<tenant>/ptd
      WORKDAY_API_KEY   — API key or OAuth bearer token
      WORKDAY_TIMEOUT   — request timeout in seconds (default 30)
    """

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        timeout: int = 30,
    ) -> None:
        self._api_url = api_url or os.environ.get("WORKDAY_API_URL", "")
        self._api_key = api_key or os.environ.get("WORKDAY_API_KEY", "")
        self._timeout = timeout

    @property
    def provider_name(self) -> str:
        return "Workday"

    def is_available(self) -> bool:
        if not self._api_url or not self._api_key:
            logger.warning("workday.not_configured")
            return False
        # Lightweight connectivity check — just verify credentials parse
        return True

    def fetch_employees(self, organisation_id: int) -> list[EmployeeRecord]:
        """
        Fetch all workers from Workday.

        Uses the Workers v1 endpoint.  Maps:
          Worker.id            -> external_id
          Worker.status        -> contract_type ("employee" | "contractor")
          Worker.leaveStatus  -> leave_status (list of leave type strings)
        """
        import requests

        records: list[EmployeeRecord] = []
        page = 1
        limit = 100

        while True:
            try:
                resp = requests.get(
                    f"{self._api_url}/workers",
                    params={"page": page, "limit": limit},
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=self._timeout,
                )
                resp.raise_for_status()
            except Exception as exc:
                logger.error("workday.fetch_workers.failed", error=str(exc))
                break

            data = resp.json()
            workers: list[dict[str, Any]] = data.get("data", [])

            if not workers:
                break

            for w in workers:
                status = w.get("worker_status", "")
                leave_status_raw = w.get("leave_status", []) or []
                leave_types = [str(lt).lower() for lt in leave_status_raw]

                records.append(
                    EmployeeRecord(
                        employee_id=0,  # mapped via employee_mapping
                        external_id=str(w.get("id", "")),
                        leave_status=leave_types,
                        contract_type=(
                            "contractor"
                            if status.lower() == "contractor"
                            else "employee"
                        ),
                        disciplinary_active=bool(w.get("disciplinary_active")),
                        grievance_active=bool(w.get("grievance_active")),
                        active_intervention=bool(w.get("active_intervention")),
                    )
                )

            # Pagination
            total = data.get("total", 0)
            if page * limit >= total:
                break
            page += 1

        logger.info("workday.fetch_employees.ok", count=len(records))
        return records

    def fetch_leave_status(
        self, employee_external_ids: list[str]
    ) -> dict[str, list[str]]:
        """
        Fetch active leave for specific workers from Workday Time Off module.

        Returns dict mapping worker_id -> list of leave type strings.
        """
        import requests

        if not employee_external_ids:
            return {}

        results: dict[str, list[str]] = {eid: [] for eid in employee_external_ids}

        try:
            resp = requests.post(
                f"{self._api_url}/time_off/balances",
                json={"worker_ids": employee_external_ids},
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self._timeout,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.error("workday.fetch_leave_status.failed", error=str(exc))
            return results

        data = resp.json()
        for item in data.get("balances", []):
            wid = str(item.get("worker_id", ""))
            if wid not in results:
                continue
            leave_type = str(item.get("leave_type", "")).lower()
            if item.get("has_active_leave"):
                results[wid].append(leave_type)

        return results
