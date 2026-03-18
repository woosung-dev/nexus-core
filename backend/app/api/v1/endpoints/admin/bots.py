"""
Admin — 봇 관리 API 엔드포인트.
봇 CRUD, 이미지 업로드, RAG 문서 관리를 담당한다.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.exceptions import BotNotFoundError, NotFoundError, ValidationError
from app.crud import crud_bot
from app.schemas.bot import BotCreateRequest, BotListResponse, BotResponse, BotUpdateRequest, BotImageUploadResponse
from app.schemas.rag import DocumentListResponse, DocumentUploadResponse
from app.services.rag.factory import get_rag_service
from app.services.storage.base import FileStorageService
from app.services.storage.factory import get_storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── 봇 CRUD ───────────────────────────────────────────────────


@router.get("/bots", response_model=BotListResponse, tags=["Admin - 봇 관리"])
async def list_bots(
    session: AsyncSession = Depends(get_session),
) -> BotListResponse:
    """봇 전체 목록 조회 (활성/비활성 모두)"""
    bots = await crud_bot.get_all_bots(session)

    return BotListResponse(
        bots=[BotResponse.model_validate(bot) for bot in bots],
        total=len(bots),
    )


@router.get("/bots/{bot_id}", response_model=BotResponse, tags=["Admin - 봇 관리"])
async def get_bot(
    bot_id: int,
    session: AsyncSession = Depends(get_session),
) -> BotResponse:
    """봇 단일 상세 조회"""
    bot = await crud_bot.get_bot(session, bot_id)

    if not bot:
        raise BotNotFoundError()

    return BotResponse.model_validate(bot)


@router.post("/bots", response_model=BotResponse, status_code=201, tags=["Admin - 봇 관리"])
async def create_bot(
    request: BotCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> BotResponse:
    """봇 생성"""
    bot = await crud_bot.create_bot(session, request)

    logger.info(f"봇 생성: id={bot.id}, name={bot.name}")
    return BotResponse.model_validate(bot)


@router.put("/bots/{bot_id}", response_model=BotResponse, tags=["Admin - 봇 관리"])
async def update_bot(
    bot_id: int,
    request: BotUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> BotResponse:
    """봇 수정 (부분 업데이트)"""
    bot = await crud_bot.get_bot(session, bot_id)

    if not bot:
        raise BotNotFoundError()

    bot = await crud_bot.update_bot(session, bot, request)

    logger.info(f"봇 수정: id={bot.id}")
    return BotResponse.model_validate(bot)


@router.delete("/bots/{bot_id}", status_code=204, tags=["Admin - 봇 관리"])
async def delete_bot(
    bot_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """봇 삭제 (소프트 삭제 — is_active=False)"""
    bot = await crud_bot.get_bot(session, bot_id)

    if not bot:
        raise BotNotFoundError()

    await crud_bot.soft_delete_bot(session, bot)

    logger.info(f"봇 비활성화: id={bot.id}")


# ── 봇 이미지 업로드 ───────────────────────────────────────────────────


@router.post(
    "/bots/{bot_id}/image",
    response_model=BotImageUploadResponse,
    status_code=201,
    tags=["Admin - 봇 관리"],
)
async def upload_bot_image(
    bot_id: int,
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
    storage: FileStorageService = Depends(get_storage_service),
) -> BotImageUploadResponse:
    """
    봇 메인 대표 이미지(아이콘) 업로드.
    스토리지에 저장 후 봇의 `image_url` 필드를 업데이트한다.
    """
    # 봇 존재 확인
    bot = await crud_bot.get_bot(session, bot_id)
    if not bot:
        raise BotNotFoundError()

    # 파일 크기 제한 확인
    settings = get_settings()
    file_data = await file.read()
    if len(file_data) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"파일 크기가 {settings.MAX_UPLOAD_SIZE_MB}MB를 초과합니다.")

    # 단순 확장자 검증 (이미지 한정)
    content_type = file.content_type or "application/octet-stream"
    if not content_type.startswith("image/"):
        raise ValidationError("이미지 파일만 업로드 가능합니다.")

    # 스토리지 업로드 (구현체에 따라 로컬/Supabase/R2로 분기)
    public_url = await storage.upload(
        file_data=file_data,
        filename=file.filename or "unknown_image.png",
        content_type=content_type,
    )

    # DB 업데이트
    bot.image_url = public_url
    bot.updated_at = datetime.now(timezone.utc)
    session.add(bot)
    await session.commit()
    await session.refresh(bot)

    logger.info(f"봇 이미지 업로드 완료: bot_id={bot_id}, url={public_url}")

    return BotImageUploadResponse(
        bot_id=bot_id,
        image_url=public_url,
    )


# ── 봇 문서 관리 (RAG) ────────────────────────────────────────────────


@router.get(
    "/bots/{bot_id}/documents",
    response_model=DocumentListResponse,
    tags=["Admin - 봇 관리"],
)
async def list_bot_documents(
    bot_id: int,
    session: AsyncSession = Depends(get_session),
) -> DocumentListResponse:
    """
    봇 전용 문서 목록 조회.
    해당 봇에 업로드된 모든 RAG 참고 문서의 목록을 반환한다.
    """
    # 봇 존재 확인 — 기존 crud_bot.get_bot 재사용
    bot = await crud_bot.get_bot(session, bot_id)
    if not bot:
        raise BotNotFoundError()

    # RAG 서비스에서 문서 목록 조회
    rag = get_rag_service(provider=bot.llm_model)
    documents = await rag.list_documents(bot_id=bot_id)

    logger.info(f"봇 문서 목록 조회: bot_id={bot_id}, count={len(documents)}")

    return DocumentListResponse(
        bot_id=bot_id,
        documents=documents,
        total=len(documents),
    )


@router.post(
    "/bots/{bot_id}/documents",
    response_model=DocumentUploadResponse,
    status_code=201,
    tags=["Admin - 봇 관리"],
)
async def upload_bot_document(
    bot_id: int,
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
    storage: FileStorageService = Depends(get_storage_service),
) -> DocumentUploadResponse:
    """
    봇 전용 참고 문서 업로드.
    스토리지에 저장 후 RAG Store에 메타데이터(bot_id) 포함 업로드.
    """
    # 봇 존재 확인
    bot = await crud_bot.get_bot(session, bot_id)
    if not bot:
        raise BotNotFoundError()

    # 파일 크기 제한 확인
    settings = get_settings()
    file_data = await file.read()
    if len(file_data) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"파일 크기가 {settings.MAX_UPLOAD_SIZE_MB}MB를 초과합니다.")

    # 스토리지 업로드 (구현체에 따라 로컬/Supabase/R2로 분기)
    await storage.upload(
        file_data=file_data,
        filename=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
    )

    # File Search Store에 업로드 (바이너리 데이터를 직접 전달)
    rag = get_rag_service(provider=bot.llm_model)
    display_name = file.filename or "unknown"

    await rag.upload_document(
        bot_id=bot_id,
        file_data=file_data,
        filename=display_name,
        display_name=display_name,
        mime_type=file.content_type,
    )

    logger.info(f"봇 문서 업로드 완료: bot_id={bot_id}, file={display_name}, provider={bot.llm_model}")

    return DocumentUploadResponse(
        file_name=file.filename or "unknown",
        display_name=display_name,
        bot_id=bot_id,
    )


@router.delete("/bots/{bot_id}/documents/{file_id}", status_code=204, tags=["Admin - 봇 관리"])
async def delete_bot_document(
    bot_id: int,
    file_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    봇 전용 문서 삭제.
    RAG Store에서 해당 문서를 제거한다.
    """
    # 봇 존재 확인
    bot = await crud_bot.get_bot(session, bot_id)
    if not bot:
        raise BotNotFoundError()

    # RAG 서비스에서 문서 삭제
    rag = get_rag_service(provider=bot.llm_model)
    try:
        await rag.delete_document(bot_id=bot_id, file_id=file_id)
    except ValueError as e:
        raise NotFoundError(str(e))

    logger.info(f"봇 문서 삭제 완료: bot_id={bot_id}, file_id={file_id}")
