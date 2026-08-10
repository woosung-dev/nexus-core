"""못 답한 질문 API 스키마."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.services.unanswered import ALL_TRIAGE


class UnansweredGroupResponse(BaseModel):
    """질문 그룹 1건 — 관리자 목록의 한 줄.

    `question_norm` 이 식별자다. 같은 질문이 23번 들어와도 관리자에겐 한 줄이고,
    판정도 하나다.
    """

    question_norm: str
    question_text: str = Field(description="가장 최근 발생의 원문")
    count: int
    last_seen: datetime
    bot_id: int | None = None
    reasons: list[str] = Field(default_factory=list, description="이 그룹에서 관측된 이유코드")
    triage: str
    ops_fact_id: int | None = None
    admin_note: str = ""


class UnansweredListResponse(BaseModel):
    items: list[UnansweredGroupResponse]
    total: int


class UnansweredOccurrenceResponse(BaseModel):
    """개별 발생 — 관리자가 `/chats` 로 넘어가는 통로.

    대화 전문은 여기서 안 편다. 민감한 사정이 섞여 있어 기존 화면에 위임한다.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    bot_id: int | None = None
    session_id: int | None = None
    message_id: int | None = None
    question_text: str
    reason: str
    detail: dict = Field(default_factory=dict)
    created_at: datetime


class UnansweredOccurrenceListResponse(BaseModel):
    items: list[UnansweredOccurrenceResponse]
    total: int


class UnansweredTriageRequest(BaseModel):
    """그룹 전체에 처리 경로를 찍는다.

    「운영 사실 등록」 단추 하나가 아니라 경로를 고르게 한 이유: `ops_facts` 는 문서를
    **못 고칠 때** 쓰는 런타임 덮개다. 덮개가 기본 경로가 되면 문서 개선 트랙이 죽는다.
    어느 칸에 일이 몰리는지가 먼저 보여야 무엇을 고쳐야 할지 정해진다.
    """

    question_norm: str
    triage: str
    ops_fact_id: int | None = None
    admin_note: str | None = None
    triaged_by: str | None = None

    def validate_triage(self) -> bool:
        return self.triage in ALL_TRIAGE


class UnansweredTriageResponse(BaseModel):
    question_norm: str
    triage: str
    updated: int = Field(description="같은 그룹에서 고친 발생 행 수")
