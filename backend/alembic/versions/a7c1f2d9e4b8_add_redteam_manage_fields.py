"""add_redteam_manage_fields

Revision ID: a7c1f2d9e4b8
Revises: f3ab5cee1278
Create Date: 2026-06-29 10:00:00.000000

중간보고 입력관리 대시보드용 관리 필드를 redteam_question_groups에 추가.
status/disposition/model_answer는 server_default로 기존 행 백필, level/assignee는 nullable.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a7c1f2d9e4b8'
down_revision: Union[str, Sequence[str], None] = 'f3ab5cee1278'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'redteam_question_groups',
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='대기'),
    )
    op.add_column(
        'redteam_question_groups',
        sa.Column('level', sa.Integer(), nullable=True),
    )
    op.add_column(
        'redteam_question_groups',
        sa.Column('disposition', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='미정'),
    )
    op.add_column(
        'redteam_question_groups',
        sa.Column('tags', sa.JSON(), nullable=False, server_default='[]'),
    )
    op.add_column(
        'redteam_question_groups',
        sa.Column('assignee', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        'redteam_question_groups',
        sa.Column('model_answer', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('redteam_question_groups', 'model_answer')
    op.drop_column('redteam_question_groups', 'assignee')
    op.drop_column('redteam_question_groups', 'tags')
    op.drop_column('redteam_question_groups', 'disposition')
    op.drop_column('redteam_question_groups', 'level')
    op.drop_column('redteam_question_groups', 'status')
