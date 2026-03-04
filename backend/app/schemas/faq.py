"""
FAQ 관련 API 스키마 (요청/응답).
FastAPI 엔드포인트의 request/response model로 사용된다.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ─── 응답 스키마 ─────────────────────────────────────────────

class FaqResponse(BaseModel):
    """FAQ 단일 조회/등록/수정 응답"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    bot_id: int
    question: str
    answer: str
    threshold: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # question_vector는 응답에 포함하지 않음 (내부 처리용)


class FaqListResponse(BaseModel):
    """FAQ 목록 응답"""
    faqs: list[FaqResponse]
    total: int


# ─── 요청 스키마 ─────────────────────────────────────────────

class FaqCreateRequest(BaseModel):
    """FAQ 등록 요청"""
    question: str = Field(..., min_length=2, max_length=1000, description="FAQ 질문")
    answer: str = Field(..., min_length=1, description="우선순위 답변")
    threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="유사도 임계값 (0.0~1.0). 이 값 이상이면 FAQ 답변 우선 출력",
    )


class FaqUpdateRequest(BaseModel):
    """FAQ 수정 요청 (부분 업데이트)"""
    question: str | None = Field(default=None, min_length=2, max_length=1000)
    answer: str | None = Field(default=None, min_length=1)
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    is_active: bool | None = None
