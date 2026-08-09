"""Add bot clarification policy

Revision ID: e2f6a4b8c1d3
Revises: d9e4f1c2a3b4
Create Date: 2026-08-03 14:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e2f6a4b8c1d3"
down_revision: Union[str, Sequence[str], None] = "d9e4f1c2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_DEFAULT_POLICY = '{"enabled": false, "rules": []}'


def upgrade() -> None:
    op.add_column(
        "bots",
        sa.Column(
            "clarification_policy",
            sa.JSON(),
            nullable=False,
            server_default=sa.text(f"'{_DEFAULT_POLICY}'::json"),
        ),
    )
    op.alter_column("bots", "clarification_policy", server_default=None)


def downgrade() -> None:
    op.drop_column("bots", "clarification_policy")
