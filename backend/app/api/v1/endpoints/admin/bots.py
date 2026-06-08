"""
Admin — 봇 관리 API 엔드포인트.
봇 CRUD, 이미지 업로드, RAG 문서 관리를 담당한다.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.exceptions import BotNotFoundError, NotFoundError, ValidationError
from app.crud import crud_bot, crud_bot_kakao_channel
from app.schemas.bot import BotCreateRequest, BotListResponse, BotResponse, BotUpdateRequest, BotImageUploadResponse
from app.schemas.bot_kakao_channel import (
    KakaoChannelCreateRequest,
    KakaoChannelListResponse,
    KakaoChannelResponse,
)
from app.schemas.rag import DocumentListResponse, DocumentUploadResponse
from app.services import bot_service
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
    파일 검증 · 스토리지 업로드 · DB 갱신은 bot_service에서 처리한다.
    """
    file_data = await file.read()
    content_type = file.content_type or "application/octet-stream"
    filename = file.filename or "unknown_image.png"

    public_url = await bot_service.upload_bot_image(
        session=session,
        storage=storage,
        bot_id=bot_id,
        file_data=file_data,
        filename=filename,
        content_type=content_type,
    )
    return BotImageUploadResponse(bot_id=bot_id, image_url=public_url)


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
    replace: bool = False,
    session: AsyncSession = Depends(get_session),
    storage: FileStorageService = Depends(get_storage_service),
) -> DocumentUploadResponse:
    """
    봇 전용 참고 문서 업로드.
    스토리지에 저장 후 RAG Store에 메타데이터(bot_id) 포함 업로드.

    replace=False(기본): append 업로드(기존 동작). 동일 문서를 반복 업로드하면 중복 누적.
    replace=True: 동일 (display_name, bot_id) 구버전을 안전 교체(신규 업로드 성공 후 구버전 삭제).
        라이브 RAG 중복 정리 시 명시적으로 켠다(묵시적 파괴 동작 방지).
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

    # 스토리지 업로드 (구현체에 따라 로컬/R2로 분기)
    await storage.upload(
        file_data=file_data,
        filename=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
    )

    # File Search Store에 업로드 (바이너리 데이터를 직접 전달)
    rag = get_rag_service(provider=bot.llm_model)
    display_name = file.filename or "unknown"

    upload_fn = rag.replace_document if replace else rag.upload_document
    await upload_fn(
        bot_id=bot_id,
        file_data=file_data,
        filename=display_name,
        display_name=display_name,
        mime_type=file.content_type,
    )

    logger.info(
        f"봇 문서 업로드 완료: bot_id={bot_id}, file={display_name}, "
        f"provider={bot.llm_model}, replace={replace}"
    )

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


# ── 카카오 채널 매핑 ───────────────────────────────────────────────────


@router.get("/bots/{bot_id}/kakao", response_model=KakaoChannelListResponse, tags=["Admin - 봇 관리"])
async def list_kakao_channels(
    bot_id: int,
    session: AsyncSession = Depends(get_session),
) -> KakaoChannelListResponse:
    """봇에 등록된 카카오 채널(오픈빌더 bot.id) 목록."""
    bot = await crud_bot.get_bot(session, bot_id)
    if not bot:
        raise BotNotFoundError()
    channels = await crud_bot_kakao_channel.list_by_bot(session, bot_id)
    return KakaoChannelListResponse(
        items=[KakaoChannelResponse.model_validate(c) for c in channels],
        total=len(channels),
    )


@router.post(
    "/bots/{bot_id}/kakao",
    response_model=KakaoChannelResponse,
    status_code=201,
    tags=["Admin - 봇 관리"],
)
async def create_kakao_channel(
    bot_id: int,
    request: KakaoChannelCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> KakaoChannelResponse:
    """봇에 카카오 채널(오픈빌더 bot.id) 등록."""
    bot = await crud_bot.get_bot(session, bot_id)
    if not bot:
        raise BotNotFoundError()
    try:
        channel = await crud_bot_kakao_channel.create(session, bot_id, request.kakao_bot_id)
    except IntegrityError:
        await session.rollback()
        raise ValidationError("이미 등록된 카카오 봇 ID 입니다.")
    logger.info("카카오 채널 등록: bot_id=%s kakao_bot_id=%s", bot_id, channel.kakao_bot_id)
    return KakaoChannelResponse.model_validate(channel)


@router.delete("/bots/{bot_id}/kakao/{channel_id}", status_code=204, tags=["Admin - 봇 관리"])
async def delete_kakao_channel(
    bot_id: int,
    channel_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """카카오 채널 매핑 삭제."""
    bot = await crud_bot.get_bot(session, bot_id)
    if not bot:
        raise BotNotFoundError()
    channels = await crud_bot_kakao_channel.list_by_bot(session, bot_id)
    target = next((c for c in channels if c.id == channel_id), None)
    if target is None:
        raise NotFoundError("카카오 채널을 찾을 수 없습니다.")
    await crud_bot_kakao_channel.delete(session, target)
    logger.info("카카오 채널 삭제: id=%s", channel_id)
