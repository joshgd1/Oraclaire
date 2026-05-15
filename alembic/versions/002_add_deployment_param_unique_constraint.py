"""002 — add unique constraint on (organisation_id, key) for deployment_parameters

Revision ID: 002
Revises: 001
Create Date: 2026-05-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table(
        "deployment_parameters", recreate="always"
    ) as batch_op:
        batch_op.create_unique_constraint(
            "uq_deployment_param_org_key",
            ["organisation_id", "key"],
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "deployment_parameters", recreate="always"
    ) as batch_op:
        batch_op.drop_constraint(
            "uq_deployment_param_org_key",
            type_="unique",
        )
