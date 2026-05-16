"""
Jurisdictional Gating Service.

Determines which regulatory requirements apply based on the jurisdiction of
the data subjects (employees) and the data controller (customer organisation).
Generates gating signals that determine which features are enabled/disabled
for a given organisation or assessment cycle.

Supported jurisdictions:
- EU/EEA member states: EU AI Act + GDPR + local employment law
  (e.g., German BetrVG works council co-determination, French CSE consultation)
- Singapore: PDPA + Ministry of Manpower guidelines
- United States: State-level privacy laws (CCPA/CPRA California, etc.)
- Other: assessed case-by-case

The service does NOT provide legal advice. Output is used to gate features
and surface requirements to HR administrators for human action.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Jurisdiction(str, Enum):
    EU = "eu"
    SINGAPORE = "singapore"
    USA = "usa"
    OTHER = "other"


class RegulatoryRequirement(str, Enum):
    # EU
    WORKS_COUNCIL_CONSULTATION = "works_council_consultation"
    EU_AI_ACT_NOTICE = "eu_ai_act_notice"
    GDPR_CONSENT = "gdpr_consent"
    DPIA_COMPLETION = "dpia_completion"

    # Singapore
    PDPA_CONSENT = "pdpa_consent"
    PDPA_NOTIFICATION = "pdpa_notification"

    # USA
    CCPA_CONSUMER_DISCLOSURE = "ccpa_consumer_disclosure"
    STATE_PRIVACY_NOTICE = "state_privacy_notice"

    # General
    DATA_RETENTION_POLICY = "data_retention_policy"


@dataclass
class JurisdictionProfile:
    """Describes the regulatory profile for a given jurisdiction."""

    jurisdiction: Jurisdiction
    country_code: str  # ISO 3166-1 alpha-2
    sub_jurisdiction: str | None = None  # e.g., "DE-BY" for Bavaria

    # EU-specific
    is_eu: bool = False
    requires_works_council: bool = False
    works_council_threshold: int | None = None  # Employee count that triggers co-determination

    # Singapore-specific
    is_singapore: bool = False
    pdpa_applies: bool = False

    # USA-specific
    is_usa: bool = False
    state_code: str | None = None
    ccpa_applies: bool = False

    # General
    requires_dpia: bool = False
    requires_privacy_notice: bool = False


@dataclass
class GatingRequirement:
    """A single gating requirement with its current status."""

    requirement: RegulatoryRequirement
    description: str
    status: str  # "met" | "pending" | "not_applicable" | "blocked"
    action_required: str | None = None  # Plain-language description of what HR must do
    regulation_reference: str | None = None  # e.g., "GDPR Art. 35", "BetrVG §87"


@dataclass
class GatingReport:
    """Complete gating assessment for an organisation or cycle."""

    organisation_id: int
    jurisdiction_profile: JurisdictionProfile
    requirements: list[GatingRequirement]

    @property
    def is_clear(self) -> bool:
        """Return True if all applicable requirements are met."""
        return all(r.status != "blocked" for r in self.requirements)

    @property
    def blocked_requirements(self) -> list[GatingRequirement]:
        return [r for r in self.requirements if r.status == "blocked"]

    @property
    def pending_requirements(self) -> list[GatingRequirement]:
        return [r for r in self.requirements if r.status == "pending"]

    @property
    def action_required(self) -> list[GatingRequirement]:
        return [r for r in self.requirements if r.status in ("blocked", "pending")]


# Country → JurisdictionProfile lookup
_JURISDICTION_MAP: dict[str, JurisdictionProfile] = {
    # EU member states
    "AT": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="AT", is_eu=True, requires_works_council=True, works_council_threshold=5),
    "BE": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="BE", is_eu=True, requires_works_council=True, works_council_threshold=50),
    "BG": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="BG", is_eu=True, requires_works_council=False, requires_dpia=True),
    "HR": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="HR", is_eu=True, requires_works_council=True, works_council_threshold=20),
    "CY": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="CY", is_eu=True, requires_works_council=False),
    "CZ": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="CZ", is_eu=True, requires_works_council=True, works_council_threshold=25),
    "DK": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="DK", is_eu=True, requires_works_council=True, works_council_threshold=35),
    "EE": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="EE", is_eu=True, requires_works_council=False),
    "FI": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="FI", is_eu=True, requires_works_council=True, works_council_threshold=30),
    "FR": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="FR", is_eu=True, requires_works_council=True, works_council_threshold=11),
    "DE": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="DE", is_eu=True, requires_works_council=True, works_council_threshold=5),
    "GR": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="GR", is_eu=True, requires_works_council=True, works_council_threshold=50),
    "HU": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="HU", is_eu=True, requires_works_council=True, works_council_threshold=50),
    "IE": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="IE", is_eu=True, requires_works_council=False),
    "IT": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="IT", is_eu=True, requires_works_council=True, works_council_threshold=15),
    "LV": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="LV", is_eu=True, requires_works_council=False),
    "LT": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="LT", is_eu=True, requires_works_council=True, works_council_threshold=20),
    "LU": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="LU", is_eu=True, requires_works_council=True, works_council_threshold=15),
    "MT": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="MT", is_eu=True, requires_works_council=False),
    "NL": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="NL", is_eu=True, requires_works_council=True, works_council_threshold=50),
    "PL": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="PL", is_eu=True, requires_works_council=True, works_council_threshold=50),
    "PT": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="PT", is_eu=True, requires_works_council=True, works_council_threshold=10),
    "RO": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="RO", is_eu=True, requires_works_council=True, works_council_threshold=20),
    "SK": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="SK", is_eu=True, requires_works_council=True, works_council_threshold=20),
    "SI": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="SI", is_eu=True, requires_works_council=True, works_council_threshold=20),
    "ES": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="ES", is_eu=True, requires_works_council=True, works_council_threshold=10),
    "SE": JurisdictionProfile(jurisdiction=Jurisdiction.EU, country_code="SE", is_eu=True, requires_works_council=False),  # Swedish system different

    # Singapore
    "SG": JurisdictionProfile(jurisdiction=Jurisdiction.SINGAPORE, country_code="SG", is_singapore=True, pdpa_applies=True, requires_privacy_notice=True),

    # USA (state-level)
    "US": JurisdictionProfile(jurisdiction=Jurisdiction.USA, country_code="US", is_usa=True),

    # Catch-all
    "OTHER": JurisdictionProfile(jurisdiction=Jurisdiction.OTHER, country_code="OTHER"),
}


def get_jurisdiction_profile(country_code: str, state_code: str | None = None) -> JurisdictionProfile:
    """Return the JurisdictionProfile for a given country code (ISO 3166-1 alpha-2)."""
    profile = _JURISDICTION_MAP.get(country_code.upper())
    if profile is None:
        return JurisdictionProfile(jurisdiction=Jurisdiction.OTHER, country_code=country_code)
    return profile


def _build_eu_requirements(profile: JurisdictionProfile, employee_count: int) -> list[GatingRequirement]:
    """Build EU-specific requirements."""
    reqs = []

    # EU AI Act notice
    reqs.append(GatingRequirement(
        requirement=RegulatoryRequirement.EU_AI_ACT_NOTICE,
        description="Employees must be informed that they are subject to an AI system classification under the EU AI Act",
        status="pending",
        action_required="Display EU AI Act notice to all employees before first assessment",
        regulation_reference="EU AI Act (2024/1689) — high-risk system transparency requirement",
    ))

    # GDPR consent / legitimate interest
    reqs.append(GatingRequirement(
        requirement=RegulatoryRequirement.GDPR_CONSENT,
        description="Lawful basis for processing employee health-related data must be established",
        status="pending",
        action_required="Establish legal basis (legitimate interest or employment law basis under GDPR Art. 9(2)(b)) and notify employees",
        regulation_reference="GDPR Art. 9(2)(b) — employment, occupational medicine",
    ))

    # DPIA (required for high-risk processing under GDPR Art. 35)
    reqs.append(GatingRequirement(
        requirement=RegulatoryRequirement.DPIA_COMPLETION,
        description="Data Protection Impact Assessment must be completed before processing begins",
        status="pending",
        action_required="Complete DPIA using the Oraclaire DPIA template and obtain DPO sign-off",
        regulation_reference="GDPR Art. 35 — DPIA required for systematic monitoring of employees",
    ))

    # Works council
    if profile.requires_works_council:
        threshold = profile.works_council_threshold or 0
        reqs.append(GatingRequirement(
            requirement=RegulatoryRequirement.WORKS_COUNCIL_CONSULTATION,
            description=f"Werksrat / CSE / employee representative body must be consulted before deployment",
            status="pending" if employee_count >= threshold else "not_applicable",
            action_required=(
                f"Consult with works council / CSE / employee representatives "
                f"(required in {profile.country_code} for organisations with {threshold}+ employees)"
                if employee_count >= threshold else None
            ),
            regulation_reference=f"{profile.country_code} local employment law — co-determination rights",
        ))

    return reqs


def _build_singapore_requirements(profile: JurisdictionProfile) -> list[GatingRequirement]:
    """Build Singapore PDPA-specific requirements."""
    reqs = []

    if profile.pdpa_applies:
        reqs.append(GatingRequirement(
            requirement=RegulatoryRequirement.PDPA_CONSENT,
            description="PDPA consent must be obtained from employees before collecting health-related personal data",
            status="pending",
            action_required="Ensure employees have been notified of the purpose of data collection and have consented",
            regulation_reference="PDPA 2012 (Act 26 of 2012) — consent obligation for personal data",
        ))

        reqs.append(GatingRequirement(
            requirement=RegulatoryRequirement.PDPA_NOTIFICATION,
            description="Employees must be notified of the PDPA data collection under the mandatory notification obligation",
            status="pending",
            action_required="Display PDPA notification (organisation name, purpose, data contact) to all employees",
            regulation_reference="PDPA 2012 — notification obligation",
        ))

    return reqs


def _build_usa_requirements(profile: JurisdictionProfile) -> list[GatingRequirement]:
    """Build USA state-level requirements."""
    reqs = []

    if profile.ccpa_applies:
        reqs.append(GatingRequirement(
            requirement=RegulatoryRequirement.CCPA_CONSUMER_DISCLOSURE,
            description="California Consumer Privacy Act disclosure must be provided",
            status="pending",
            action_required="Update privacy policy to include CCPA-required disclosures for California residents",
            regulation_reference="CCPA / CPRA (California Civil Code §1798.100 et seq.)",
        ))

    reqs.append(GatingRequirement(
        requirement=RegulatoryRequirement.STATE_PRIVACY_NOTICE,
        description="State-level privacy notice may be required depending on employee count and revenue",
        status="pending",
        action_required="Assess whether applicable state privacy law (e.g., CCPA, VCDPA, CPA) requires a specific employee notice",
        regulation_reference="Applicable state privacy law",
    ))

    return reqs


class JurisdictionalGatingService:
    """
    Generates gating reports for an organisation based on its jurisdiction
    and the number of employees.

    Usage:
        report = JurisdictionalGatingService.for_organisation(
            organisation_id=1,
            country_code="DE",
            employee_count=120,
        )
        if not report.is_clear:
            for req in report.action_required:
                print(f"Action needed: {req.action_required}")
    """

    def __init__(
        self,
        organisation_id: int,
        country_code: str,
        employee_count: int,
        state_code: str | None = None,
    ):
        self.organisation_id = organisation_id
        self.profile = get_jurisdiction_profile(country_code, state_code)
        self.employee_count = employee_count

    @classmethod
    def for_organisation(
        cls,
        organisation_id: int,
        country_code: str,
        employee_count: int,
        state_code: str | None = None,
    ) -> GatingReport:
        """
        Factory: build a GatingReport for an organisation.
        """
        svc = cls(
            organisation_id=organisation_id,
            country_code=country_code,
            employee_count=employee_count,
            state_code=state_code,
        )
        return svc.build_report()

    def build_report(self) -> GatingReport:
        """Build the full gating report for this organisation."""
        requirements: list[GatingRequirement] = []

        if self.profile.is_eu:
            requirements.extend(_build_eu_requirements(self.profile, self.employee_count))

        if self.profile.is_singapore:
            requirements.extend(_build_singapore_requirements(self.profile))

        if self.profile.is_usa:
            requirements.extend(_build_usa_requirements(self.profile))

        # General requirements always apply
        requirements.append(GatingRequirement(
            requirement=RegulatoryRequirement.DATA_RETENTION_POLICY,
            description="A data retention policy must be defined and communicated to employees",
            status="pending",
            action_required="Define retention period for individual assessment data (default: 12 months) and notify employees",
            regulation_reference="GDPR Art. 5(1)(e) — storage limitation; PDPA s.25 — retention limitation",
        ))

        return GatingReport(
            organisation_id=self.organisation_id,
            jurisdiction_profile=self.profile,
            requirements=requirements,
        )
