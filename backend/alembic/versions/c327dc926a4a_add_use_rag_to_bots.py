"""add use_rag to bots

Revision ID: c327dc926a4a
Revises: c7f8e2a91b3d
Create Date: 2026-05-21 21:16:05.371429

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c327dc926a4a'
down_revision: Union[str, Sequence[str], None] = 'c7f8e2a91b3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    기존 row에 use_rag=True를 채우기 위해 server_default 사용. 신규 row는 model
    default(True)로 채워지므로 server_default를 그대로 두어도 무방. file_search store가
    비어있는 봇은 admin에서 use_rag=False로 토글 가능.
    """
    op.add_column(
        'bots',
        sa.Column('use_rag', sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('bots', 'use_rag')
