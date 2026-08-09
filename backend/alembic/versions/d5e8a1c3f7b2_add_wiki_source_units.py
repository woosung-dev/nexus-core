"""add_wiki_source_units

Revision ID: d5e8a1c3f7b2
Revises: a1f6c30d84be
Create Date: 2026-08-09 03:10:00.000000

위키 원문(규정집·대사전 조문 250건)을 DB 로 옮긴다.

`app/services/wiki/store.py` 가 `exports/wiki_2026-08/` 를 파일시스템에서 직접 읽고 있었다.
그 디렉터리는 7.9MB 이고 `/exports` 는 gitignore 라 배포 이미지에 실리지 않는다 —
어휘 검색(`retrieval_mode="lexical"`)을 라이브에 붙이려면 원문이 DB 에 있어야 한다.

**두 테이블로 나눈 이유**: 디스크에서 `sources/<sha8>/` 는 봇과 무관하게 문서 단위로 공유되고
(`exports/wiki_2026-08/_split.py:11-13`) 봇별 구분은 manifest 가 한다. 또 `src_id` 만으로는
유일하지 않다 — 규정집이 v20→v21 로 올라가면 `reg-33` 이 둘이 된다. 유일키는 `(sha8, src_id)`.

**위키 페이지 138쪽도 담는다 — 답변 본문이 아니라 검색 신호로만 쓴다.** 위키 본문으로 답하는
팔 C 는 기각됐지만(§2-5), 페이지의 `## 사실` 문장 971개는 RRF 융합의 세 순위표 중 하나다.
빼고 45문항을 재보니 실제 주입 원문이 43/45 에서 달라졌고, reg-100(29,774자 부칙 모음)
주입이 1/45 → 19/45 로 늘어 3,000자 예산을 통째로 먹었다.

벡터는 담지 않는다 — BM25 전용이라 역색인이 기동 시 0.01초면 선다.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e8a1c3f7b2'
down_revision: Union[str, Sequence[str], None] = 'a1f6c30d84be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'wiki_source_units',
        sa.Column('id', sa.Integer(), nullable=False),
        # 원본 문서 sha256 앞 8자리. 판본을 가르는 유일한 값.
        sa.Column('sha8', sa.String(length=16), nullable=False),
        # 'reg-33' · 'glo-47'. 판본이 다르면 같은 값이 또 나온다.
        sa.Column('src_id', sa.String(length=32), nullable=False),
        sa.Column('doc', sa.String(length=64), nullable=False, server_default=''),
        sa.Column('locator', sa.String(length=255), nullable=False, server_default=''),
        # reg-100(부칙 모음)이 29,775자라 String 이 아니라 Text 여야 한다.
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('chars', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sha8', 'src_id', name='uq_wiki_source_unit_sha8_src_id'),
    )
    op.create_index(op.f('ix_wiki_source_units_sha8'), 'wiki_source_units', ['sha8'])
    op.create_index(op.f('ix_wiki_source_units_src_id'), 'wiki_source_units', ['src_id'])

    op.create_table(
        'wiki_bot_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bot_id', sa.Integer(), nullable=False),
        sa.Column('sha8', sa.String(length=16), nullable=False),
        # 'reg' · 'glo' — src_id 접두사와 같다.
        sa.Column('prefix', sa.String(length=16), nullable=False, server_default=''),
        sa.Column('doc', sa.String(length=64), nullable=False, server_default=''),
        # 업로드 원본 파일명. 어느 PDF 에서 나왔는지 추적용.
        sa.Column('display_name', sa.String(length=512), nullable=False, server_default=''),
        sa.Column('count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['bot_id'], ['bots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('bot_id', 'sha8', name='uq_wiki_bot_source_bot_sha8'),
    )
    op.create_index(op.f('ix_wiki_bot_sources_bot_id'), 'wiki_bot_sources', ['bot_id'])
    op.create_index(op.f('ix_wiki_bot_sources_sha8'), 'wiki_bot_sources', ['sha8'])

    # 페이지는 원문과 달리 봇별이다 — 같은 규정집에서 봇마다 다른 위키를 컴파일한다.
    op.create_table(
        'wiki_pages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bot_id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('summary', sa.Text(), nullable=False, server_default=''),
        # `## 사실` 절 전문. 줄 단위로 쪼개 fact 스케일(971건)이 된다.
        sa.Column('facts', sa.Text(), nullable=False, server_default=''),
        # 이 페이지가 인용하는 원문 src_id 목록
        sa.Column('sources', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['bot_id'], ['bots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('bot_id', 'slug', name='uq_wiki_page_bot_slug'),
    )
    op.create_index(op.f('ix_wiki_pages_bot_id'), 'wiki_pages', ['bot_id'])
    op.create_index(op.f('ix_wiki_pages_slug'), 'wiki_pages', ['slug'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_wiki_pages_slug'), table_name='wiki_pages')
    op.drop_index(op.f('ix_wiki_pages_bot_id'), table_name='wiki_pages')
    op.drop_table('wiki_pages')
    op.drop_index(op.f('ix_wiki_bot_sources_sha8'), table_name='wiki_bot_sources')
    op.drop_index(op.f('ix_wiki_bot_sources_bot_id'), table_name='wiki_bot_sources')
    op.drop_table('wiki_bot_sources')
    op.drop_index(op.f('ix_wiki_source_units_src_id'), table_name='wiki_source_units')
    op.drop_index(op.f('ix_wiki_source_units_sha8'), table_name='wiki_source_units')
    op.drop_table('wiki_source_units')
