"""add is_official to users

Revision ID: 8f3d7a1c9e5b
Revises: f8a4c2d9e1b7
Create Date: 2026-07-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f3d7a1c9e5b'
down_revision: Union[str, Sequence[str], None] = 'f8a4c2d9e1b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """기존 row는 server_default=false로 백필, 하나로 SSO 공직자 여부."""
    op.add_column(
        'users',
        sa.Column('is_official', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'is_official')
