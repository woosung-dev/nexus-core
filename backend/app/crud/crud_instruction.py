# 봇 지침 빌더의 데이터베이스 CRUD를 담당한다.

from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.instruction import BotInstruction


async def get_instruction(
    session: AsyncSession,
    instruction_id: int,
) -> BotInstruction | None:
    """지침 단일 조회"""
    result = await session.execute(
        select(BotInstruction).where(BotInstruction.id == instruction_id)
    )
    return result.scalar_one_or_none()


async def list_instructions(
    session: AsyncSession,
    bot_id: int | None = None,
) -> Sequence[BotInstruction]:
    """지침 목록 조회. bot_id가 있으면 해당 봇 지침만 반환한다."""
    statement = select(BotInstruction)
    if bot_id is not None:
        statement = statement.where(BotInstruction.bot_id == bot_id)

    result = await session.execute(statement.order_by(BotInstruction.updated_at.desc()))
    return result.scalars().all()


async def create_instruction(session: AsyncSession, data: dict) -> BotInstruction:
    """지침 생성"""
    instruction = BotInstruction(**data)
    session.add(instruction)
    await session.flush()
    await session.refresh(instruction)
    return instruction


async def update_instruction(
    session: AsyncSession,
    instruction: BotInstruction,
    update_data: dict,
) -> BotInstruction:
    """지침 부분 업데이트"""
    for key, value in update_data.items():
        setattr(instruction, key, value)

    session.add(instruction)
    await session.flush()
    await session.refresh(instruction)
    return instruction


async def delete_instruction(session: AsyncSession, instruction: BotInstruction) -> None:
    """지침 삭제"""
    await session.delete(instruction)
    await session.flush()
