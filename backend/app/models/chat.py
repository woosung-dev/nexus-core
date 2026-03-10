"""
ChatSession & Message 모델.
사이드바 History 구조를 지원한다.
"""

from datetime import datetime

from sqlmodel import Field, SQLModel
from sqlalchemy import Column, Enum as SAEnum

from app.models.enums import MessageRole


class ChatSession(SQLModel, table=True):
    """채팅 세션 — User와 Bot 간의 대화 단위"""

    __tablename__ = "chat_sessions"
    __table_args__ = {"schema": "nexus_core"}

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="nexus_core.users.id", index=True)
    bot_id: int | None = Field(default=None, foreign_key="nexus_core.bots.id", index=True)
    title: str = Field(default="새 대화", max_length=200)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Message(SQLModel, table=True):
    """개별 메시지 — 세션 내의 대화 기록"""

    __tablename__ = "messages"
    __table_args__ = {"schema": "nexus_core"}

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="nexus_core.chat_sessions.id", index=True)
    role: MessageRole = Field(
        default=MessageRole.USER,
        sa_column=Column(SAEnum(MessageRole, name="messagerole", schema="nexus_core", values_callable=lambda x: [e.value for e in x]))
    )
    content: str
    feedback: str | None = Field(default=None, max_length=10, description="피드백 (up, down 등)")

    created_at: datetime = Field(default_factory=datetime.utcnow)
