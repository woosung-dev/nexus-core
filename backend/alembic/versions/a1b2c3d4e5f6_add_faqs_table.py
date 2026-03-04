"""add_faqs_table

Revision ID: a1b2c3d4e5f6
Revises: 50e4439ee7d7
Create Date: 2026-03-03 22:00:00.000000

faqs 테이블 생성:
- pgvector 확장 활성화 (CREATE EXTENSION IF NOT EXISTS vector)
- bot_id(FK), question, answer, threshold, question_vector(768dim), is_active 컬럼
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "50e4439ee7d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgvector 확장 활성화 (Supabase에서 이미 활성화됨, 멱등성 보장)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # faqs 테이블 생성
    op.create_table(
        "faqs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bot_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.String(length=1000), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False, server_default="0.85"),
        sa.Column("question_vector", Vector(768), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["bot_id"],
            ["nexus_core.bots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="nexus_core",
    )

    # bot_id 인덱스 생성 (봇별 FAQ 조회 성능)
    op.create_index(
        "ix_nexus_core_faqs_bot_id",
        "faqs",
        ["bot_id"],
        schema="nexus_core",
    )

    # question_vector HNSW 인덱스 (코사인 유사도 검색 최적화)
    # 향후 채팅 서비스에서 벡터 유사도 검색 시 사용
    op.execute(
        """
        CREATE INDEX ix_nexus_core_faqs_question_vector
        ON nexus_core.faqs
        USING hnsw (question_vector vector_cosine_ops)
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_nexus_core_faqs_question_vector",
        table_name="faqs",
        schema="nexus_core",
    )
    op.drop_index(
        "ix_nexus_core_faqs_bot_id",
        table_name="faqs",
        schema="nexus_core",
    )
    op.drop_table("faqs", schema="nexus_core")
