"""
Admin — FAQ 관리 API 엔드포인트.
봇별 FAQ CRUD 및 질문 임베딩 생성/갱신을 담당한다.
임베딩 생성(외부 AI API 호출)은 Router에서 수행 후 CRUD로 결과값을 주입한다.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import BotNotFoundError, NotFoundError
from app.crud import crud_bot, crud_faq
from app.schemas.faq import FaqCreateRequest, FaqListResponse, FaqResponse, FaqUpdateRequest
from app.services import faq_service

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
    bot = await crud_bot.get_bot(session, bot_id)
    if not bot:
        raise BotNotFoundError()

    faqs = await crud_faq.get_active_faqs_by_bot(session, bot_id)

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
    faq = await crud_faq.get_faq(session, faq_id)

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
    bot = await crud_bot.get_bot(session, bot_id)
    if not bot:
        raise BotNotFoundError()

    # 임베딩 생성 + DB 저장은 faq_service에서 조립
    faq = await faq_service.create_faq_with_embedding(
        session=session,
        bot_id=bot_id,
        question=request.question,
        answer=request.answer,
        threshold=request.threshold,
    )
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
    faq = await crud_faq.get_faq(session, faq_id)
    if not faq:
        raise NotFoundError("FAQ를 찾을 수 없습니다.")

    update_data = request.model_dump(exclude_unset=True)

    # 임베딩 재생성 포함 조립은 faq_service에서 처리
    faq = await faq_service.update_faq_with_embedding(session, faq, update_data)
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
    faq = await crud_faq.get_faq(session, faq_id)

    if not faq:
        raise NotFoundError("FAQ를 찾을 수 없습니다.")

    await crud_faq.soft_delete_faq(session, faq)

    logger.info(f"FAQ 비활성화: id={faq_id}")
