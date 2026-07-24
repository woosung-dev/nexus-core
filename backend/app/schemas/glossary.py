"""
용어집 관련 API 스키마.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GlossaryResponse(BaseModel):
    """용어집 단일 조회/등록/수정 응답"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    bot_id: int | None
    term: str
    aliases: list = []
    definition: str
    priority: int
    threshold: float
    is_active: bool
    created_at: datetime
    updated_at: datetime


class GlossaryListResponse(BaseModel):
    """용어집 목록 응답"""
    terms: list[GlossaryResponse]
    total: int


class GlossaryCreateRequest(BaseModel):
    """용어집 등록 요청"""
    term: str = Field(..., min_length=1, max_length=200)
    aliases: list[str] = []
    definition: str = Field(..., min_length=1)
    bot_id: int | None = None
    priority: int = 100
    threshold: float = Field(default=0.88, ge=0, le=1)


class GlossaryUpdateRequest(BaseModel):
    """용어집 수정 요청 (부분 업데이트)"""
    term: str | None = Field(default=None, min_length=1, max_length=200)
    aliases: list[str] | None = None
    definition: str | None = Field(default=None, min_length=1)
    bot_id: int | None = None
    priority: int | None = None
    threshold: float | None = Field(default=None, ge=0, le=1)
    is_active: bool | None = None
