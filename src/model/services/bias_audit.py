"""
BiasAuditService — M5-08.

Automated disparate impact analysis: runs after each scoring cycle to detect
whether any demographic slice has a materially different Critical+High rate
from the overall population.

Outputs an audit report JSON with flag + detail per slice.
Must run before each customer deployment.

Decision basis: cost-model.md §2 — FP in disadvantaged groups is
disproportionately costly (higher false-alarm burden, erosion of trust),
so the calibration target is precision not just recall.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import structlog

from src.model.entities import Employee, RiskScore
from src.model.entities._db import get_session_factory

log = structlog.get_logger(__name__)

# Maximum allowed pp difference before a group is flagged
DISPARATE_IMPACT_THRESHOLD_PP = 10.0


@dataclass
class SliceResult:
    """Result for one demographic slice."""

    slice_name: str
    slice_key: str  # e.g. "seniority_tier=1" or "company_type=Product"
    total: int
    hc_count: int  # high + critical
    hc_rate: float  # fraction
    rate_diff_pp: float  # difference from population mean in pp
    flagged: bool


@dataclass
class BiasAuditReport:
    """Full bias audit result for one scoring cycle."""

    cycle_id: int
    organisation_id: int
    generated_at: str
    population_total: int
    population_hc_rate: float
    slices: list[dict]
    any_flagged: bool
    flags: list[str]


class BiasAuditService:
    """
    Computes disparate impact metrics for a scored cycle.

    Slices evaluated:
      - Seniority tier (junior / senior)
      - Company type (Product / Service)
      - WFH setup (available / not available)

    A slice is flagged when its Critical+High rate differs from the
    population mean by more than DISPARATE_IMPACT_THRESHOLD_PP percentage points.
    """

    def __init__(self, session=None):
        self._session = session

    def audit(self, cycle_id: int, organisation_id: int) -> BiasAuditReport:
        """
        Run bias audit for one cycle.

        Returns a BiasAuditReport with per-slice results and a list of
        flag messages for any slices that exceed the disparate impact threshold.
        """
        factory = get_session_factory
        if self._session is None:
            session = factory()
            try:
                return self._audit(session, cycle_id, organisation_id)
            finally:
                session.close()
        else:
            return self._audit(self._session, cycle_id, organisation_id)

    def _audit(
        self, session, cycle_id: int, organisation_id: int
    ) -> BiasAuditReport:
        log.info(
            "bias_audit.start",
            cycle_id=cycle_id,
            organisation_id=organisation_id,
        )

        # ── Population rate ──────────────────────────────────────────────────
        total = session.query(Employee).filter(
            Employee.organisation_id == organisation_id,
            Employee.consent_status.name != "withdrawn",
            Employee.exclusion_status == False,  # noqa: E712
        ).count()

        if total == 0:
            report = BiasAuditReport(
                cycle_id=cycle_id,
                organisation_id=organisation_id,
                generated_at=datetime.now(UTC).isoformat(),
                population_total=0,
                population_hc_rate=0.0,
                slices=[],
                any_flagged=False,
                flags=[],
            )
            log.info("bias_audit.empty", cycle_id=cycle_id)
            return report

        hc_pop = session.query(RiskScore).join(
            Employee, RiskScore.employee_id == Employee.id
        ).filter(
            RiskScore.cycle_id == cycle_id,
            RiskScore.risk_tier.in_(("high", "critical")),
            Employee.organisation_id == organisation_id,
            Employee.consent_status.name != "withdrawn",
            Employee.exclusion_status == False,  # noqa: E712
        ).count()

        pop_hc_rate = hc_pop / total

        # ── Slice evaluation ──────────────────────────────────────────────────
        slice_definitions = [
            ("seniority_tier", "seniority_tier", {0: "junior", 1: "senior"}),
            ("company_type", "company_type", {"Product": "Product", "Service": "Service"}),
            ("wfh_setup", "wfh_setup_available", {True: "wfh_yes", False: "wfh_no"}),
        ]

        slice_results: list[SliceResult] = []
        flags: list[str] = []

        for slice_name, field, value_labels in slice_definitions:
            results = self._evaluate_slice(
                session=session,
                cycle_id=cycle_id,
                organisation_id=organisation_id,
                slice_name=slice_name,
                field=field,
                value_labels=value_labels,
                population_hc_rate=pop_hc_rate,
            )
            slice_results.extend(results)
            for r in results:
                if r.flagged:
                    flags.append(
                        f"disparate_impact: {r.slice_name}={r.slice_key} "
                        f"(HC rate {r.hc_rate:.1%} vs population {pop_hc_rate:.1%}, "
                        f"diff {r.rate_diff_pp:+.1f}pp, threshold {DISPARATE_IMPACT_THRESHOLD_PP}pp)"
                    )

        any_flagged = len(flags) > 0

        log.info(
            "bias_audit.complete",
            cycle_id=cycle_id,
            slices=len(slice_results),
            flagged=any_flagged,
            flags=flags,
        )

        return BiasAuditReport(
            cycle_id=cycle_id,
            organisation_id=organisation_id,
            generated_at=datetime.now(UTC).isoformat(),
            population_total=total,
            population_hc_rate=round(pop_hc_rate, 4),
            slices=[asdict(r) for r in slice_results],
            any_flagged=any_flagged,
            flags=flags,
        )

    def _evaluate_slice(
        self,
        session,
        cycle_id: int,
        organisation_id: int,
        slice_name: str,
        field: str,
        value_labels: dict,
        population_hc_rate: float,
    ) -> list[SliceResult]:
        """Evaluate one demographic dimension, returning one SliceResult per value."""
        results = []

        for value, label in value_labels.items():
            if field == "seniority_tier":
                filter_clause = (
                    Employee.seniority_tier == value
                )
            elif field == "company_type":
                filter_clause = (
                    Employee.company_type == value
                )
            elif field == "wfh_setup_available":
                filter_clause = (
                    Employee.wfh_setup_available == value
                )
            else:
                continue

            total = session.query(Employee).filter(
                Employee.organisation_id == organisation_id,
                Employee.consent_status.name != "withdrawn",
                Employee.exclusion_status == False,  # noqa: E712
            ).filter(filter_clause).count()

            if total == 0:
                continue

            hc_count = session.query(RiskScore).join(
                Employee, RiskScore.employee_id == Employee.id
            ).filter(
                RiskScore.cycle_id == cycle_id,
                RiskScore.risk_tier.in_(("high", "critical")),
                Employee.organisation_id == organisation_id,
                Employee.consent_status.name != "withdrawn",
                Employee.exclusion_status == False,  # noqa: E712
            ).filter(filter_clause).count()

            hc_rate = hc_count / total
            rate_diff_pp = round((hc_rate - population_hc_rate) * 100, 2)
            flagged = abs(rate_diff_pp) > DISPARATE_IMPACT_THRESHOLD_PP

            results.append(SliceResult(
                slice_name=slice_name,
                slice_key=label,
                total=total,
                hc_count=hc_count,
                hc_rate=round(hc_rate, 4),
                rate_diff_pp=rate_diff_pp,
                flagged=flagged,
            ))

        return results

    @classmethod
    def for_cycle(
        cls, cycle_id: int, organisation_id: int
    ) -> BiasAuditReport:
        """Convenience: run bias audit for one cycle."""
        return cls().audit(cycle_id, organisation_id)
