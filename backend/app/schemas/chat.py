"""
채팅 관련 API 스키마.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import (
    ALL_FEEDBACK_REASONS,
    NEGATIVE_FEEDBACK_REASONS,
    POSITIVE_FEEDBACK_REASONS,
    MessageRole,
)
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
    followups: list[str] = Field(default_factory=list)  # 후속 질문 (빈 리스트 = 없음 또는 생성 실패)


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
    feedback_reasons: list[str] = Field(default_factory=list)
    feedback_comment: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("feedback_reasons", mode="before")
    @classmethod
    def _parse_feedback_reasons(cls, v):
        """DB에는 JSON 문자열로 저장되므로 list 로 디시리얼라이즈."""
        if v is None or v == "":
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            import json
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                return []
        return []


class ChatSessionListResponse(BaseModel):
    """채팅 세션 목록 응답 스키마"""

    sessions: list[ChatSessionResponse]
    total: int


class MessageFeedbackUpdate(BaseModel):
    """메시지 피드백 업데이트 요청 스키마"""

    feedback: str | None = None
    feedback_reasons: list[str] = Field(default_factory=list)
    feedback_comment: str | None = Field(default=None, max_length=1000)

    @field_validator("feedback")
    @classmethod
    def _validate_feedback(cls, v):
        if v is None:
            return None
        if v not in {"up", "down"}:
            raise ValueError("feedback 은 'up', 'down', null 만 허용됩니다.")
        return v

    @field_validator("feedback_reasons")
    @classmethod
    def _validate_reasons(cls, v):
        if not v:
            return []
        unknown = [r for r in v if r not in ALL_FEEDBACK_REASONS]
        if unknown:
            raise ValueError(f"허용되지 않은 사유 코드: {unknown}")
        # 중복 제거 + 순서 유지
        seen = set()
        deduped = []
        for r in v:
            if r not in seen:
                seen.add(r)
                deduped.append(r)
        return deduped


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
    feedback_reasons: list[str] = Field(default_factory=list)
    feedback_comment: str | None = None
    created_at: datetime

    # 조인으로 가져올 추가 정보
    bot_name: str | None = None
    user_email: str | None = None
    session_title: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("feedback_reasons", mode="before")
    @classmethod
    def _parse_feedback_reasons(cls, v):
        if v is None or v == "":
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            import json
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                return []
        return []


class FeedbackMessageListResponse(BaseModel):
    """어드민용 피드백 메시지 목록 응답 스키마"""
    items: list[FeedbackMessageResponse]
    total: int
