"""
채팅 관련 API 스키마.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models.enums import MessageRole
from app.schemas.bot import BotResponse


class ChatCompletionRequest(BaseModel):
    """채팅 완성 요청 스키마"""

    bot_id: int
    message: str
    session_id: int | None = None
    stream: bool = True
    use_rag: bool = False  # RAG 활성화 여부


class ChatCompletionResponse(BaseModel):
    """일반(Non-Streaming) 채칭 응답 스키마"""

    session_id: int
    content: str
    bot_id: int
    citations: list[dict] | None = None  # RAG 인용구 출처


class ChatSessionResponse(BaseModel):
    """채팅 세션 응답 스키마"""

    id: int
    bot_id: int | None
    bot: BotResponse | None = None
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class MessageResponse(BaseModel):
    """채팅 메시지 응답 스키마"""

    id: int
    session_id: int
    role: MessageRole
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionListResponse(BaseModel):
    """채팅 세션 목록 응답 스키마"""

    sessions: list[ChatSessionResponse]
    total: int
