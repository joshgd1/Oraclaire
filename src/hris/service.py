"""
HRIS service — factory that selects and returns the configured HRIS adapter.

The adapter is selected based on environment variables:
  HRIS_PROVIDER=workday   → WorkdayAdapter
  HRIS_PROVIDER=bamboo   → BambooHRAdapter
  HRIS_PROVIDER=manual   → ManualAdapter (default / fallback)
"""

from __future__ import annotations

import os

from src.hris import BambooHRAdapter, HRISAdapter, ManualAdapter, WorkdayAdapter


def get_hris_adapter() -> HRISAdapter:
    """
    Return the configured HRIS adapter based on HRIS_PROVIDER env var.

    Priority:
      1. WORKDAY  — if WORKDAY_API_URL is set
      2. BAMBOO   — if BAMBOO_SUBDOMAIN is set
      3. MANUAL   — always available fallback
    """
    provider = os.environ.get("HRIS_PROVIDER", "").lower()

    if provider == "workday":
        return WorkdayAdapter()
    if provider == "bamboo":
        return BambooHRAdapter()
    if provider == "manual":
        return ManualAdapter()

    # Auto-detect: check if any provider is configured
    if os.environ.get("WORKDAY_API_URL"):
        return WorkdayAdapter()
    if os.environ.get("BAMBOO_SUBDOMAIN") and os.environ.get("BAMBOO_API_KEY"):
        return BambooHRAdapter()

    # Default to manual
    return ManualAdapter()
