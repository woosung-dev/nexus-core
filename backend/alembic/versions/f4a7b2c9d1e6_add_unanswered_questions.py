"""add_unanswered_questions

Revision ID: f4a7b2c9d1e6
Revises: 2e7f2e0417ec
Create Date: 2026-08-10 14:00:00.000000

못 답한 질문(unanswered_questions) — 「답변 못 함」이 데이터로 남는 자리.

지금은 챗봇이 「확인되지 않습니다 + 가정행복국」이라고 답해도 그 사실이 어디에도 안 남는다
(`messages` 10컬럼에 구분 컬럼이 없다). 그래서 관리자는 「무엇부터 채울지」를 알 수 없고,
`ops_facts` 는 코드·화면·승인 절차가 다 있는데 0행이다 — 채울 목록이 없기 때문이다.

`messages` 컬럼이 아니라 새 표인 이유는 모델 docstring 참조. 요지는 `triage`·`ops_fact_id`
가 메시지가 아니라 **질문 그룹**의 속성이라는 것이다.

`question_norm` 인덱스가 빈도 집계(GROUP BY)를 받친다. 라이브 실측에서 사용자 메시지의
74%가 이 정규화 후 정확히 중복이라, 임베딩 클러스터링 없이 빈도순 화면이 성립한다.
`created_at` 인덱스는 90일 보존 필터·삭제용이다.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'f4a7b2c9d1e6'
down_revision: Union[str, Sequence[str], None] = '2e7f2e0417ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'unanswered_questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bot_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('message_id', sa.Integer(), nullable=True),
        sa.Column('question_text', sa.Text(), nullable=False),
        # 빈도 집계 그룹핑 키 — unanswered.normalize_question() 의 결과
        sa.Column('question_norm', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        # empty_answer | lexical_empty | corpus_unavailable | self_refusal | judge_clarify
        sa.Column('reason', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('detail', sa.JSON(), nullable=False, server_default='{}'),
        # 미분류 | 문서없음 | 검색못함 | 문서오류 | 해당없음
        sa.Column('triage', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='미분류'),
        sa.Column('ops_fact_id', sa.Integer(), nullable=True),
        sa.Column('triaged_by', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('triaged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('admin_note', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['bot_id'], ['bots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        # 운영 사실이 지워져도 「무엇을 물어봤나」는 남아야 한다 — SET NULL
        sa.ForeignKeyConstraint(['ops_fact_id'], ['ops_facts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_unanswered_questions_bot_id'), 'unanswered_questions', ['bot_id'], unique=False)
    op.create_index(op.f('ix_unanswered_questions_question_norm'), 'unanswered_questions', ['question_norm'], unique=False)
    op.create_index(op.f('ix_unanswered_questions_reason'), 'unanswered_questions', ['reason'], unique=False)
    op.create_index(op.f('ix_unanswered_questions_triage'), 'unanswered_questions', ['triage'], unique=False)
    op.create_index(op.f('ix_unanswered_questions_created_at'), 'unanswered_questions', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_unanswered_questions_created_at'), table_name='unanswered_questions')
    op.drop_index(op.f('ix_unanswered_questions_triage'), table_name='unanswered_questions')
    op.drop_index(op.f('ix_unanswered_questions_reason'), table_name='unanswered_questions')
    op.drop_index(op.f('ix_unanswered_questions_question_norm'), table_name='unanswered_questions')
    op.drop_index(op.f('ix_unanswered_questions_bot_id'), table_name='unanswered_questions')
    op.drop_table('unanswered_questions')
