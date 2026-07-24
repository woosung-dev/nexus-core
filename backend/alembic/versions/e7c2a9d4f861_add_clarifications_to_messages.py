"""Add clarifications JSON column to messages

Revision ID: e7c2a9d4f861
Revises: b4d8f2a1c6e9
Create Date: 2026-07-19 00:00:00.000000

재질문 카드 payload를 메시지에 영속화.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7c2a9d4f861"
down_revision: Union[str, Sequence[str], None] = "b4d8f2a1c6e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("messages", sa.Column("clarifications", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("messages", "clarifications")
