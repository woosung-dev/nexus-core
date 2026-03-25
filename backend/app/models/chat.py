"""
ChatSession & Message 모델.
사이드바 History 구조를 지원한다.
"""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel
from sqlalchemy import Column, DateTime, Enum as SAEnum, func
from app.models.enums import MessageRole


def get_utc_now():
    """파이썬 레벨의 UTC 현재 시간 — default_factory용"""
    return datetime.now(timezone.utc)


class ChatSession(SQLModel, table=True):
    """채팅 세션 — User와 Bot 간의 대화 단위"""

    __tablename__ = "chat_sessions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    bot_id: int | None = Field(default=None, foreign_key="bots.id", index=True)
    title: str = Field(default="새 대화", max_length=200)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
        default_factory=get_utc_now
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), 
            server_default=func.now(), 
            onupdate=func.now(), 
            nullable=False
        ),
        default_factory=get_utc_now
    )


class Message(SQLModel, table=True):
    """개별 메시지 — 세션 내의 대화 기록"""

    __tablename__ = "messages"

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="chat_sessions.id", index=True)
    role: MessageRole = Field(
        default=MessageRole.USER,
        sa_column=Column(SAEnum(MessageRole, name="messagerole", values_callable=lambda x: [e.value for e in x]))
    )
    content: str
    feedback: str | None = Field(default=None, max_length=10, description="피드백 (up, down 등)")

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
        default_factory=get_utc_now
    )
