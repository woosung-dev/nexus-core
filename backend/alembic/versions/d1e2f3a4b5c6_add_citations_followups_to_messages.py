"""Add citations and followups JSON columns to messages

Revision ID: d1e2f3a4b5c6
Revises: c327dc926a4a
Create Date: 2026-05-30 17:30:00.000000

RAG 인용/후속질문을 메시지에 영속화. 기존 행은 NULL(기능 도입 전 대화 → UI에서 '인용 기록 없음' 안내).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'c327dc926a4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('messages', sa.Column('citations', sa.JSON(), nullable=True))
    op.add_column('messages', sa.Column('followups', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('messages', 'followups')
    op.drop_column('messages', 'citations')
