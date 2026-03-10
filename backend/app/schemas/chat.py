"""
채팅 관련 API 스키마.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models.enums import MessageRole
from app.schemas.bot import BotResponse
from app.schemas.rag import RAGCitation


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
    citations: list[RAGCitation] | None = None  # RAG 인용구 출처
    source: str | None = None  # 응답 소스: "faq_override" | "rag" | "llm"


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
    feedback: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionListResponse(BaseModel):
    """채팅 세션 목록 응답 스키마"""

    sessions: list[ChatSessionResponse]
    total: int


class MessageFeedbackUpdate(BaseModel):
    """메시지 피드백 업데이트 요청 스키마"""

    feedback: str | None


class ChatSessionAdminResponse(BaseModel):
    """어드민용 채팅 세션 응답 스키마 (추가 정보 포함)"""

    id: int
    bot_id: int | None
    bot_name: str | None = None
    user_id: int | None
    user_email: str | None = None
    title: str
    like_count: int = 0
    dislike_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionAdminListResponse(BaseModel):
    """어드민용 채팅 세션 목록 응답 스키마"""

    items: list[ChatSessionAdminResponse]
    total: int


class FeedbackMessageResponse(BaseModel):
    """어드민용 피드백 메시지 상세 응답 스키마 (제안 2 - 포커스 뷰 용)"""
    id: int
    session_id: int
    role: MessageRole
    content: str
    feedback: str
    created_at: datetime
    
    # 조인으로 가져올 추가 정보
    bot_name: str | None = None
    user_email: str | None = None
    session_title: str | None = None

    model_config = ConfigDict(from_attributes=True)


class FeedbackMessageListResponse(BaseModel):
    """어드민용 피드백 메시지 목록 응답 스키마"""
    items: list[FeedbackMessageResponse]
    total: int
