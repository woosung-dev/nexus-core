"""
Dashboard 관련 DB 연산(CRUD)을 담당하는 Repository.
서비스(Service) 계층에서 비즈니스 로직과 DB 접근 코드를 분리하기 위해 사용합니다.
"""

from datetime import datetime
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func, desc

from app.models.bot import Bot
from app.models.user import User
from app.models.chat import ChatSession, Message


async def get_total_bots_count(session: AsyncSession) -> int:
    """전체 봇 개수 조회"""
    return (await session.execute(select(func.count(Bot.id)))).scalar_one()


async def get_total_users_count(session: AsyncSession) -> int:
    """전체 사용자 수 조회"""
    return (await session.execute(select(func.count(User.id)))).scalar_one()


async def get_today_chats_count(session: AsyncSession, today_start: datetime) -> int:
    """오늘 생성된 채팅 세션 수 조회"""
    return (
        await session.execute(
            select(func.count(ChatSession.id)).where(ChatSession.created_at >= today_start)
        )
    ).scalar_one()


async def get_today_feedback_counts(session: AsyncSession, today_start: datetime) -> dict[str, int]:
    """오늘 생성된 피드백의 종류별 개수 조회"""
    feedback_query = (
        select(Message.feedback, func.count(Message.id))
        .where(
            Message.created_at >= today_start,
            Message.feedback.is_not(None)
        )
        .group_by(Message.feedback)
    )
    feedback_result = await session.execute(feedback_query)
    # feedback을 문자열 처리 가능하도록 안전하게 추출. 'up', 'down' 등의 값이 예상됨
    return {str(row[0]): int(row[1]) for row in feedback_result.all()}


async def get_recent_chat_trend(session: AsyncSession, period_start: datetime) -> Sequence[tuple[datetime, int]]:
    """특정 기간 동안의 일별 대화 발생 추이 조회"""
    date_trunc_expr = func.date_trunc("day", ChatSession.created_at).label("day")
    trend_query = (
        select(date_trunc_expr, func.count(ChatSession.id))
        .where(ChatSession.created_at >= period_start)
        .group_by(date_trunc_expr)
        .order_by(date_trunc_expr)
    )
    trend_result = await session.execute(trend_query)
    return trend_result.all()


async def get_recent_bot_shares(session: AsyncSession, period_start: datetime) -> Sequence[tuple[str, int]]:
    """특정 기간 동안 가장 많이 사용된 봇의 점유율 조회"""
    share_query = (
        select(Bot.name, func.count(ChatSession.id))
        .join(ChatSession, ChatSession.bot_id == Bot.id)
        .where(ChatSession.created_at >= period_start)
        .group_by(Bot.name)
        .order_by(desc(func.count(ChatSession.id)))
    )
    share_result = await session.execute(share_query)
    return share_result.all()


async def get_feedback_count_by_type(session: AsyncSession, feedback_type: str) -> int:
    """특정 피드백 타입('up', 'down')의 전체 개수 조회"""
    return (
        await session.execute(select(func.count(Message.id)).where(Message.feedback == feedback_type))
    ).scalar_one()


async def get_recent_feedbacks_by_type(
    session: AsyncSession, feedback_type: str, limit: int = 10, offset: int = 0
) -> Sequence[tuple[Message, str | None, str | None, str | None]]:
    """
    특정 피드백 타입의 최근 메시지 목록을 페이징하여 조회
    반환값: [(Message_객체, 세션타이틀, 봇이름, 유저이메일), ...]
    """
    query = (
        select(
            Message,
            ChatSession.title.label("session_title"),
            Bot.name.label("bot_name"),
            User.email.label("user_email")
        )
        .join(ChatSession, Message.session_id == ChatSession.id)
        .outerjoin(Bot, ChatSession.bot_id == Bot.id)
        .outerjoin(User, ChatSession.user_id == User.id)
        .where(Message.feedback == feedback_type)
        .order_by(desc(Message.created_at))
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(query)
    return result.all()
