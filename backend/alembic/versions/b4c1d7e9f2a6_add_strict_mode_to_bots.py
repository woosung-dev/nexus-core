"""add_strict_mode_to_bots

Revision ID: b4c1d7e9f2a6
Revises: f8a4c2d9e1b7
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4c1d7e9f2a6"
down_revision: Union[str, Sequence[str], None] = "f8a4c2d9e1b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bots",
        sa.Column("evidence_policy_mode", sa.String(length=20), nullable=False, server_default="legacy"),
    )


def downgrade() -> None:
    op.drop_column("bots", "evidence_policy_mode")
