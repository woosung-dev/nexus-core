# BotKakaoChannel(오픈빌더 봇 ↔ 내부 봇) CRUD
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.bot_kakao_channel import BotKakaoChannel


async def get_by_kakao_bot_id(session: AsyncSession, kakao_bot_id: str) -> BotKakaoChannel | None:
    result = await session.execute(
        select(BotKakaoChannel).where(BotKakaoChannel.kakao_bot_id == kakao_bot_id)
    )
    return result.scalar_one_or_none()


async def list_by_bot(session: AsyncSession, bot_id: int) -> Sequence[BotKakaoChannel]:
    result = await session.execute(
        select(BotKakaoChannel).where(BotKakaoChannel.bot_id == bot_id)
    )
    return result.scalars().all()


async def create(session: AsyncSession, bot_id: int, kakao_bot_id: str) -> BotKakaoChannel:
    channel = BotKakaoChannel(bot_id=bot_id, kakao_bot_id=kakao_bot_id)
    session.add(channel)
    await session.flush()
    await session.refresh(channel)
    return channel


async def delete(session: AsyncSession, channel: BotKakaoChannel) -> None:
    await session.delete(channel)
    await session.flush()
