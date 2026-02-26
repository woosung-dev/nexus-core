"""
채팅 관련 API 스키마.
"""

from pydantic import BaseModel

from app.schemas.rag import RAGCitation


class ChatCompletionRequest(BaseModel):
    """채팅 완성 요청"""
    bot_id: int
    message: str
    session_id: int | None = None  # None이면 새 세션 생성
    stream: bool = True
    use_rag: bool = False  # True이면 RAG 기반 응답 생성


class ChatCompletionResponse(BaseModel):
    """채팅 완성 응답 (Non-Streaming)"""
    session_id: int
    content: str
    bot_id: int
    citations: list[RAGCitation] = []  # RAG 사용 시 인용 정보
