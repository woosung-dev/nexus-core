"""
RAG(Retrieval-Augmented Generation) 관련 API 스키마.
"""

from pydantic import BaseModel


class RAGCitation(BaseModel):
    """RAG 응답 인용 정보"""
    title: str | None = None
    content: str | None = None


class RAGResponse(BaseModel):
    """RAG 기반 응답"""
    answer: str
    citations: list[RAGCitation] = []


class DocumentInfo(BaseModel):
    """개별 문서 정보"""
    file_id: str
    display_name: str
    created_at: str | None = None
    status: str | None = None
    size_bytes: int | None = None


class DocumentListResponse(BaseModel):
    """봇 전용 문서 목록 응답"""
    bot_id: int
    documents: list[DocumentInfo] = []
    total: int = 0


class DocumentUploadResponse(BaseModel):
    """문서 업로드 응답"""
    file_name: str
    display_name: str
    bot_id: int
    message: str = "문서가 성공적으로 업로드되었습니다."
