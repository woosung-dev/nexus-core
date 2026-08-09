"""Add per-bot clarification pilot toggle

Revision ID: d9e4f1c2a3b4
Revises: c8e2a4d6f9b1
Create Date: 2026-08-03 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d9e4f1c2a3b4"
down_revision: Union[str, Sequence[str], None] = "c8e2a4d6f9b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bots",
        sa.Column("clarify_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("bots", "clarify_enabled", server_default=None)


def downgrade() -> None:
    op.drop_column("bots", "clarify_enabled")
