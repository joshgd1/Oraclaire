"""
CBI instrument service — Copenhagen Burnout Inventory scoring.

19-item CBI (Kristensen 2005):
  Items 1–6:    Personal Burnout (PB)
  Items 7–12:   Work-Related Burnout (WB)
  Items 13–17:  Client-Related Burnout (CB)  [scored 0 if not applicable]
  Items 18–19:  not part of the standard subscales

Scoring: each item 0–100. Subscale score = mean of non-missing items × (100/max).
Cut-points: PB ≥ 50, WB ≥ 50, CB ≥ 45 = high burnout on that subscale.

Reference: Kristensen, P., Borritz, M., Villadsen, E., & Christensen, K.
(2005). The Copenhagen Burnout Inventory. Work & Stress, 19(3), 192–207.
"""

from __future__ import annotations

from dataclasses import dataclass


# Item → subscale mapping
# PB: personal burnout, WB: work-related burnout, CB: client-related burnout
_ITEM_SUBSCALES: list[str] = [
    "PB",  # 1
    "PB",  # 2
    "PB",  # 3
    "PB",  # 4
    "PB",  # 5
    "PB",  # 6
    "WB",  # 7
    "WB",  # 8
    "WB",  # 9
    "WB",  # 10
    "WB",  # 11
    "WB",  # 12
    "CB",  # 13
    "CB",  # 14
    "CB",  # 15
    "CB",  # 16
    "CB",  # 17
    "PB",  # 18 — scorched earth / overidentification (scored as PB)
    "PB",  # 19 — overidentification (scored as PB)
]

# Valid range per item
_MIN, _MAX = 0.0, 6.0

# Subscale cut-points (high burnout)
_CUT_PB = 50.0
_CUT_WB = 50.0
_CUT_CB = 45.0


@dataclass(frozen=True)
class CBISubscaleScores:
    personal: float
    work_related: float
    client_related: float

    def is_high_personal(self) -> bool:
        return self.personal >= _CUT_PB

    def is_high_work_related(self) -> bool:
        return self.work_related >= _CUT_WB

    def is_high_client_related(self) -> bool:
        return self.client_related >= _CUT_CB

    def high_subscales(self) -> list[str]:
        out = []
        if self.is_high_personal():
            out.append("personal")
        if self.is_high_work_related():
            out.append("work_related")
        if self.is_high_client_related():
            out.append("client_related")
        return out


@dataclass(frozen=True)
class CBIResult:
    subscales: CBISubscaleScores
    composite: float  # mean of three subscale scores
    raw_item_scores: list[float]  # 0–100 per item
    valid_items: int  # count of items with non-null responses


class CBIValidationError(ValueError):
    pass


def scorecbi(responses: list[float | None], na_acceptable: bool = False) -> CBIResult:
    """
    Score a 19-item CBI response list.

    Parameters
    ----------
    responses:
        List of 19 numeric responses, one per CBI item.
        Each value must be in [0, 6] (0=never, 6=every day).
        None entries are treated as missing.
        Items 13–17 (CB subscale) may be None if not applicable;
        ``na_acceptable`` must be True to allow this.

    na_acceptable:
        If True, None values for items 13–17 are acceptable (respondent has
        no client contact). If False, any None entry raises.

    Returns
    -------
    CBIResult
        subscales: CBISubscaleScores (all three subscale scores 0–100)
        composite: mean of the three subscale scores (overall burnout index)
        raw_item_scores: each item expressed as 0–100 (multiply by 100/6)
        valid_items: number of non-null items

    Raises
    ------
    CBIValidationError
        If the list is not exactly 19 items, or if any non-CB item is None,
        or if any value is outside [0, 6].
    """
    if len(responses) != 19:
        raise CBIValidationError(
            f"expected 19 CBI responses, got {len(responses)}"
        )

    # Validate each response
    validated: list[float] = []
    cb_na_items: set[int] = set()  # indices of acceptable None CB items

    for i, val in enumerate(responses):
        subscale = _ITEM_SUBSCALES[i]
        if val is None:
            if subscale == "CB" and na_acceptable:
                cb_na_items.add(i)
                validated.append(0.0)  # placeholder; excluded from CB mean
            else:
                raise CBIValidationError(
                    f"item {i+1} (subscale={subscale}) is None but "
                    f"na_acceptable={na_acceptable}"
                )
        elif not isinstance(val, (int, float)):
            raise CBIValidationError(
                f"item {i+1} must be numeric, got {type(val).__name__}"
            )
        elif val < _MIN or val > _MAX:
            raise CBIValidationError(
                f"item {i+1} must be in [{_MIN}, {_MAX}], got {val}"
            )
        else:
            validated.append(float(val))

    # Convert to 0–100 scale
    raw: list[float] = [v * (100.0 / _MAX) for v in validated]

    # Compute subscale means
    pb_vals = [raw[i] for i in range(19) if _ITEM_SUBSCALES[i] == "PB"]
    wb_vals = [raw[i] for i in range(19) if _ITEM_SUBSCALES[i] == "WB"]
    cb_vals = [
        raw[i]
        for i in range(19)
        if _ITEM_SUBSCALES[i] == "CB" and i not in cb_na_items
    ]

    if not pb_vals:
        raise CBIValidationError("no personal burnout items present")
    if not wb_vals:
        raise CBIValidationError("no work-related burnout items present")

    pb_mean = sum(pb_vals) / len(pb_vals)
    wb_mean = sum(wb_vals) / len(wb_vals)
    cb_mean = sum(cb_vals) / len(cb_vals) if cb_vals else 0.0

    subscales = CBISubscaleScores(
        personal=pb_mean,
        work_related=wb_mean,
        client_related=cb_mean,
    )

    composite = (pb_mean + wb_mean + cb_mean) / 3.0

    return CBIResult(
        subscales=subscales,
        composite=composite,
        raw_item_scores=raw,
        valid_items=sum(1 for i in range(19) if i not in cb_na_items),
    )


def composite_burnout_score(responses: list[float | None], na_acceptable: bool = False) -> float:
    """
    Convenience: return the composite CBI score (0–100) from a response list.

    Raises CBIValidationError on invalid input.
    """
    return scorecbi(responses, na_acceptable=na_acceptable).composite
