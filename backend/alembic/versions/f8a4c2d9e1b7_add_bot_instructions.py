# 봇 지침 빌더 테이블을 추가하는 Alembic 마이그레이션.
"""add_bot_instructions

Revision ID: f8a4c2d9e1b7
Revises: e7d9c3b1a5f2

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f8a4c2d9e1b7"
down_revision: Union[str, Sequence[str], None] = "e7d9c3b1a5f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """봇 지침 빌더 테이블을 생성한다."""
    op.create_table(
        "bot_instructions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bot_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("goal", sa.String(), nullable=False),
        sa.Column("tone", sa.String(), nullable=False),
        sa.Column("audience", sa.String(), nullable=False),
        sa.Column("constraints", sa.Text(), nullable=False),
        sa.Column("dos", sa.JSON(), nullable=True),
        sa.Column("donts", sa.JSON(), nullable=True),
        sa.Column("examples", sa.JSON(), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("llm_model", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_applied", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["bot_id"], ["bots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bot_instructions_bot_id"), "bot_instructions", ["bot_id"], unique=False)


def downgrade() -> None:
    """봇 지침 빌더 테이블을 제거한다."""
    op.drop_index(op.f("ix_bot_instructions_bot_id"), table_name="bot_instructions")
    op.drop_table("bot_instructions")
