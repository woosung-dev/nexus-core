"""
Admin — 채팅 기록 관리 API 엔드포인트.
채팅 세션 목록, 메시지 상세, 피드백 포커스 뷰를 담당한다.
"""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col, func

from app.core.database import get_session
from app.models.bot import Bot
from app.models.chat import ChatSession, Message
from app.models.user import User
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
        filters.append(User.email.ilike(f"%{user_email}%"))  # type: ignore[attr-defined]
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
        f_expr = Message.feedback == (
            "up" if feedback_type == "like" else "down" if feedback_type == "dislike" else feedback_type
        )
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
