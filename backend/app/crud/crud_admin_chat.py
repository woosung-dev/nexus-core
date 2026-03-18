"""
Admin 채팅 관련 DB 연산(CRUD)을 담당하는 Repository.
어드민 전용 조인 쿼리(세션+봇+유저), 피드백 집계 등을 담당한다.
"""

from dataclasses import dataclass
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col, func

from app.models.bot import Bot
from app.models.chat import ChatSession, Message
from app.models.user import User


@dataclass
class AdminChatFilters:
    """어드민 채팅 목록 조회 필터 옵션"""
    title: str | None = None
    user_email: str | None = None
    bot_id: int | None = None
    has_feedback: str | None = None  # "all" | "like" | "dislike"


def _build_feedback_subquery():
    """피드백 집계용 서브쿼리 생성 (재사용 목적으로 분리)"""
    return (
        select(
            Message.session_id,
            func.count(1).filter(Message.feedback == "up").label("like_count"),
            func.count(1).filter(Message.feedback == "down").label("dislike_count"),
        )
        .group_by(Message.session_id)
        .subquery()
    )


async def get_admin_chat_sessions(
    session: AsyncSession,
    filters: AdminChatFilters,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[tuple]:
    """
    어드민용 채팅 세션 목록 조회 (봇+유저 조인, 피드백 집계 포함).
    반환값: [(ChatSession, bot_name, user_email, like_count, dislike_count), ...]
    """
    feedback_sq = _build_feedback_subquery()

    statement = (
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

    statement = _apply_chat_filters(statement, filters, feedback_sq)
    statement = statement.order_by(ChatSession.updated_at.desc()).limit(limit).offset(offset)

    result = await session.execute(statement)
    return result.all()


async def count_admin_chat_sessions(
    session: AsyncSession,
    filters: AdminChatFilters,
) -> int:
    """어드민용 채팅 세션 총 개수 집계 (필터 동일 적용)"""
    feedback_sq = _build_feedback_subquery()

    statement = (
        select(func.count(ChatSession.id))
        .outerjoin(User, ChatSession.user_id == User.id)
        .outerjoin(feedback_sq, ChatSession.id == feedback_sq.c.session_id)
    )
    statement = _apply_chat_filters(statement, filters, feedback_sq)

    result = await session.execute(statement)
    return result.scalar_one()


def _apply_chat_filters(statement, filters: AdminChatFilters, feedback_sq):
    """공통 필터 조건 적용 헬퍼"""
    if filters.title:
        statement = statement.where(ChatSession.title.ilike(f"%{filters.title}%"))
    if filters.user_email:
        statement = statement.where(User.email.ilike(f"%{filters.user_email}%"))  # type: ignore[attr-defined]
    if filters.bot_id:
        statement = statement.where(ChatSession.bot_id == filters.bot_id)
    if filters.has_feedback == "all":
        statement = statement.where(
            (col(feedback_sq.c.like_count) > 0) | (col(feedback_sq.c.dislike_count) > 0)
        )
    elif filters.has_feedback == "like":
        statement = statement.where(col(feedback_sq.c.like_count) > 0)
    elif filters.has_feedback == "dislike":
        statement = statement.where(col(feedback_sq.c.dislike_count) > 0)
    return statement


async def get_messages_by_session_id(
    session: AsyncSession,
    session_id: int,
) -> Sequence[Message]:
    """특정 어드민 채팅 세션의 전체 메시지 조회 (시간순 정렬)"""
    result = await session.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    return result.scalars().all()


async def get_feedback_messages(
    session: AsyncSession,
    feedback_type: str | None = None,
    bot_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[tuple]:
    """
    피드백이 달린 메시지 목록 조회 (세션+봇+유저 조인).
    반환값: [(Message, session_title, bot_name, user_email), ...]
    """
    statement = (
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

    statement = _apply_feedback_filters(statement, feedback_type, bot_id)
    statement = statement.order_by(Message.created_at.desc()).limit(limit).offset(offset)

    result = await session.execute(statement)
    return result.all()


async def count_feedback_messages(
    session: AsyncSession,
    feedback_type: str | None = None,
    bot_id: int | None = None,
) -> int:
    """피드백 메시지 총 개수 집계"""
    statement = (
        select(func.count(Message.id))
        .join(ChatSession, Message.session_id == ChatSession.id)
        .where(Message.feedback.is_not(None))
    )
    statement = _apply_feedback_filters(statement, feedback_type, bot_id)
    result = await session.execute(statement)
    return result.scalar_one()


def _apply_feedback_filters(statement, feedback_type: str | None, bot_id: int | None):
    """피드백 쿼리 공통 필터 헬퍼"""
    if feedback_type:
        fb_value = (
            "up" if feedback_type == "like"
            else "down" if feedback_type == "dislike"
            else feedback_type
        )
        statement = statement.where(Message.feedback == fb_value)
    if bot_id:
        statement = statement.where(ChatSession.bot_id == bot_id)
    return statement
