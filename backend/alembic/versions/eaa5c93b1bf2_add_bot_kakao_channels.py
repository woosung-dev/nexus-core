"""add bot_kakao_channels

Revision ID: eaa5c93b1bf2
Revises: d1e2f3a4b5c6
Create Date: 2026-06-05 12:25:53.336826

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eaa5c93b1bf2'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bot_kakao_channels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id"), nullable=False),
        sa.Column("kakao_bot_id", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_bot_kakao_channels_bot_id", "bot_kakao_channels", ["bot_id"])
    op.create_index(
        "ix_bot_kakao_channels_kakao_bot_id",
        "bot_kakao_channels",
        ["kakao_bot_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_bot_kakao_channels_kakao_bot_id", table_name="bot_kakao_channels")
    op.drop_index("ix_bot_kakao_channels_bot_id", table_name="bot_kakao_channels")
    op.drop_table("bot_kakao_channels")
