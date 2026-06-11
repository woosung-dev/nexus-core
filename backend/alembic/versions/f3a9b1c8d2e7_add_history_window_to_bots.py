"""add history_window to bots

Revision ID: f3a9b1c8d2e7
Revises: eaa5c93b1bf2
Create Date: 2026-06-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a9b1c8d2e7'
down_revision: Union[str, Sequence[str], None] = 'eaa5c93b1bf2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    멀티턴 대화 기억 윈도우 — LLM 호출에 함께 보낼 최근 메시지 수.
    기존/신규 row 모두 0(비활성, stateless 현행 유지)으로 시작하고
    admin 페이지에서 봇별로 숫자 입력해 켠다. 카카오 연결 봇은 0 유지 권장.
    """
    op.add_column(
        'bots',
        sa.Column('history_window', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('bots', 'history_window')
