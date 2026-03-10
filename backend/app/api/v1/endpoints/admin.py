"""
Admin 봇/사용자 관리 API 엔드포인트.
관리자 프론트엔드에서 호출하는 CRUD API.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query, UploadFile
from app.core.exceptions import BotNotFoundError, NotFoundError, ValidationError, NexusException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col, func

from app.core.config import get_settings
from app.core.database import get_session
from app.crud import crud_bot
from app.models.bot import Bot
from app.models.chat import ChatSession, Message
from app.models.faq import Faq
from app.models.user import User
from app.models.enums import PlanType
from app.schemas.bot import BotCreateRequest, BotListResponse, BotResponse, BotUpdateRequest, BotImageUploadResponse
from app.schemas.chat import (
    ChatSessionAdminResponse, 
    ChatSessionAdminListResponse,
    MessageResponse,
    FeedbackMessageListResponse,
    FeedbackMessageResponse
)
from app.schemas.faq import FaqCreateRequest, FaqListResponse, FaqResponse, FaqUpdateRequest
from app.schemas.rag import DocumentListResponse, DocumentUploadResponse
from app.schemas.user import UserAdminUpdateRequest, UserListResponse, UserResponse
from app.services.rag.factory import get_rag_service
from app.services.storage.base import FileStorageService
from app.services.storage.factory import get_storage_service
from app.utils.embeddings import get_embedding
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


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
    stored_path = await storage.upload(
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
        statement = statement.where(col(User.email).ilike(f"%{email}%"))  # type: ignore[attr-defined]

    # 플랜 타입 필터
    if plan_type:
        statement = statement.where(User.plan_type == plan_type)

    statement = statement.order_by(col(User.created_at).desc())  # type: ignore[attr-defined]

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
        raise NotFoundError("사용자를 찾을 수 없습니다.")

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
        raise NotFoundError("사용자를 찾을 수 없습니다.")

    user.is_active = False
    session.add(user)
    await session.commit()

    logger.info(f"사용자 비활성화: id={user_id}")


# ── FAQ Override 관리 ──────────────────────────────────────────────


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
        .where(Faq.bot_id == bot_id, Faq.is_active == True)
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


# ── 채팅 기록 관리 (Admin) ──────────────────────────────────────────


@router.get("/chats", response_model=ChatSessionAdminListResponse, tags=["Admin - 채팅 관리"])
async def list_admin_chats(
    title: str | None = Query(None, description="세션 타이틀 검색"),
    user_email: str | None = Query(None, description="사용자 이메일 검색"),
    bot_id: int | None = Query(None, description="봇 필터"),
    has_feedback: str | None = Query(None, description="피드백 필터 (all, like, dislike)"),
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
) -> ChatSessionAdminListResponse:
    """
    전체 채팅 세션 목록 조회.
    봇 정보와 사용자 정보를 조인하여 반환한다.
    """
    # 피드백 집계를 위한 서브쿼리
    feedback_sq = (
        select(
            Message.session_id,
            func.count(1).filter(Message.feedback == "up").label("like_count"),
            func.count(1).filter(Message.feedback == "down").label("dislike_count"),
        )
        .group_by(Message.session_id)
        .subquery()
    )

    base_query = (
        select(
            ChatSession,
            Bot.name.label("bot_name"),
            User.email.label("user_email"),
            func.coalesce(col(feedback_sq.c.like_count), 0).label("like_count"),
            func.coalesce(col(feedback_sq.c.dislike_count), 0).label("dislike_count"),
        )
        .outerjoin(Bot, ChatSession.bot_id == Bot.id)
        .outerjoin(User, ChatSession.user_id == User.id)
        .outerjoin(feedback_sq, ChatSession.id == feedback_sq.c.session_id)
    )

    count_query = (
        select(func.count(ChatSession.id))
        .outerjoin(User, ChatSession.user_id == User.id)
        .outerjoin(feedback_sq, ChatSession.id == feedback_sq.c.session_id)
    )

    filters = []
    if title:
        filters.append(ChatSession.title.ilike(f"%{title}%"))
    if user_email:
        filters.append(User.email.ilike(f"%{user_email}%")) # type: ignore[attr-defined]
    if bot_id:
        filters.append(ChatSession.bot_id == bot_id)
    if has_feedback == "all":
        filters.append((col(feedback_sq.c.like_count) > 0) | (col(feedback_sq.c.dislike_count) > 0))
    elif has_feedback == "like":
        filters.append(col(feedback_sq.c.like_count) > 0)
    elif has_feedback == "dislike":
        filters.append(col(feedback_sq.c.dislike_count) > 0)

    for f in filters:
        base_query = base_query.where(f)
        count_query = count_query.where(f)

    statement = base_query.order_by(ChatSession.updated_at.desc()).limit(limit).offset(offset)

    result = await session.execute(statement)
    rows = result.all()

    # 데이터 매핑
    items = []
    for sess_obj, bot_name, email, like_count, dislike_count in rows:
        data = sess_obj.model_dump()
        data["bot_name"] = bot_name
        data["user_email"] = email
        data["like_count"] = like_count
        data["dislike_count"] = dislike_count
        items.append(ChatSessionAdminResponse.model_validate(data))

    total_res = await session.execute(count_query)
    total = total_res.scalar_one()

    return ChatSessionAdminListResponse(items=items, total=total)



@router.get("/chats/{session_id}/messages", response_model=list[MessageResponse], tags=["Admin - 채팅 관리"])
async def list_admin_chat_messages(
    session_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[MessageResponse]:
    """
    특정 채팅 세션의 전체 메시지 로그 조회 (상세).
    """
    statement = select(Message).where(Message.session_id == session_id).order_by(Message.created_at.asc())
    result = await session.execute(statement)
    messages = result.scalars().all()

    return [MessageResponse.model_validate(m) for m in messages]


@router.get("/chats/feedbacks", response_model=FeedbackMessageListResponse, tags=["Admin - 채팅 관리"])
async def list_feedback_messages(
    feedback_type: str | None = Query(None, description="피드백 타입 (up, down)"),
    bot_id: int | None = Query(None, description="봇 필터"),
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
) -> FeedbackMessageListResponse:
    """
    피드백을 받은 메시지 단위의 포커스 뷰 목록 조회 (제안 2 전용 API).
    """
    base_query = (
        select(
            Message,
            ChatSession.title.label("session_title"),
            Bot.name.label("bot_name"),
            User.email.label("user_email"),
        )
        .join(ChatSession, Message.session_id == ChatSession.id)
        .outerjoin(Bot, ChatSession.bot_id == Bot.id)
        .outerjoin(User, ChatSession.user_id == User.id)
        .where(Message.feedback.is_not(None))
    )

    count_query = (
        select(func.count(Message.id))
        .join(ChatSession, Message.session_id == ChatSession.id)
        .where(Message.feedback.is_not(None))
    )

    if feedback_type:
        f_expr = Message.feedback == ("up" if feedback_type == "like" else "down" if feedback_type == "dislike" else feedback_type)
        base_query = base_query.where(f_expr)
        count_query = count_query.where(f_expr)
        
    if bot_id:
        base_query = base_query.where(ChatSession.bot_id == bot_id)
        count_query = count_query.where(ChatSession.bot_id == bot_id)

    statement = base_query.order_by(Message.created_at.desc()).limit(limit).offset(offset)

    result = await session.execute(statement)
    rows = result.all()

    items = []
    for msg_obj, session_title, bot_name, user_email in rows:
        data = msg_obj.model_dump()
        data["session_title"] = session_title
        data["bot_name"] = bot_name
        data["user_email"] = user_email
        items.append(FeedbackMessageResponse.model_validate(data))

    total_res = await session.execute(count_query)
    total = total_res.scalar_one()

    return FeedbackMessageListResponse(items=items, total=total)

