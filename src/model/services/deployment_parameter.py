"""
DeploymentParameterService — admin CRUD for deployment parameters.

Provides typed accessors so callers don't need to know whether a parameter
is stored as int, float, or string — the service handles the coercion.

All methods accept organisation_id as the first argument, enforcing
tenant isolation at the service layer.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.model.entities import DeploymentParameter
from src.model.entities._db import get_session_factory


# Default values per M1-07 spec
_DEFAULTS: dict[str, Any] = {
    "grievance_cooldown_days": 90,
    "auto_flag_ceiling_pct": 20,
    "auto_flag_trigger_consecutive_weeks": 2,
    "participation_target_sprint1": 0.20,
    "participation_target_architecture": 0.40,
    "seniority_default_source": "hris_derived",
    "retention_months": 12,
}


class DeploymentParameterService:
    """CRUD service for per-organisation deployment parameters."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── read ────────────────────────────────────────────────────────────────

    def get(self, organisation_id: int, key: str) -> DeploymentParameter | None:
        """Return a single parameter, or None if not set."""
        return (
            self._session.query(DeploymentParameter)
            .filter(
                DeploymentParameter.organisation_id == organisation_id,
                DeploymentParameter.key == key,
            )
            .first()
        )

    def get_typed(
        self, organisation_id: int, key: str
    ) -> int | float | bool | str | None:
        """Return the parameter value coerced to its Python type, or None."""
        param = self.get(organisation_id, key)
        if param is None:
            default = _DEFAULTS.get(key)
            if default is not None:
                return default
            return None
        # Coerce to the type implied by the default
        default = _DEFAULTS.get(key)
        if isinstance(default, bool):
            return param.bool_value()
        if isinstance(default, int):
            return param.int_value()
        if isinstance(default, float):
            return param.float_value()
        return param.value

    def get_all(self, organisation_id: int) -> dict[str, Any]:
        """Return all parameters for an org, falling back to defaults for missing."""
        rows = (
            self._session.query(DeploymentParameter)
            .filter(DeploymentParameter.organisation_id == organisation_id)
            .all()
        )
        result = dict(_DEFAULTS)  # start with defaults
        for row in rows:
            default = _DEFAULTS.get(row.key)
            if isinstance(default, bool):
                result[row.key] = row.bool_value()
            elif isinstance(default, int):
                result[row.key] = row.int_value()
            elif isinstance(default, float):
                result[row.key] = row.float_value()
            else:
                result[row.key] = row.value
        return result

    # ── write ─────────────────────────────────────────────────────────────

    def set(
        self, organisation_id: int, key: str, value: int | float | bool | str
    ) -> DeploymentParameter:
        """Upsert a single parameter."""
        param = self.get(organisation_id, key)
        if param is None:
            param = DeploymentParameter(
                organisation_id=organisation_id,
                key=key,
                value=str(value),
            )
            self._session.add(param)
        else:
            param.value = str(value)
        self._session.flush()
        return param

    def bulk_upsert(
        self, organisation_id: int, params: dict[str, int | float | bool | str]
    ) -> list[DeploymentParameter]:
        """Upsert multiple parameters in one transaction."""
        results = []
        for key, value in params.items():
            results.append(self.set(organisation_id, key, value))
        return results

    def delete(self, organisation_id: int, key: str) -> bool:
        """Delete a parameter. Returns True if it existed, False if not."""
        param = self.get(organisation_id, key)
        if param is None:
            return False
        self._session.delete(param)
        self._session.flush()
        return True

    def reset_to_defaults(self, organisation_id: int) -> list[DeploymentParameter]:
        """Delete all custom parameters for an org, restoring defaults."""
        self._session.query(DeploymentParameter).filter(
            DeploymentParameter.organisation_id == organisation_id
        ).delete()
        self._session.flush()
        # Return the effective parameters (defaults)
        return [
            DeploymentParameter(organisation_id=organisation_id, key=k, value=str(v))
            for v, k in [(v, k) for k, v in _DEFAULTS.items()]
        ]

    # ── context manager ────────────────────────────────────────────────────

    @classmethod
    def using(cls) -> "DeploymentParameterService":
        """Create a service backed by a session from the factory."""
        factory = get_session_factory()
        session = factory()
        return cls(session)

    def close(self) -> None:
        self._session.close()
