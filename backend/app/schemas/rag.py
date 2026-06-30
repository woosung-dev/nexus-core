"""
RAG(Retrieval-Augmented Generation) 관련 API 스키마.
"""

from pydantic import BaseModel


class RAGCitation(BaseModel):
    """RAG 응답 인용 정보"""
    title: str | None = None
    content: str | None = None
    # interactions file_citation 기반 정확 인용 여부 (False=정확, True=별도 검색 근사).
    approximate: bool = False
    # 원문 문서 URI / 인용된 페이지 번호 (있을 때만). 기존 {title,content} UI 에는 무영향.
    uri: str | None = None
    page_number: int | None = None


class RAGResponse(BaseModel):
    """RAG 기반 응답"""
    answer: str
    citations: list[RAGCitation] = []
    # RAG 호출 1회로 본문과 같이 받은 후속 질문 (최대 3개). 별도 LLM 호출(followup_service)을
    # 대체해 wall-time/비용 절반으로 줄이고 timeout 사고를 차단한다.
    followups: list[str] = []


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
