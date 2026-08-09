"""add_redteam_goldens

Revision ID: 7c04bb6da692
Revises: c8e2a4d6f9b1
Create Date: 2026-08-05 12:00:00.000000

정답지(golden) 테이블 — 회귀 하네스 L3 심사의 기준. 그룹당 1행.
`redteam_question_groups.model_answer`(리뷰어 자유 메모)와 별개다.
개발이 규정집 v20·공문·대사전 v4 원문에서 근거 카드를 만들어 넣고(status='초안'),
관리자는 화면에서 판정만 한다(승인 / 수정승인 / 근거없음 / 반려).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '7c04bb6da692'
down_revision: Union[str, Sequence[str], None] = 'c8e2a4d6f9b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'redteam_goldens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('golden', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('evidence', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('must_any', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('must_not', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('source_docs', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('corpus_version', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('coverage', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('open_question', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('draft_engine', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='codex'),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='초안'),
        sa.Column('approver', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('admin_note', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('draft_golden', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['redteam_question_groups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_id', name='uq_redteam_golden_group'),
    )
    op.create_index(
        op.f('ix_redteam_goldens_group_id'), 'redteam_goldens', ['group_id'], unique=False,
    )
    op.create_index(
        op.f('ix_redteam_goldens_status'), 'redteam_goldens', ['status'], unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_redteam_goldens_status'), table_name='redteam_goldens')
    op.drop_index(op.f('ix_redteam_goldens_group_id'), table_name='redteam_goldens')
    op.drop_table('redteam_goldens')
