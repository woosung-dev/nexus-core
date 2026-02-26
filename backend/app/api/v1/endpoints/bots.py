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
