"""003 — add role column to employees

Revision ID: 003
Revises: 002
Create Date: 2026-05-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column(
            "role",
            sa.Enum(
                "employee", "manager", "hr_admin", "system_admin",
                name="role",
            ),
            nullable=False,
            server_default=sa.text("'employee'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("employees", "role")
