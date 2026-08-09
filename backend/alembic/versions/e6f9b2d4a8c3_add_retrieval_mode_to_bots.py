"""add_retrieval_mode_to_bots

Revision ID: e6f9b2d4a8c3
Revises: d5e8a1c3f7b2
Create Date: 2026-08-09 03:30:00.000000

봇별 근거 조달 방식(`retrieval_mode`).

    file_search  Gemini file_search 단독      57.9% · 7.0초   커버리지 최고 (기본값)
    lexical      BM25 원문 주입 단독           40.2% · 1.6초   덜 맞히고 덜 틀린다
    both         file_search + BM25 원문      50.4% · 6.1초   중간

수치는 봇 11 · gemini-3.5-flash-lite · 45문항 실측이다
(`docs/architecture/handoff-wiki-retrieval-2026-08-08.md` §2-2).

`server_default='file_search'` 이므로 **기존 봇은 전부 지금과 똑같이 동작한다.**
evidence_policy_mode 와 같이 DB enum 이 아니라 String(20) 이다 — 값 추가·롤백에
CREATE TYPE 이 필요 없고, 열거는 Pydantic Literal 이 강제한다.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6f9b2d4a8c3'
down_revision: Union[str, Sequence[str], None] = 'd5e8a1c3f7b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'bots',
        sa.Column('retrieval_mode', sa.String(length=20),
                  nullable=False, server_default='file_search'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('bots', 'retrieval_mode')
