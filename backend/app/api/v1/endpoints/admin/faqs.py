"""
Admin — FAQ 관리 API 엔드포인트.
봇별 FAQ CRUD 및 질문 임베딩 생성/갱신을 담당한다.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.core.exceptions import BotNotFoundError, NotFoundError, NexusException
from app.crud import crud_bot
from app.models.faq import Faq
from app.schemas.faq import FaqCreateRequest, FaqListResponse, FaqResponse, FaqUpdateRequest
from app.utils.embeddings import get_embedding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/bots/{bot_id}/faqs",
    response_model=FaqListResponse,
    tags=["Admin - FAQ 관리"],
)
async def list_faqs(
    bot_id: int,
    session: AsyncSession = Depends(get_session),
) -> FaqListResponse:
    """봇별 활성 FAQ 목록 조회"""
    # 봇 존재 확인
    bot = await crud_bot.get_bot(session, bot_id)
    if not bot:
        raise BotNotFoundError()

    result = await session.execute(
        select(Faq)
        .where(Faq.bot_id == bot_id, Faq.is_active == True)  # noqa: E712
        .order_by(Faq.id)
    )
    faqs = result.scalars().all()

    return FaqListResponse(
        faqs=[FaqResponse.model_validate(faq) for faq in faqs],
        total=len(faqs),
    )


@router.get(
    "/faqs/{faq_id}",
    response_model=FaqResponse,
    tags=["Admin - FAQ 관리"],
)
async def get_faq(
    faq_id: int,
    session: AsyncSession = Depends(get_session),
) -> FaqResponse:
    """FAQ 단일 조회"""
    result = await session.execute(select(Faq).where(Faq.id == faq_id))
    faq = result.scalar_one_or_none()

    if not faq:
        raise NotFoundError("FAQ를 찾을 수 없습니다.")

    return FaqResponse.model_validate(faq)


@router.post(
    "/bots/{bot_id}/faqs",
    response_model=FaqResponse,
    status_code=201,
    tags=["Admin - FAQ 관리"],
)
async def create_faq(
    bot_id: int,
    request: FaqCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> FaqResponse:
    """
    FAQ 등록.
    질문 텍스트를 gemini-embedding-001로 임베딩하여 question_vector에 저장한다.
    """
    # 봇 존재 확인
    bot = await crud_bot.get_bot(session, bot_id)
    if not bot:
        raise BotNotFoundError()

    # 질문 임베딩 생성
    try:
        vector = await get_embedding(request.question)
    except RuntimeError as e:
        raise NexusException(
            error_code="EMBEDDING_FAILED",
            message="임베딩 생성 중 오류가 발생했습니다.",
            status_code=502,
            details=str(e)
        )

    faq = Faq(
        bot_id=bot_id,
        question=request.question,
        answer=request.answer,
        threshold=request.threshold,
        question_vector=vector,
    )
    session.add(faq)
    await session.flush()
    await session.refresh(faq)

    logger.info(f"FAQ 등록: id={faq.id}, bot_id={bot_id}, question='{faq.question[:30]}'")
    return FaqResponse.model_validate(faq)


@router.put(
    "/faqs/{faq_id}",
    response_model=FaqResponse,
    tags=["Admin - FAQ 관리"],
)
async def update_faq(
    faq_id: int,
    request: FaqUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> FaqResponse:
    """
    FAQ 수정 (부분 업데이트).
    question이 변경된 경우 임베딩을 자동으로 재생성한다.
    """
    result = await session.execute(select(Faq).where(Faq.id == faq_id))
    faq = result.scalar_one_or_none()

    if not faq:
        raise NotFoundError("FAQ를 찾을 수 없습니다.")

    update_data = request.model_dump(exclude_unset=True)

    # 질문이 변경된 경우 임베딩 재생성
    if "question" in update_data and update_data["question"] != faq.question:
        try:
            update_data["question_vector"] = await get_embedding(update_data["question"])
        except RuntimeError as e:
            raise NexusException(
                error_code="EMBEDDING_FAILED",
                message="임베딩 재생성 중 오류가 발생했습니다.",
                status_code=502,
                details=str(e)
            )

    for key, value in update_data.items():
        setattr(faq, key, value)

    faq.updated_at = datetime.utcnow()
    session.add(faq)
    await session.flush()
    await session.refresh(faq)

    logger.info(f"FAQ 수정: id={faq_id}, changes={list(update_data.keys())}")
    return FaqResponse.model_validate(faq)


@router.delete(
    "/faqs/{faq_id}",
    status_code=204,
    tags=["Admin - FAQ 관리"],
)
async def delete_faq(
    faq_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """FAQ 비활성화 (소프트 삭제 — is_active=False)"""
    result = await session.execute(select(Faq).where(Faq.id == faq_id))
    faq = result.scalar_one_or_none()

    if not faq:
        raise NotFoundError("FAQ를 찾을 수 없습니다.")

    faq.is_active = False
    faq.updated_at = datetime.utcnow()
    session.add(faq)

    logger.info(f"FAQ 비활성화: id={faq_id}")
