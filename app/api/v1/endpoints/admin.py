"""
Admin 봇 관리 API 엔드포인트.
관리자 프론트엔드에서 호출하는 CRUD API.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import get_settings
from app.core.database import get_session
from app.models.bot import Bot
from app.schemas.bot import BotCreateRequest, BotResponse, BotUpdateRequest
from app.schemas.rag import DocumentUploadResponse
from app.services.rag.factory import get_rag_service
from app.services.storage.local import LocalFileStorage
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/bots", tags=["Admin - 봇 관리"])


@router.post("", response_model=BotResponse, status_code=201)
async def create_bot(
    request: BotCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> BotResponse:
    """봇 생성"""
    bot = Bot(**request.model_dump())
    session.add(bot)
    await session.flush()
    await session.refresh(bot)

    logger.info(f"봇 생성: id={bot.id}, name={bot.name}")
    return BotResponse.model_validate(bot)


@router.put("/{bot_id}", response_model=BotResponse)
async def update_bot(
    bot_id: int,
    request: BotUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> BotResponse:
    """봇 수정 (부분 업데이트)"""
    result = await session.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()

    if not bot:
        raise HTTPException(status_code=404, detail="봇을 찾을 수 없습니다.")

    # None이 아닌 필드만 업데이트
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(bot, key, value)

    bot.updated_at = datetime.utcnow()
    session.add(bot)
    await session.flush()
    await session.refresh(bot)

    logger.info(f"봇 수정: id={bot.id}")
    return BotResponse.model_validate(bot)


@router.delete("/{bot_id}", status_code=204)
async def delete_bot(
    bot_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """봇 삭제 (소프트 삭제 — is_active=False)"""
    result = await session.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()

    if not bot:
        raise HTTPException(status_code=404, detail="봇을 찾을 수 없습니다.")

    bot.is_active = False
    bot.updated_at = datetime.utcnow()
    session.add(bot)

    logger.info(f"봇 비활성화: id={bot.id}")


@router.post(
    "/{bot_id}/documents",
    response_model=DocumentUploadResponse,
    status_code=201,
)
async def upload_bot_document(
    bot_id: int,
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
) -> DocumentUploadResponse:
    """
    봇 전용 참고 문서 업로드.
    로컬에 저장 후 Google File Search Store에 메타데이터(bot_id) 포함 업로드.
    """
    # 봇 존재 확인
    result = await session.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=404, detail="봇을 찾을 수 없습니다.")

    # 파일 크기 제한 확인
    settings = get_settings()
    file_data = await file.read()
    if len(file_data) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"파일 크기가 {settings.MAX_UPLOAD_SIZE_MB}MB를 초과합니다.",
        )

    # 로컬 저장
    storage = LocalFileStorage()
    local_path = await storage.upload(
        file_data=file_data,
        filename=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
    )

    # File Search Store에 업로드
    rag = get_rag_service(provider=bot.llm_model)
    display_name = file.filename or "unknown"
    await rag.upload_document(
        bot_id=bot_id,
        file_path=local_path,
        display_name=display_name,
    )

    logger.info(f"봇 문서 업로드 완료: bot_id={bot_id}, file={display_name}, provider={bot.llm_model}")

    return DocumentUploadResponse(
        file_name=file.filename or "unknown",
        display_name=display_name,
        bot_id=bot_id,
    )
