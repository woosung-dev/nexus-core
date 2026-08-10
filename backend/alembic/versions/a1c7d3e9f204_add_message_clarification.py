"""add_message_clarification

Revision ID: a1c7d3e9f204
Revises: f4a7b2c9d1e6
Create Date: 2026-08-10 18:00:00.000000

`messages.clarification` — 봇이 되물은 턴의 선택지 카드를 남긴다.

컬럼이 필요한 이유는 프론트 때문이다. `ChatProvider.tsx` 는 응답을 받은 직후
`refetchMessages()` 로 세션 메시지를 통째로 다시 불러온다. 되묻기 카드를 응답에만 싣고
낙관적 메시지에 붙이면 **그 재조회가 덮어써서 1초 뒤 사라진다.** 새로고침해도 남아야
사용자가 나중에 선택지를 누를 수 있다.

`citations`·`followups` 와 같은 자리·같은 방식(JSON nullable)이다. 되묻지 않은 턴은
NULL 이고, 도입 전 대화도 전부 NULL 이라 기존 행 보정이 필요 없다.

담는 모양은 `ChatClarification`(schemas/clarification.py):
    {"status": "ask"|"handoff", "questions": [...], "rule_id": str|null, "round": int}
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c7d3e9f204'
down_revision: Union[str, Sequence[str], None] = 'f4a7b2c9d1e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('messages', sa.Column('clarification', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('messages', 'clarification')
