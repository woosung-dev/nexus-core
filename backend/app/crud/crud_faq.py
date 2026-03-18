"""
FAQ 관련 DB 연산(CRUD)을 담당하는 Repository.
임베딩 벡터는 서비스/라우터 계층에서 생성 후 주입받는다.
"""

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.faq import Faq


async def get_faq(session: AsyncSession, faq_id: int) -> Faq | None:
    """FAQ 단일 조회"""
    result = await session.execute(select(Faq).where(Faq.id == faq_id))
    return result.scalar_one_or_none()


async def get_active_faqs_by_bot(session: AsyncSession, bot_id: int) -> Sequence[Faq]:
    """봇별 활성 FAQ 목록 조회 (is_active=True만 반환)"""
    result = await session.execute(
        select(Faq)
        .where(Faq.bot_id == bot_id, Faq.is_active == True)  # noqa: E712
        .order_by(Faq.id)
    )
    return result.scalars().all()


async def create_faq(
    session: AsyncSession,
    bot_id: int,
    question: str,
    answer: str,
    threshold: float,
    question_vector: list[float],
) -> Faq:
    """FAQ 생성. 임베딩 벡터는 호출 측에서 미리 생성하여 주입한다."""
    faq = Faq(
        bot_id=bot_id,
        question=question,
        answer=answer,
        threshold=threshold,
        question_vector=question_vector,
    )
    session.add(faq)
    await session.flush()
    await session.refresh(faq)
    return faq


async def update_faq(session: AsyncSession, faq: Faq, update_data: dict) -> Faq:
    """FAQ 부분 업데이트. update_data는 호출 측에서 exclude_unset 적용 후 주입한다."""
    for key, value in update_data.items():
        setattr(faq, key, value)

    faq.updated_at = datetime.now(timezone.utc)
    session.add(faq)
    await session.flush()
    await session.refresh(faq)
    return faq


async def soft_delete_faq(session: AsyncSession, faq: Faq) -> None:
    """FAQ 비활성화 (소프트 삭제 — is_active=False)"""
    faq.is_active = False
    faq.updated_at = datetime.now(timezone.utc)
    session.add(faq)
    await session.flush()
