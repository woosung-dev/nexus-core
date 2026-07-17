"""add_redteam_testbot_evals

Revision ID: e7d9c3b1a5f2
Revises: b8d2e3f4a5c6
Create Date: 2026-07-17 01:40:00.000000

테스트 봇 재검증 — 3주차 상·중 질문을 테스트 봇에 재질의한 답변 + AI(codex) 3평가 테이블.
(그룹 × 봇 × 회차)당 1행. question_norm 으로 재임포트 보존.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'e7d9c3b1a5f2'
down_revision: Union[str, Sequence[str], None] = 'b8d2e3f4a5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'redteam_testbot_evals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('question_norm', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('run_label', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='테스트 1주차'),
        sa.Column('bot_label', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='테스트 봇 D-1'),
        sa.Column('bot_id', sa.Integer(), nullable=True),
        sa.Column('bot_model', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('answer', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('citations', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('bf_citations', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('risk_recur', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('risk_recur_detail', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('independent_risk', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('independent_risk_detail', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('ai_rating', sa.Float(), nullable=True),
        sa.Column('ai_rating_detail', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('eval_engine', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='codex'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['redteam_question_groups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_id', 'bot_label', 'run_label', name='uq_redteam_testbot_eval'),
    )
    op.create_index(
        op.f('ix_redteam_testbot_evals_group_id'),
        'redteam_testbot_evals', ['group_id'], unique=False,
    )
    op.create_index(
        op.f('ix_redteam_testbot_evals_question_norm'),
        'redteam_testbot_evals', ['question_norm'], unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_redteam_testbot_evals_question_norm'), table_name='redteam_testbot_evals')
    op.drop_index(op.f('ix_redteam_testbot_evals_group_id'), table_name='redteam_testbot_evals')
    op.drop_table('redteam_testbot_evals')
