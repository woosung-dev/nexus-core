"""
채팅 관련 API 엔드포인트.
세션 관리, 메시지 기록, SSE(Server-Sent Events) 스트리밍 지원.
"""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, desc, func

from app.api.deps import get_current_user
from app.core.database import get_session
from app.crud import crud_chat
from app.core.exceptions import BotNotFoundError, NotFoundError, NexusException
from app.models.bot import Bot
from app.models.chat import ChatSession, Message
from app.models.enums import MessageRole
from app.models.user import User
from app.schemas.chat import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
    MessageResponse,
    MessageFeedbackUpdate,
)
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chats", tags=["채팅"])


# Removed _get_llm_service (moved to ChatService)


@router.get("", response_model=ChatSessionListResponse)
async def list_chat_sessions(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatSessionListResponse:
    """
    현재 로그인한 사용자의 채팅 세션 목록을 조회합니다.
    최근 업데이트된 순서(updated_at DESC)로 정렬됩니다.
    """
    rows, total = await crud_chat.get_user_chat_sessions(
        session, current_user.id, limit, offset
    )

    session_responses = []
    for chat_sess, bot_obj in rows:
        sess_dict = chat_sess.model_dump()
        if bot_obj:
            sess_dict["bot"] = bot_obj.model_dump()
        session_responses.append(ChatSessionResponse.model_validate(sess_dict))

    return ChatSessionListResponse(sessions=session_responses, total=total)


@router.post("", response_model=ChatSessionResponse)
async def create_chat_session(
    bot_id: int | None = None,
    title: str = "새 대화",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatSessionResponse:
    """
    새로운 채팅 세션을 생성합니다.
    """
    bot_obj = None
    if bot_id:
        result = await session.execute(select(Bot).where(Bot.id == bot_id))
        bot_obj = result.scalar_one_or_none()
        if not bot_obj:
            raise BotNotFoundError()

    chat_session = await crud_chat.create_chat_session(
        session=session, user_id=current_user.id, bot_id=bot_id, title=title
    )
    await session.commit()
    await session.refresh(chat_session)

    sess_dict = chat_session.model_dump()
    if bot_obj:
        sess_dict["bot"] = bot_obj.model_dump()

    return ChatSessionResponse.model_validate(sess_dict)


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[MessageResponse]:
    """
    특정 채팅 세션의 메시지 기록을 조회합니다.
    """
    # 세션 소유권 검증
    chat_session = await crud_chat.get_chat_session_by_id(session, session_id)

    if not chat_session:
        raise NotFoundError("채팅 세션을 찾을 수 없습니다.")
    if chat_session.user_id != current_user.id:
        raise NexusException(
            error_code="FORBIDDEN", 
            message="접근 권한이 없습니다.", 
            status_code=status.HTTP_403_FORBIDDEN
        )

    messages = await crud_chat.get_session_messages(session, session_id)

    return [MessageResponse.model_validate(m) for m in messages]


@router.post("/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    채팅 완성 엔드포인트.
    사용자 메시지를 DB에 저장하고, AI 응답 스트리밍 완료 후 응답 메시지를 DB에 저장합니다.
    session_id가 없으면 자동으로 새 채팅 세션을 생성합니다.
    """
    # 1. 봇 검증
    result = await session.execute(select(Bot).where(Bot.id == request.bot_id))
    bot = result.scalar_one_or_none()

    if not bot:
        raise BotNotFoundError()
    if not bot.is_active:
        raise ValidationError("비활성화된 봇입니다.")

    # 2. 세션 검증 또는 신규 생성
    chat_session = None

    if request.session_id:
        chat_session = await crud_chat.get_chat_session_by_id(session, request.session_id)
        if not chat_session:
            raise NotFoundError("세션을 찾을 수 없습니다.")
        if chat_session.user_id != current_user.id:
            raise NexusException(
                error_code="FORBIDDEN", 
                message="세션 접근 권한이 없습니다.", 
                status_code=status.HTTP_403_FORBIDDEN
            )
    else:
        # 새 세션 생성
        title = request.message[:20] + "..." if len(request.message) > 20 else request.message
        chat_session = await crud_chat.create_chat_session(
            session=session, user_id=current_user.id, bot_id=request.bot_id, title=title
        )

    # 3. 사용자 메시지 DB에 저장 (commit 없이 flush만)
    await crud_chat.create_message(
        session=session, session_id=chat_session.id, role=MessageRole.USER, content=request.message
    )

    # 4. 서비스 레이어 위임 (ChatService)
    chat_service = ChatService(session=session)
    return await chat_service.process_chat_request(
        request=request, bot=bot, chat_session=chat_session
    )


@router.patch("/messages/{message_id}", response_model=MessageResponse)
async def update_message_feedback(
    message_id: int,
    request: MessageFeedbackUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """
    메시지에 대한 피드백(좋아요/싫어요)을 업데이트합니다.
    """
    # 메시지 및 세션 소유권 확인 (비동기 쿼리)
    result = await session.execute(
        select(Message, ChatSession)
        .join(ChatSession, Message.session_id == ChatSession.id)
        .where(Message.id == message_id)
    )
    row = result.first()

    if not row:
        raise NotFoundError("메시지를 찾을 수 없습니다.")

    msg_obj, sess_obj = row

    if sess_obj.user_id != current_user.id:
        raise NexusException(
            error_code="FORBIDDEN",
            message="피드백 수정 권한이 없습니다.",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # 업데이트
    msg_obj.feedback = request.feedback
    session.add(msg_obj)
    await session.commit()
    await session.refresh(msg_obj)

    return MessageResponse.model_validate(msg_obj)
