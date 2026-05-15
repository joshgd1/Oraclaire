"""004 — add employee feature-extraction fields

Revision ID: 004
Revises: 003
Create Date: 2026-05-15

Adds:
- date_of_joining (DATE, nullable) — tenure computation
- company_type (VARCHAR(20), nullable) — "Product" or "Service"
- wfh_setup_available (BOOLEAN, default False) — work-from-home flag

These fields are required for M5-09 real feature extraction in the
scoring pipeline. Nullable allows existing employees to be scored with
defaults (median imputation) while HRIS sync populates the fields.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column("date_of_joining", sa.Date(), nullable=True),
    )
    op.add_column(
        "employees",
        sa.Column("company_type", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "employees",
        sa.Column(
            "wfh_setup_available",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("employees", "wfh_setup_available")
    op.drop_column("employees", "company_type")
    op.drop_column("employees", "date_of_joining")
