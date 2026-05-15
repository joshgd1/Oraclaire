"""
Deployment parameter entity — key-value config scoped per Organisation.

Covers all configurable deployment parameters from D14/D15 and the build plan:
- grievance_cooldown_days (default 90)
- auto_flag_ceiling_pct (default 20)
- auto_flag_trigger_consecutive_weeks (default 2)
- participation_target_sprint1 (0.20)
- participation_target_architecture (0.40)
- seniority_default_source (hris_derived)
- retention_months (12)
- jurisdiction (SG/EU/US)
- min_team_size (5)
"""

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, OrganisationMixin


class DeploymentParameter(Base, TimestampMixin, OrganisationMixin):
    __tablename__ = "deployment_parameters"
    __table_args__ = (
        UniqueConstraint("organisation_id", "key", name="uq_deployment_param_org_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relations
    organisation = relationship("Organisation", back_populates="parameters")

    def int_value(self) -> int:
        return int(self.value)

    def float_value(self) -> float:
        return float(self.value)

    def bool_value(self) -> bool:
        return self.value.lower() in ("true", "1", "yes")
