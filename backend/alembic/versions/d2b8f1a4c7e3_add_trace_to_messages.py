"""Add trace JSON column to messages

Revision ID: d2b8f1a4c7e3
Revises: c5b1e7a09d42
Create Date: 2026-08-13 18:20:00.000000

한 턴이 여덟 단계(faq · ops_facts · retrieval · strict · strip · unanswered · term · record)를
어떻게 지났는지 남긴다. 규약은 `app/services/turn_trace.py`.

**관리자 전용이다.** `ChatCompletionResponse` 에 넣지 않는다(`tests/test_turn_trace.py` 가 검증).
기존 행은 NULL — 도입 이전 대화는 trace 가 없으므로 읽는 쪽이 없을 때를 견뎌야 한다.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd2b8f1a4c7e3'
down_revision: Union[str, Sequence[str], None] = 'c5b1e7a09d42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('messages', sa.Column('trace', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('messages', 'trace')
