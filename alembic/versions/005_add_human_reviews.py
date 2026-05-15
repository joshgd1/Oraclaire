"""005 — add human_reviews table

Revision ID: 005
Revises: 004
Create Date: 2026-05-15

M6-01: Human review gate for Critical-tier scores.
Each Critical-tier RiskScore gets a HumanReview record in PENDING_REVIEW
state. HR must explicitly approve or override before any intervention
triggers for that employee.

Tables:
- human_reviews: per-employee review gate
  - unique per employee+cycle (one review per employee per cycle)
  - unique FK to risk_scores (one review per score)
  - indexes on status (for pending review queries) and employee+cycle

ReviewStatus values:
- pending_review: initial state, no HR action yet
- approved: HR reviewed and confirmed the tier is correct
- overridden: HR reviewed and changed the tier to low/moderate/high
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "human_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("cycle_id", sa.Integer(), nullable=False),
        sa.Column("risk_score_id", sa.Integer(), nullable=False, unique=True),
        sa.Column(
            "review_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending_review",
        ),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("override_new_tier", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["cycle_id"], ["assessment_cycles.id"]),
        sa.ForeignKeyConstraint(["risk_score_id"], ["risk_scores.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "cycle_id", name="ix_human_reviews_employee_cycle"),
    )
    op.create_index(
        "ix_human_reviews_status",
        "human_reviews",
        ["review_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_human_reviews_status", table_name="human_reviews")
    op.drop_table("human_reviews")
