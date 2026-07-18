"""
용어집 관련 DB 연산을 담당하는 Repository.
"""

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.glossary import Glossary


async def get_glossary(session: AsyncSession, glossary_id: int) -> Glossary | None:
    """용어집 단일 조회"""
    result = await session.execute(select(Glossary).where(Glossary.id == glossary_id))
    return result.scalar_one_or_none()


async def get_active_glossary_for_bot(
    session: AsyncSession,
    bot_id: int,
) -> Sequence[Glossary]:
    """봇별 및 전역 활성 용어집 목록 조회"""
    result = await session.execute(
        select(Glossary)
        .where(
            Glossary.is_active == True,  # noqa: E712
            or_(Glossary.bot_id == bot_id, Glossary.bot_id.is_(None)),
        )
        .order_by(Glossary.priority.desc(), Glossary.id)
    )
    return result.scalars().all()


async def list_glossary(
    session: AsyncSession,
    bot_id: int | None = None,
    scope: str | None = None,
) -> Sequence[Glossary]:
    """관리자용 용어집 목록 조회"""
    statement = select(Glossary)
    if scope == "global":
        statement = statement.where(Glossary.bot_id.is_(None))
    elif bot_id is not None:
        statement = statement.where(
            or_(Glossary.bot_id == bot_id, Glossary.bot_id.is_(None))
        )
    result = await session.execute(statement.order_by(Glossary.priority.desc(), Glossary.id))
    return result.scalars().all()


async def create_glossary(session: AsyncSession, data: dict) -> Glossary:
    """용어집 생성"""
    glossary = Glossary(**data)
    session.add(glossary)
    await session.flush()
    await session.refresh(glossary)
    return glossary


async def update_glossary(
    session: AsyncSession,
    glossary: Glossary,
    update_data: dict,
) -> Glossary:
    """용어집 부분 업데이트"""
    for key, value in update_data.items():
        setattr(glossary, key, value)

    glossary.updated_at = datetime.now(timezone.utc)
    session.add(glossary)
    await session.flush()
    await session.refresh(glossary)
    return glossary


async def soft_delete_glossary(session: AsyncSession, glossary: Glossary) -> None:
    """용어집 비활성화 (소프트 삭제)"""
    glossary.is_active = False
    glossary.updated_at = datetime.now(timezone.utc)
    session.add(glossary)
    await session.flush()
