"""
Chat 관련 DB 연산(CRUD)을 담당하는 Repository.
라우터(Controller)에서 비즈니스 로직과 DB 접근 코드를 분리하기 위해 사용합니다.
"""

from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, desc, func

from app.models.bot import Bot
from app.models.chat import ChatSession, Message
from app.models.enums import MessageRole


async def get_user_chat_sessions(
    session: AsyncSession, user_id: int, limit: int = 50, offset: int = 0
) -> tuple[Sequence[tuple[ChatSession, Bot | None]], int]:
    """
    사용자의 채팅 세션 목록 조회.
    반환값: ([(ChatSession, Bot), ...], 총 개수)
    """
    statement = (
        select(ChatSession, Bot)
        .outerjoin(Bot, ChatSession.bot_id == Bot.id)
        .where(ChatSession.user_id == user_id)
        .order_by(desc(ChatSession.updated_at))
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(statement)
    rows = result.all()

    # 전체 개수 집계
    count_statement = select(func.count()).where(ChatSession.user_id == user_id)
    total = await session.scalar(count_statement)

    return rows, total or 0


async def get_chat_session_by_id(session: AsyncSession, session_id: int) -> ChatSession | None:
    """채팅 세션 단일 조회"""
    result = await session.execute(select(ChatSession).where(ChatSession.id == session_id))
    return result.scalar_one_or_none()


async def create_chat_session(
    session: AsyncSession, user_id: int, bot_id: int | None = None, title: str = "새 대화"
) -> ChatSession:
    """새로운 채팅 세션 생성"""
    chat_session = ChatSession(
        user_id=user_id,
        bot_id=bot_id,
        title=title,
    )
    session.add(chat_session)
    # 호출하는 쪽에서 commit을 제어하도록 flush만 수행
    await session.flush()
    await session.refresh(chat_session)
    return chat_session


async def get_session_messages(session: AsyncSession, session_id: int) -> Sequence[Message]:
    """특정 세션의 메시지 이력 조회"""
    statement = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    result = await session.execute(statement)
    return result.scalars().all()


async def create_message(
    session: AsyncSession, session_id: int, role: MessageRole, content: str
) -> Message:
    """
    새로운 메시지 생성 기록 (Flush).
    실제 DB 영속화는 상위 서비스/라우터의 commit()에서 일괄 처리.
    """
    msg = Message(
        session_id=session_id,
        role=role,
        content=content,
    )
    session.add(msg)
    await session.flush() 
    return msg


async def get_message_with_session(
    session: AsyncSession, message_id: int
) -> tuple[Message, ChatSession] | None:
    """
    메시지와 해당 채팅 세션을 함께 조회한다.
    소유권 검증(user_id 비교) 등에 활용.
    반환값: (Message, ChatSession) 또는 None
    """
    result = await session.execute(
        select(Message, ChatSession)
        .join(ChatSession, Message.session_id == ChatSession.id)
        .where(Message.id == message_id)
    )
    row = result.first()
    if row is None:
        return None
    return row[0], row[1]

