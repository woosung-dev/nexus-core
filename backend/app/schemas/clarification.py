"""비영속 맥락 보완 프로토타입의 요청/응답 계약."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.rag import RAGCitation


class ClarificationQuestion(BaseModel):
    """사용자가 답할 수 있는 하나의 맥락 보완 질문."""

    id: str
    question: str
    selection_mode: Literal["single", "multiple"] = "single"
    options: list[str] = Field(default_factory=list)
    allow_custom: bool = True
    required: bool = False
    policy: bool = False


class ClarificationAnswer(BaseModel):
    """질문 카드에서 수집한 값. 저장하지 않고 다음 판정 호출에만 전달한다."""

    question_id: str
    question: str
    values: list[str] = Field(default_factory=list)


class ClarificationPreviewRequest(BaseModel):
    """프로토타입 전용 맥락 보완 판정 요청."""

    bot_id: int
    message: str = Field(min_length=1, max_length=2_000)
    answers: list[ClarificationAnswer] = Field(default_factory=list)
    # 정책 카드가 반환한 규칙 ID. 다음 요청에서도 서버가 항목과 값을 재검증한다.
    policy_rule_id: str | None = Field(default=None, max_length=100)
    policy_context: str | None = Field(default=None, max_length=1_000)
    round: int = Field(default=0, ge=0, le=2)
    mode: Literal["fixture", "live"] = "fixture"


class ClarificationDiagnostics(BaseModel):
    """화면에는 표시하지 않는 정책 적용 진단. 관리자 테스트 결과에만 사용한다."""

    applied_rule_id: str | None = None
    policy_match_status: Literal["disabled", "matched", "unmatched", "uncertain"] = "disabled"
    missing_slot_ids: list[str] = Field(default_factory=list)
    document_ref_ids: list[str] = Field(default_factory=list)


class ClarificationPreviewResponse(BaseModel):
    """질문을 더 받을지, 사용자가 확인할 요청 요약을 보여 줄지 결정한다."""

    status: Literal["ask", "ready", "handoff"]
    source: Literal["fixture", "live", "fallback"]
    questions: list[ClarificationQuestion] = Field(default_factory=list)
    summary: str | None = None
    citations: list[RAGCitation] = Field(default_factory=list)
    fallback: bool = False
    handoff_message: str | None = None
    diagnostics: ClarificationDiagnostics = Field(default_factory=ClarificationDiagnostics)
    policy_context: str | None = None


class ChatClarification(BaseModel):
    """실제 대화가 되물을 때 응답에 싣는 것. 프로토타입 계약과 별개다.

    `ClarificationPreviewResponse` 를 재사용하지 않는다 — 그쪽은
    `source: "fixture"|"live"|"fallback"` 과 `fallback`·`diagnostics` 를 요구하는데
    실제 대화에는 픽스처도 진단도 없다. 화면이 실제로 쓰는 `ClarificationQuestion`
    모양만 공유하면 프로토타입의 `OptionFields` 를 그대로 재사용할 수 있다.

    `round` 는 되묻기를 한 번으로 묶기 위한 것이다. 0 = 처음 되물었다.
    이 값이 실린 응답에 사용자가 답하면 클라이언트가 그대로 돌려보내고,
    서버는 1 이상이면 판정을 건너뛴다.
    """

    status: Literal["ask", "handoff"]
    questions: list[ClarificationQuestion] = Field(default_factory=list)
    rule_id: str | None = None
    round: int = 0


class ClarificationAnswerRequest(BaseModel):
    """확정 또는 건너뛴 요약으로 RAG 답변을 시험하는 비영속 요청."""

    bot_id: int
    message: str = Field(min_length=1, max_length=4_000)


class ClarificationAnswerResponse(BaseModel):
    """저장하지 않는 최종 RAG 답변."""

    content: str
    citations: list[RAGCitation] = Field(default_factory=list)
    followups: list[str] = Field(default_factory=list)
    source: Literal["rag"] = "rag"
