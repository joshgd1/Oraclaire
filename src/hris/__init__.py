"""HRIS adapter layer for Oraclaire."""

from src.hris.base import HRISAdapter
from src.hris.workday import WorkdayAdapter
from src.hris.bamboo import BambooHRAdapter
from src.hris.manual import ManualAdapter

__all__ = [
    "HRISAdapter",
    "WorkdayAdapter",
    "BambooHRAdapter",
    "ManualAdapter",
]
