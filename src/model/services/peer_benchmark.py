"""
Peer benchmarking service.

Shows employees how their wellbeing dimensions compare to peers with
similar seniority, tenure, work setup, and company type.

Peer averages are computed once from the training dataset and cached.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

# ── Peer bucket definition ────────────────────────────────────────────────────

TENURE_BUCKETS = [
    ("new", 0, 365),         # 0–12 months
    ("established", 366, 1095),  # 1–3 years
    ("veteran", 1096, 99999),  # 3+ years
]


def _bucket_tenure(tenure_days: float) -> str:
    for label, lo, hi in TENURE_BUCKETS:
        if lo <= tenure_days <= hi:
            return label
    return "veteran"


@dataclass
class PeerBucket:
    """The 4-dimensional bucket this employee belongs to."""
    seniority_bucket: Literal["junior", "senior"]
    tenure_bucket: Literal["new", "established", "veteran"]
    wfh_bucket: Literal["wfh", "hybrid_office"]
    company_bucket: Literal["product", "service"]


def bucket_employee(
    seniority_tier: float,
    tenure_days: float,
    wfh_setup: float,
    company_type: float,
) -> PeerBucket:
    """
    Map an employee's raw features to their peer bucket.

    Seniority: junior (Designation < 4) / senior (Designation >= 4)
    Tenure:    new / established / veteran (by days)
    WFH:       wfh (0) / hybrid_office (1 or 2)
    Company:   product (1) / service (0)
    """
    seniority = "senior" if seniority_tier >= 1.0 else "junior"
    tenure = _bucket_tenure(tenure_days)
    wfh = "wfh" if wfh_setup == 0.0 else "hybrid_office"
    company = "product" if company_type >= 1.0 else "service"

    return PeerBucket(
        seniority_bucket=seniority,
        tenure_bucket=tenure,
        wfh_bucket=wfh,
        company_bucket=company,
    )


# ── Peer average computation ─────────────────────────────────────────────────

# Columns we need from the training CSV
PEER_COLS = [
    "Company Type",
    "WFH Setup Available",
    "Resource Allocation",
    "Mental Fatigue Score",
    "Designation",
    "Date of Joining",
    "Burn Rate",
]

# Reference date for tenure (must match model train.py)
REF_DATE = datetime(2026, 1, 1)


def _load_and_prepare_peer_data() -> pd.DataFrame:
    """Load training data and compute per-row features for peer grouping."""
    path = Path("data/raw/train.csv")
    if not path.exists():
        return pd.DataFrame()  # empty — peer averages unavailable

    df = pd.read_csv(path, usecols=PEER_COLS).dropna(subset=["Burn Rate"])

    # Seniority: Designation >= 4 → senior
    df["seniority_tier"] = (df["Designation"] >= 4).astype(float)

    # Tenure days
    df["doj"] = pd.to_datetime(df["Date of Joining"], errors="coerce")
    df["tenure_days"] = (REF_DATE - df["doj"]).dt.days.clip(lower=0)

    # WFH: Yes → 0 (WFH), No/other → 1 (Hybrid/Office)
    df["wfh_setup"] = df["WFH Setup Available"].apply(
        lambda v: 0.0 if str(v).strip().lower() == "yes" else 1.0
    )

    # Company type: Product → 1, Service → 0
    df["company_type"] = df["Company Type"].apply(
        lambda v: 1.0 if str(v).strip().lower() == "product" else 0.0
    )

    # Scale resource_allocation and mental_fatigue_score to 0–100
    # Resource Allocation: 0–10 raw → 0–100
    df["workload_dim"] = df["Resource Allocation"] / 10.0 * 100.0

    # Energy (mental_fatigue_score): 1–10 raw, invert → higher fatigue = lower score
    # Score = (10 - mfs) / 9 * 100
    mfs = df["Mental Fatigue Score"].clip(1.0, 10.0)
    df["energy_dim"] = (10.0 - mfs) / 9.0 * 100.0

    # Burn Rate: already 0–1 → 0–100
    df["burnout_dim"] = df["Burn Rate"] * 100.0

    # Recovery: invert burn_rate → higher recovery = lower burnout
    df["recovery_dim"] = 100.0 - df["burnout_dim"]

    return df


def _peer_key(bucket: PeerBucket) -> tuple:
    return (bucket.seniority_bucket, bucket.tenure_bucket, bucket.wfh_bucket, bucket.company_bucket)


# Cached peer averages — keyed by PeerBucket tuple
_PEER_AVG_CACHE: dict[tuple, dict[str, float]] = {}


def _compute_all_peer_averages() -> dict:
    """Compute mean wellbeing scores for every peer bucket from training data."""
    df = _load_and_prepare_peer_data()
    if df.empty:
        return {}

    # Tenure bucket thresholds
    TENURE_LO = {"new": 0, "established": 366, "veteran": 1096}
    TENURE_HI = {"new": 365, "established": 1095, "veteran": 99999}

    seniority_map = {"senior": 1.0, "junior": 0.0}
    wfh_map = {"wfh": 0.0, "hybrid_office": 1.0}
    company_map = {"product": 1.0, "service": 0.0}

    results = {}
    for seniority in ("junior", "senior"):
        for tenure in ("new", "established", "veteran"):
            for wfh in ("wfh", "hybrid_office"):
                for company in ("product", "service"):
                    lo = TENURE_LO[tenure]
                    hi = TENURE_HI[tenure]
                    mask = (
                        (df["seniority_tier"] == seniority_map[seniority])
                        & (df["tenure_days"] >= lo)
                        & (df["tenure_days"] <= hi)
                        & (df["wfh_setup"] == wfh_map[wfh])
                        & (df["company_type"] == company_map[company])
                    )
                    group = df[mask]
                    if len(group) < 5:
                        group = df

                    results[(seniority, tenure, wfh, company)] = {
                        "workload": round(float(group["workload_dim"].mean()), 1),
                        "energy": round(float(group["energy_dim"].mean()), 1),
                        "recovery": round(float(group["recovery_dim"].mean()), 1),
                        "burnout": round(float(group["burnout_dim"].mean()), 1),
                        "n_peers": int(len(group)),
                    }
    return results


# ── Public API ──────────────────────────────────────────────────────────────


def get_peer_benchmark(
    seniority_tier: float,
    tenure_days: float,
    wfh_setup: float,
    company_type: float,
    *,
    employee_workload: float | None = None,
    employee_energy: float | None = None,
    employee_recovery: float | None = None,
) -> dict:
    """
    Return peer benchmark comparison for an employee's wellbeing dimensions.

    Returns a dict of dimension → {score, peer_avg, better_than_peer}
    for Workload, Energy, Recovery, and Overall Burnout.

    Uses the employee's raw features to find their peer bucket, then returns
    peer averages from the cached training-data computation.

    Pass the employee's check-in responses (0–100 scaled) for the score;
    if None, returns only peer_avg.
    """
    global _PEER_AVG_CACHE

    if not _PEER_AVG_CACHE:
        _PEER_AVG_CACHE = _compute_all_peer_averages()

    bucket = bucket_employee(seniority_tier, tenure_days, wfh_setup, company_type)
    key = _peer_key(bucket)

    peer_avgs = _PEER_AVG_CACHE.get(key, {})
    n_peers = peer_avgs.get("n_peers", 0)

    # Fall back to overall population means if bucket too small
    if n_peers < 5:
        if _PEER_AVG_CACHE:
            all_vals = {dim: [] for dim in ("workload", "energy", "recovery", "burnout")}
            for v in _PEER_AVG_CACHE.values():
                for dim in all_vals:
                    all_vals[dim].append(v[dim])
            peer_avgs = {dim: round(float(np.mean(vals)), 1) for dim, vals in all_vals.items()}
        else:
            peer_avgs = {"workload": 50.0, "energy": 50.0, "recovery": 50.0, "burnout": 50.0}

    def compare(score: float | None, peer_avg: float) -> dict:
        if score is None:
            return {"score": None, "peer_avg": peer_avg, "better_than_peer": None}
        # For workload/burnout: higher is worse; for energy/recovery: higher is better
        delta = score - peer_avg
        return {"score": score, "peer_avg": peer_avg, "delta": round(delta, 1)}

    return {
        "bucket": bucket,
        "n_peers": n_peers,
        "dimensions": {
            "Workload": compare(employee_workload, peer_avgs.get("workload", 50.0)),
            "Energy": compare(employee_energy, peer_avgs.get("energy", 50.0)),
            "Recovery": compare(employee_recovery, peer_avgs.get("recovery", 50.0)),
            "Burnout": compare(None, peer_avgs.get("burnout", 50.0)),
        },
    }
