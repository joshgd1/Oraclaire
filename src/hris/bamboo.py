"""
BambooHR adapter.

Fetches employee data via the BambooHR REST API.
BambooHR does not have a native leave-status field; this adapter
uses time-off requests and employment history as proxies.
"""

from __future__ import annotations

import os
from typing import Any

import structlog

from src.hris.base import EmployeeRecord, HRISAdapter

logger = structlog.get_logger(__name__)


class BambooHRAdapter(HRISAdapter):
    """
    BambooHR REST API adapter.

    Required environment variables:
      BAMBOO_API_KEY  — BambooHR API key
      BAMBOO_SUBDOMAIN — e.g. "mycompany" (results in api.bamboohr.com)
      BAMBOO_TIMEOUT   — request timeout in seconds (default 30)
    """

    def __init__(
        self,
        api_key: str | None = None,
        subdomain: str | None = None,
        timeout: int = 30,
    ) -> None:
        self._api_key = api_key or os.environ.get("BAMBOO_API_KEY", "")
        self._subdomain = subdomain or os.environ.get("BAMBOO_SUBDOMAIN", "")
        self._timeout = timeout
        self._base_url = f"https://api.bamboohr.com/api/gateway.php/{self._subdomain}/v1"

    @property
    def provider_name(self) -> str:
        return "BambooHR"

    def is_available(self) -> bool:
        if not self._api_key or not self._subdomain:
            logger.warning("bamboo.not_configured")
            return False
        return True

    def fetch_employees(self, organisation_id: int) -> list[EmployeeRecord]:
        """
        Fetch all employees from BambooHR.

        Uses /employees/directory endpoint and maps:
          id            -> external_id
          status        -> "employee" | "contractor" | "inactive"
          employmentHistory -> contract_type
        """
        import requests

        records: list[EmployeeRecord] = []
        try:
            resp = requests.get(
                f"{self._base_url}/employees/directory",
                headers={"Accept": "application/json"},
                auth=(self._api_key, ""),
                timeout=self._timeout,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.error("bamboo.fetch_employees.failed", error=str(exc))
            return records

        data = resp.json()
        employees: list[dict[str, Any]] = data.get("employees", [])

        for emp in employees:
            emp_id = str(emp.get("id", ""))
            status = str(emp.get("status", "Active")).lower()

            if status == "contractor":
                contract_type = "contractor"
            elif status in ("inactive", "archived"):
                contract_type = "test"  # treat inactive as test/non-scoring
            else:
                contract_type = "employee"

            records.append(
                EmployeeRecord(
                    employee_id=0,
                    external_id=emp_id,
                    leave_status=[],
                    contract_type=contract_type,
                    disciplinary_active=False,
                    grievance_active=False,
                    active_intervention=False,
                )
            )

        logger.info("bamboo.fetch_employees.ok", count=len(records))
        return records

    def fetch_leave_status(
        self, employee_external_ids: list[str]
    ) -> dict[str, list[str]]:
        """
        Fetch approved time-off requests as a proxy for active leave.

        BambooHR does not expose a leave-balance or leave-type flag;
        approved time-off in the current period is used as a proxy.
        """
        import requests
        from datetime import date

        results: dict[str, list[str]] = {eid: [] for eid in employee_external_ids}
        today = date.today()
        start_of_year = date(today.year, 1, 1)

        try:
            resp = requests.get(
                f"{self._base_url}/reports/time_off",
                params={
                    "end": today.isoformat(),
                    "start": start_of_year.isoformat(),
                    "type": "ACCURAL_BALANCE",
                },
                headers={"Accept": "application/json"},
                auth=(self._api_key, ""),
                timeout=self._timeout,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.error("bamboo.fetch_leave_status.failed", error=str(exc))
            return results

        try:
            items = resp.json().get("employees", [])
        except Exception:
            return results

        for emp_item in items:
            emp_id = str(emp_item.get("employeeId", ""))
            if emp_id not in results:
                continue
            for entry in emp_item.get("timeOff", []):
                leave_type = str(entry.get("type", "")).lower()
                # Map common BambooHR leave types to our categories
                if leave_type in ("fmla", "family and medical leave"):
                    results[emp_id].append("fmla")
                elif leave_type in ("medical", "sick", "medical leave"):
                    results[emp_id].append("ada")
                elif leave_type in ("workers compensation", "workers comp"):
                    results[emp_id].append("workers_comp")

        return results
