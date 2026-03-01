"""
봇 목록 API 엔드포인트.
"""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.models.bot import Bot
from app.schemas.bot import BotListResponse, BotResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bots", tags=["봇"])


@router.get("", response_model=BotListResponse)
async def list_bots(
    tag: str | None = Query(None, description="태그 필터 (예: Coding, Writing)"),
    session: AsyncSession = Depends(get_session),
) -> BotListResponse:
    """
    봇 목록 조회.
    활성화(is_active=True)된 봇만 반환한다.
    """
    statement = select(Bot).where(Bot.is_active == True)  # noqa: E712

    result = await session.execute(statement)
    bots = result.scalars().all()

    # 태그 필터링 (JSON 배열 내 검색)
    if tag:
        bots = [b for b in bots if tag in (b.tags or [])]

    bot_responses = [BotResponse.model_validate(b) for b in bots]

    return BotListResponse(bots=bot_responses, total=len(bot_responses))


@router.get("/categories", response_model=list[str])
async def list_bot_categories(
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    """
    등록된 봇들의 모든 태그(tags)를 수합하여 유니크한 카테고리 목록을 반환한다.
    """
    # 모든 활성화된 봇의 태그 리스트를 가져옴
    statement = select(Bot.tags).where(Bot.is_active == True)  # noqa: E712
    result = await session.execute(statement)
    tags_data = result.scalars().all()

    unique_tags = set()
    for tags in tags_data:
        if tags and isinstance(tags, list):
            for t in tags:
                unique_tags.add(t)

    # 가나다순 정렬하여 반환
    return sorted(list(unique_tags))
