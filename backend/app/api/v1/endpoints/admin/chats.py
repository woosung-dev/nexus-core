"""
Admin — 채팅 기록 관리 API 엔드포인트.
채팅 세션 목록, 메시지 상세, 피드백 포커스 뷰를 담당한다.
"""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.crud import crud_admin_chat
from app.crud.crud_admin_chat import AdminChatFilters
from app.schemas.chat import (
    ChatSessionAdminResponse,
    ChatSessionAdminListResponse,
    FeedbackMessageListResponse,
    FeedbackMessageResponse,
    MessageResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


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
    filters = AdminChatFilters(
        title=title,
        user_email=user_email,
        bot_id=bot_id,
        has_feedback=has_feedback,
    )

    rows = await crud_admin_chat.get_admin_chat_sessions(session, filters, limit, offset)
    total = await crud_admin_chat.count_admin_chat_sessions(session, filters)

    items = []
    for sess_obj, bot_name, email, like_count, dislike_count in rows:
        data = sess_obj.model_dump()
        data["bot_name"] = bot_name
        data["user_email"] = email
        data["like_count"] = like_count
        data["dislike_count"] = dislike_count
        items.append(ChatSessionAdminResponse.model_validate(data))

    return ChatSessionAdminListResponse(items=items, total=total)


@router.get("/chats/{session_id}/messages", response_model=list[MessageResponse], tags=["Admin - 채팅 관리"])
async def list_admin_chat_messages(
    session_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[MessageResponse]:
    """
    특정 채팅 세션의 전체 메시지 로그 조회 (상세).
    """
    messages = await crud_admin_chat.get_messages_by_session_id(session, session_id)
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
    rows = await crud_admin_chat.get_feedback_messages(session, feedback_type, bot_id, limit, offset)
    total = await crud_admin_chat.count_feedback_messages(session, feedback_type, bot_id)

    items = []
    for msg_obj, session_title, bot_name, user_email in rows:
        data = msg_obj.model_dump()
        data["session_title"] = session_title
        data["bot_name"] = bot_name
        data["user_email"] = user_email
        items.append(FeedbackMessageResponse.model_validate(data))

    return FeedbackMessageListResponse(items=items, total=total)
