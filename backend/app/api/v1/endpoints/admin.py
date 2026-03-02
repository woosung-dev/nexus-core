"""
Admin 봇/사용자 관리 API 엔드포인트.
관리자 프론트엔드에서 호출하는 CRUD API.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import get_settings
from app.core.database import get_session
from app.models.bot import Bot
from app.models.user import User
from app.schemas.bot import BotCreateRequest, BotListResponse, BotResponse, BotUpdateRequest, BotImageUploadResponse
from app.schemas.rag import DocumentListResponse, DocumentUploadResponse
from app.schemas.user import UserAdminUpdateRequest, UserListResponse, UserResponse
from app.services.rag.factory import get_rag_service
from app.services.storage.local import LocalFileStorage
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/bots", response_model=BotListResponse, tags=["Admin - 봇 관리"])
async def list_bots(
    session: AsyncSession = Depends(get_session),
) -> BotListResponse:
    """봇 전체 목록 조회 (활성 봇만)"""
    result = await session.execute(
        select(Bot).where(Bot.is_active == True).order_by(Bot.id)
    )
    bots = result.scalars().all()

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
    result = await session.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()

    if not bot:
        raise HTTPException(status_code=404, detail="봇을 찾을 수 없습니다.")

    return BotResponse.model_validate(bot)


@router.post("/bots", response_model=BotResponse, status_code=201, tags=["Admin - 봇 관리"])
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


@router.put("/bots/{bot_id}", response_model=BotResponse, tags=["Admin - 봇 관리"])
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


@router.delete("/bots/{bot_id}", status_code=204, tags=["Admin - 봇 관리"])
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
    "/bots/{bot_id}/image",
    response_model=BotImageUploadResponse,
    status_code=201,
    tags=["Admin - 봇 관리"],
)
async def upload_bot_image(
    bot_id: int,
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
) -> BotImageUploadResponse:
    """
    봇 메인 대표 이미지(아이콘) 업로드.
    로컬에 저장 후 봇의 `image_url` 필드를 업데이트한다.
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

    # 단순 확장자 검증 (이미지 한정)
    content_type = file.content_type or "application/octet-stream"
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다.")

    # 로컬 저장
    storage = LocalFileStorage()
    local_path = await storage.upload(
        file_data=file_data,
        filename=file.filename or "unknown_image.png",
        content_type=content_type,
    )

    # 프론트엔드가 접근 가능한 정적 서빙 경로 URL 생성 ("/uploads/...")
    # *storage.upload()는 "uploads/~~"를 반환하므로, 앞에 "/static/"를 붙이거나 
    # FastAPI mount 경로와 일치하도록 가공합니다.
    # main.py에서 mount("/static/uploads", directory="uploads") 기준
    # file_path에서 'uploads/' 제거하고 조합
    relative_path = local_path.replace("uploads/", "")
    public_url = f"/static/uploads/{relative_path}"

    # DB 업데이트
    bot.image_url = public_url
    bot.updated_at = datetime.utcnow()
    session.add(bot)
    await session.commit()
    await session.refresh(bot)

    logger.info(f"봇 이미지 업로드 완료: bot_id={bot_id}, url={public_url}")

    return BotImageUploadResponse(
        bot_id=bot_id,
        image_url=public_url,
    )

# ── 문서 관리 ──────────────────────────────────────────────

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
    # 봇 존재 확인
    result = await session.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=404, detail="봇을 찾을 수 없습니다.")

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
) -> DocumentUploadResponse:
    """
    봇 전용 참고 문서 업로드.
    로컬에 저장 후 RAG Store에 메타데이터(bot_id) 포함 업로드.
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
    result = await session.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=404, detail="봇을 찾을 수 없습니다.")

    # RAG 서비스에서 문서 삭제
    rag = get_rag_service(provider=bot.llm_model)
    try:
        await rag.delete_document(bot_id=bot_id, file_id=file_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    logger.info(f"봇 문서 삭제 완료: bot_id={bot_id}, file_id={file_id}")


# ── 사용자 관리 ────────────────────────────────────────────────


@router.get("/users", response_model=UserListResponse, tags=["Admin - 사용자 관리"])
async def list_users(
    email: str | None = Query(None, description="이메일 검색어"),
    plan_type: str | None = Query(None, description="플랜 필터 (FREE/PRO)"),
    session: AsyncSession = Depends(get_session),
) -> UserListResponse:
    """
    전체 사용자 목록 조회.
    이메일 검색 및 플랜 타입 필터링을 지원한다.
    """
    statement = select(User)

    # 이메일 검색 (부분 일치)
    if email:
        statement = statement.where(User.email.ilike(f"%{email}%"))  # type: ignore[attr-defined]

    # 플랜 타입 필터
    if plan_type:
        statement = statement.where(User.plan_type == plan_type)

    statement = statement.order_by(User.created_at.desc())  # type: ignore[attr-defined]

    result = await session.execute(statement)
    users = result.scalars().all()

    return UserListResponse(
        users=[UserResponse.model_validate(u) for u in users],
        total=len(users),
    )


@router.patch("/users/{user_id}", response_model=UserResponse, tags=["Admin - 사용자 관리"])
async def update_user(
    user_id: int,
    request: UserAdminUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """
    사용자 정보 수정 (부분 업데이트).
    plan_type 및 is_active 변경을 지원한다.
    """
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    # None이 아닌 필드만 업데이트
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    session.add(user)
    await session.commit()
    await session.refresh(user)

    logger.info(f"사용자 수정: id={user_id}, changes={update_data}")
    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}", status_code=204, tags=["Admin - 사용자 관리"])
async def deactivate_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    사용자 비활성화 (소프트 삭제 — is_active=False).
    실제 DB 레코드는 유지하여 데이터 무결성을 보장한다.
    """
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    user.is_active = False
    session.add(user)
    await session.commit()

    logger.info(f"사용자 비활성화: id={user_id}")
