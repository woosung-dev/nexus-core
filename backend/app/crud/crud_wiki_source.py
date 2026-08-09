"""위키 원문 조회 — `app/services/wiki/store.py` 의 파일시스템 로더를 대신한다."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.wiki_source import WikiBotSource, WikiPageRow, WikiSourceUnit


async def get_bot_sources(session: AsyncSession, bot_id: int) -> list[WikiBotSource]:
    """봇에 연결된 문서 목록. `manifest.json` 의 sources 와 같은 것이다."""
    result = await session.execute(
        select(WikiBotSource).where(WikiBotSource.bot_id == bot_id).order_by(WikiBotSource.id)
    )
    return list(result.scalars().all())


async def get_units_for_bot(session: AsyncSession, bot_id: int) -> list[WikiSourceUnit]:
    """봇이 쓰는 문서들의 원문 조각 전부.

    두 단계로 나눈 이유는 `wiki_source_units` 가 문서 단위로 공유되기 때문이다 —
    봇 테이블과 조인하지 않고 sha8 목록으로 받아온다.
    """
    sources = await get_bot_sources(session, bot_id)
    if not sources:
        return []
    sha8s = [s.sha8 for s in sources]
    result = await session.execute(
        select(WikiSourceUnit)
        .where(WikiSourceUnit.sha8.in_(sha8s))  # type: ignore[attr-defined]
        .order_by(WikiSourceUnit.id)
    )
    return list(result.scalars().all())


async def get_pages_for_bot(session: AsyncSession, bot_id: int) -> list[WikiPageRow]:
    """봇의 위키 페이지. 답변 본문이 아니라 fact 스케일·페이지 역매핑을 만드는 검색 신호다."""
    result = await session.execute(
        select(WikiPageRow).where(WikiPageRow.bot_id == bot_id).order_by(WikiPageRow.slug)
    )
    return list(result.scalars().all())
