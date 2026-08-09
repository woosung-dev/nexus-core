"""
운영 사실(ops_facts) API 스키마 (요청/응답).

근거 구조는 정답지와 같은 모양이라 `schemas.redteam.GoldenEvidence` 를 그대로 쓴다.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.redteam import GoldenEvidence

KIND_PATTERN = "^(deprecated|forbidden|term|contact|crisis)$"
STATUS_PATTERN = "^(초안|승인|수정승인|반려)$"


# ─── 응답 스키마 ─────────────────────────────────────────────

class OpsFactResponse(BaseModel):
    """운영 사실 단일 조회/등록/수정 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    bot_id: int | None = None
    kind: str
    title: str = ""
    superseded: str = ""
    statement: str = ""
    triggers: list[str] = []
    detect: list[str] = []
    evidence: list[GoldenEvidence] = []
    source_docs: list[str] = []
    priority: int = 100
    status: str = "초안"
    approver: str | None = None
    approved_at: datetime | None = None
    admin_note: str = ""
    draft_statement: str = ""
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class OpsFactListResponse(BaseModel):
    """운영 사실 목록 응답"""

    items: list[OpsFactResponse]
    total: int


# ─── 요청 스키마 ─────────────────────────────────────────────

class OpsFactCreateRequest(BaseModel):
    """운영 사실 등록 — 항상 status='초안' 으로 들어간다(런타임 미반영)."""

    bot_id: int | None = Field(default=None, description="NULL이면 전역")
    kind: str = Field(..., pattern=KIND_PATTERN)
    title: str = Field(default="", max_length=200)
    superseded: str = Field(default="", description="쓰면 안 되는 것")
    statement: str = Field(default="", description="대신 쓸 것 / 현행 사실")
    triggers: list[str] = Field(default_factory=list, description="비면 항상 주입")
    detect: list[str] = Field(
        default_factory=list, description="L2 검출 정규식. 비면 superseded 문자열 포함으로 검사"
    )
    evidence: list[GoldenEvidence] = Field(default_factory=list)
    source_docs: list[str] = Field(default_factory=list)
    priority: int = Field(default=100)


class OpsFactUpdateRequest(BaseModel):
    """관리자 판정 — 보낸 필드만 갱신.

    화면 기본 동작은 정답지 검수와 같은 3버튼이다.
      [맞음]       → status='승인'
      [고쳐야 함]   → status='수정승인' + statement 수정본
      [반려]       → status='반려'
    """

    status: str | None = Field(default=None, pattern=STATUS_PATTERN)
    kind: str | None = Field(default=None, pattern=KIND_PATTERN)
    title: str | None = Field(default=None, max_length=200)
    superseded: str | None = Field(default=None)
    statement: str | None = Field(default=None)
    triggers: list[str] | None = Field(default=None)
    detect: list[str] | None = Field(default=None)
    evidence: list[GoldenEvidence] | None = Field(default=None)
    source_docs: list[str] | None = Field(default=None)
    priority: int | None = Field(default=None)
    approver: str | None = Field(default=None, max_length=50)
    admin_note: str | None = Field(default=None)
    is_active: bool | None = Field(default=None)
