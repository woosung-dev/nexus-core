"""
ChatSession & Message 모델.
사이드바 History 구조를 지원한다.
"""

from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.enums import MessageRole


class ChatSession(SQLModel, table=True):
    """채팅 세션 — User와 Bot 간의 대화 단위"""

    __tablename__ = "chat_sessions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    bot_id: int | None = Field(default=None, foreign_key="bots.id", index=True)
    title: str = Field(default="새 대화", max_length=200)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Message(SQLModel, table=True):
    """개별 메시지 — 세션 내의 대화 기록"""

    __tablename__ = "messages"

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="chat_sessions.id", index=True)
    role: MessageRole = Field(default=MessageRole.USER)
    content: str

    created_at: datetime = Field(default_factory=datetime.utcnow)
