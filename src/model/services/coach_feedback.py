"""
Coach feedback service.

Managers rate the interventions they've tried, building a "what worked" knowledge base
for similar teams over time.

Architecture:
- In-memory store for demo mode (persisted across sessions via session_state)
- Pluggable storage backend for real deployments
- Peer team matching by: team size bucket + ORT bucket (low/moderate/high)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

# ── Types ────────────────────────────────────────────────────────────────────

@dataclass
class CoachFeedback:
    id: int
    recommendation: str
    rating: Literal["helped", "neutral", "did_not_help"]
    notes: str
    manager_id: str
    team_size_bucket: str
    ort_bucket: str  # low (<10%), moderate (10-20%), high (>20%)
    ort_pct: float
    created_at: datetime


@dataclass
class WorkedRecommendation:
    recommendation: str
    helpful_count: int
    total_count: int
    helpful_pct: float
    avg_rating: float  # 1=helped, 0=neutral, -1=did_not_help


# ── In-memory store ───────────────────────────────────────────────────────────

_feedbacks: list[CoachFeedback] = []
_feedback_counter = 0


def _team_size_bucket(size: int) -> str:
    if size <= 5:
        return "xs"    # 1-5
    elif size <= 10:
        return "sm"     # 6-10
    elif size <= 25:
        return "md"    # 11-25
    elif size <= 50:
        return "lg"    # 26-50
    else:
        return "xl"     # 51+


def _ort_bucket(hc_pct: float) -> str:
    if hc_pct < 0.10:
        return "low"
    elif hc_pct <= 0.20:
        return "moderate"
    else:
        return "high"


def submit_feedback(
    recommendation: str,
    rating: str,
    notes: str,
    manager_id: str,
    team_size: int,
    ort_pct: float,
) -> CoachFeedback:
    """Record a manager's feedback on an intervention."""
    global _feedback_counter, _feedbacks

    fb = CoachFeedback(
        id=_feedback_counter,
        recommendation=recommendation,
        rating=rating,
        notes=notes or "",
        manager_id=manager_id,
        team_size_bucket=_team_size_bucket(team_size),
        ort_bucket=_ort_bucket(ort_pct),
        ort_pct=ort_pct,
        created_at=datetime.utcnow(),
    )
    _feedbacks.append(fb)
    _feedback_counter += 1
    return fb


def get_worked_recommendations(
    ort_pct: float,
    team_size: int,
    top_n: int = 5,
) -> list[WorkedRecommendation]:
    """Return top-rated interventions for teams with similar ORT and size profile."""
    my_ort = _ort_bucket(ort_pct)
    my_size = _team_size_bucket(team_size)

    # Same ORT bucket + similar team size bucket (±1)
    size_buckets = {
        "xs": ("xs", "sm"),
        "sm": ("xs", "sm", "md"),
        "md": ("sm", "md", "lg"),
        "lg": ("md", "lg", "xl"),
        "xl": ("lg", "xl"),
    }
    relevant_buckets = size_buckets.get(my_size, (my_size,))

    pool = [
        fb for fb in _feedbacks
        if fb.ort_bucket == my_ort and fb.team_size_bucket in relevant_buckets
    ]

    if not pool:
        return []

    # Group by recommendation
    from collections import defaultdict
    by_rec: dict[str, list[CoachFeedback]] = defaultdict(list)
    for fb in pool:
        by_rec[fb.recommendation].append(fb)

    results = []
    for rec, fbs in by_rec.items():
        total = len(fbs)
        helpful = sum(1 for fb in fbs if fb.rating == "helped")
        neutral = sum(1 for fb in fbs if fb.rating == "neutral")
        didnt_help = sum(1 for fb in fbs if fb.rating == "did_not_help")
        helpful_pct = helpful / total if total > 0 else 0
        avg_rating = (helpful * 1.0 + neutral * 0.0 + didnt_help * -1.0) / total
        results.append(WorkedRecommendation(
            recommendation=rec,
            helpful_count=helpful,
            total_count=total,
            helpful_pct=helpful_pct,
            avg_rating=avg_rating,
        ))

    results.sort(key=lambda r: (r.avg_rating, r.helpful_count), reverse=True)
    return results[:top_n]


def get_my_feedback(manager_id: str) -> list[CoachFeedback]:
    """Return all feedback submitted by a manager."""
    return [fb for fb in _feedbacks if fb.manager_id == manager_id]
