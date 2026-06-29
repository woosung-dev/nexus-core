"""add_redteam_manage_feedback

Revision ID: b8d2e3f4a5c6
Revises: a7c1f2d9e4b8
Create Date: 2026-06-29 16:00:00.000000

입력관리 — 질문(그룹)별 복수 담당자 피드백 코멘트 스레드 테이블.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'b8d2e3f4a5c6'
down_revision: Union[str, Sequence[str], None] = 'a7c1f2d9e4b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'redteam_manage_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('author', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('content', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['redteam_question_groups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_redteam_manage_feedback_group_id'),
        'redteam_manage_feedback',
        ['group_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_redteam_manage_feedback_group_id'), table_name='redteam_manage_feedback')
    op.drop_table('redteam_manage_feedback')
