"""Add persisted adaptive clarification state to chat sessions.

Revision ID: b1c2d3e4f5a6
Revises: e2f6a4b8c1d3
Create Date: 2026-08-04 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "e2f6a4b8c1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chat_sessions", sa.Column("clarification_state", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("chat_sessions", "clarification_state")
