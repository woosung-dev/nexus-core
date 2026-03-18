"""
Bot 관련 DB 연산(CRUD)을 담당하는 Repository.
라우터(Controller)에서 비즈니스 로직과 DB 접근 코드를 분리하기 위해 사용합니다.
"""

from typing import Sequence

from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.bot import Bot
from app.schemas.bot import BotCreateRequest, BotUpdateRequest

async def get_bot(session: AsyncSession, bot_id: int) -> Bot | None:
    """봇 단일 조회 (활성화/비활성화 무관, 관리자용)"""
    result = await session.execute(select(Bot).where(Bot.id == bot_id))
    return result.scalar_one_or_none()

async def get_active_bot(session: AsyncSession, bot_id: int) -> Bot | None:
    """활성화된 봇 단일 조회 (클라이언트용)"""
    result = await session.execute(
        select(Bot).where(Bot.id == bot_id, Bot.is_active == True) # noqa: E712
    )
    return result.scalar_one_or_none()

async def get_all_bots(session: AsyncSession) -> Sequence[Bot]:
    """봇 전체 목록 조회 (관리자용)"""
    result = await session.execute(select(Bot).order_by(Bot.id))
    return result.scalars().all()

async def get_active_bots(session: AsyncSession, tag: str | None = None) -> Sequence[Bot]:
    """활성화된 봇 목록 조회 (클라이언트용). tag가 주어지면 DB 레벨에서 필터링."""
    statement = select(Bot).where(Bot.is_active == True)  # noqa: E712

    if tag:
        # PostgreSQL @> 연산자: JSONB 배열에 해당 값이 포함되는지 DB 레벨에서 검사
        statement = statement.where(
            cast(Bot.tags, JSONB).contains(cast([tag], JSONB))
        )

    result = await session.execute(statement)
    return result.scalars().all()

async def get_active_bot_categories(session: AsyncSession) -> list[str]:
    """모든 활성화된 봇의 태그 리스트를 가져와 유니크한 카테고리 목록 반환"""
    statement = select(Bot.tags).where(Bot.is_active == True)  # noqa: E712
    result = await session.execute(statement)
    tags_data = result.scalars().all()

    unique_tags = set()
    for tags in tags_data:
        if tags and isinstance(tags, list):
            for t in tags:
                unique_tags.add(t)

    return sorted(list(unique_tags))

async def create_bot(session: AsyncSession, request: BotCreateRequest) -> Bot:
    """새로운 봇 생성"""
    bot = Bot(**request.model_dump())
    session.add(bot)
    await session.flush()
    await session.refresh(bot)
    return bot

async def update_bot(session: AsyncSession, bot: Bot, request: BotUpdateRequest) -> Bot:
    """기존 봇 정보 수정"""
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(bot, key, value)
        
    session.add(bot)
    await session.flush()
    await session.refresh(bot)
    return bot

async def soft_delete_bot(session: AsyncSession, bot: Bot) -> Bot:
    """봇 소프트 삭제 (is_active = False)"""
    bot.is_active = False
    session.add(bot)
    await session.flush()
    return bot
