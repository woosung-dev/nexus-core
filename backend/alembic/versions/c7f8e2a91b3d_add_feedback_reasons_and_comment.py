"""Add feedback_reasons and feedback_comment columns to messages

Revision ID: c7f8e2a91b3d
Revises: 9c4542e79a68
Create Date: 2026-05-20 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = 'c7f8e2a91b3d'
down_revision: Union[str, Sequence[str], None] = '9c4542e79a68'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'messages',
        sa.Column('feedback_reasons', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    )
    op.add_column(
        'messages',
        sa.Column('feedback_comment', sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('messages', 'feedback_comment')
    op.drop_column('messages', 'feedback_reasons')
