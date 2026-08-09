"""add_ops_facts

Revision ID: a1f6c30d84be
Revises: 7c04bb6da692
Create Date: 2026-08-07 10:00:00.000000

운영 사실(ops_facts) 테이블 — 문서가 답해주지 않는 확정 사실.

규정집·공문은 "폐지된 기준"을 폐지됐다고 말해주지 않는다. 그래서 RAG 를 고쳐도
버전 드리프트는 남는다 (실측: 프롬프트 4종 × 2회 = 8/8 오답,
`exports/prompt4_2026-08-05/FINDINGS.md` §2-3).

이 표는 그 공백만 메운다 — "쓰면 안 되는 것 → 대신 쓸 것" 만 담고,
positive 지식은 담지 않는다. 런타임은 status ∈ (승인, 수정승인) 만 읽으므로
초안이 사용자에게 닿지 않는다. 회귀 하네스(exports/regression/_l2.py)도 같은 행을 읽어
제품과 채점 기준이 갈라지지 않게 한다.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a1f6c30d84be'
down_revision: Union[str, Sequence[str], None] = '7c04bb6da692'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'ops_facts',
        sa.Column('id', sa.Integer(), nullable=False),
        # NULL = 전역(모든 봇). glossary_terms 와 같은 규약.
        sa.Column('bot_id', sa.Integer(), nullable=True),
        # deprecated | forbidden | term | contact | crisis
        sa.Column('kind', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('superseded', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('statement', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        # 비면 항상 주입, 값이 있으면 질문에 그 표현이 있을 때만 주입
        sa.Column('triggers', sa.JSON(), nullable=False, server_default='[]'),
        # 채점기(L2)가 응답에서 이 사실 위반을 찾을 정규식. 비면 superseded 문자열 포함으로 본다.
        sa.Column('detect', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('evidence', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('source_docs', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        # 초안 | 승인 | 수정승인 | 반려
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='초안'),
        sa.Column('approver', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('admin_note', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('draft_statement', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['bot_id'], ['bots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ops_facts_bot_id'), 'ops_facts', ['bot_id'], unique=False)
    op.create_index(op.f('ix_ops_facts_kind'), 'ops_facts', ['kind'], unique=False)
    op.create_index(op.f('ix_ops_facts_status'), 'ops_facts', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_ops_facts_status'), table_name='ops_facts')
    op.drop_index(op.f('ix_ops_facts_kind'), table_name='ops_facts')
    op.drop_index(op.f('ix_ops_facts_bot_id'), table_name='ops_facts')
    op.drop_table('ops_facts')
