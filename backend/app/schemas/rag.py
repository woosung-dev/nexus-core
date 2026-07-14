"""
RAG(Retrieval-Augmented Generation) 관련 API 스키마.
"""

from pydantic import BaseModel


class RAGCitation(BaseModel):
    """RAG 응답 인용 정보 — 문서가 아니라 **청크** 하나를 가리킨다."""
    title: str | None = None
    content: str | None = None
    # interactions file_citation 기반 정확 인용 여부 (False=정확, True=별도 검색 근사).
    approximate: bool = False
    # 원문 문서 URI / 인용된 페이지 번호 (있을 때만). 기존 {title,content} UI 에는 무영향.
    uri: str | None = None
    page_number: int | None = None
    # 이 청크가 답변의 몇 개 구간을 뒷받침했는지 (= file_citation 어노테이션 수).
    # 출처를 문서 단위로 묶어 "가장 많이 참고한 순"으로 정렬하는 랭킹 점수로 쓴다.
    # 주의: 근사 인용(approximate=True)의 구간은 표시된 답변이 아니라 백필이 새로
    # 생성한 답변 기준이다 → 정렬에만 쓰고 "답변의 N% 근거" 같은 수치로 노출 금지.
    cite_count: int = 1


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
