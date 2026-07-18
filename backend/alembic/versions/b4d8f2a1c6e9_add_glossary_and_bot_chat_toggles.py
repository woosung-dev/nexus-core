"""용어집과 봇 채팅 토글 추가."""

from typing import Sequence, Union

from alembic import op
import pgvector.sqlalchemy
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b4d8f2a1c6e9"
down_revision: Union[str, Sequence[str], None] = "f8a4c2d9e1b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """용어집 테이블과 봇별 채팅 토글을 생성한다."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.create_table(
        "glossary_terms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bot_id", sa.Integer(), nullable=True),
        sa.Column("term", sa.String(length=200), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=True),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("term_vector", pgvector.sqlalchemy.Vector(768), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("threshold", sa.Float(), nullable=False, server_default="0.88"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["bot_id"], ["bots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_glossary_terms_bot_id", "glossary_terms", ["bot_id"])
    op.create_index(
        "ix_glossary_terms_bot_active",
        "glossary_terms",
        ["bot_id", "is_active"],
    )
    op.create_index("ix_glossary_terms_term", "glossary_terms", ["term"])
    op.add_column(
        "bots",
        sa.Column("glossary_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "bots",
        sa.Column("clarify_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """용어집 테이블과 봇별 채팅 토글을 제거한다."""
    op.drop_column("bots", "clarify_enabled")
    op.drop_column("bots", "glossary_enabled")
    op.drop_index("ix_glossary_terms_term", table_name="glossary_terms")
    op.drop_index("ix_glossary_terms_bot_active", table_name="glossary_terms")
    op.drop_index("ix_glossary_terms_bot_id", table_name="glossary_terms")
    op.drop_table("glossary_terms")
