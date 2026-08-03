"""관리자가 설정하는 추가 확인 질문 정책 계약."""

from typing import Literal

from pydantic import BaseModel, Field


class ClarificationPolicyOption(BaseModel):
    """정책 항목의 안정적인 선택지 식별자와 화면 문구."""

    id: str = ""
    label: str = ""


class ClarificationPolicyDocumentRef(BaseModel):
    """봇 File Search Store에 등록된 문서를 가리키는 참조."""

    document_id: str = ""
    label: str = ""


class ClarificationRequiredSlot(BaseModel):
    """답변 전에 반드시 받아야 하는 한 가지 사실."""

    id: str = ""
    label: str = ""
    question: str = ""
    selection_mode: Literal["single", "multiple"] = "single"
    options: list[ClarificationPolicyOption] = Field(default_factory=list)
    allow_custom: bool = True


class ClarificationPolicyRule(BaseModel):
    """업무별 질문 강제 규칙. 비활성 규칙은 초안으로 미완성일 수 있다."""

    id: str = ""
    name: str = ""
    enabled: bool = False
    priority: int = 0
    request_examples: list[str] = Field(default_factory=list)
    why_ask: str = ""
    document_refs: list[ClarificationPolicyDocumentRef] = Field(default_factory=list)
    required_slots: list[ClarificationRequiredSlot] = Field(default_factory=list)
    when_unknown: Literal["ask", "handoff", "allow_answer"] = "ask"


class ClarificationPolicy(BaseModel):
    """봇 단위 정책. 기본값은 기존 동작을 보존하는 비활성 상태다."""

    enabled: bool = False
    rules: list[ClarificationPolicyRule] = Field(default_factory=list)


DEFAULT_CLARIFICATION_POLICY = {"enabled": False, "rules": []}


def _normalise(value: str) -> str:
    return "".join(value.split()).casefold()


def validate_active_policy(
    policy: ClarificationPolicy,
    owned_document_ids: set[str],
) -> None:
    """공개되는 규칙만 완전한 계약과 봇 문서 소유를 검사한다.

    Pydantic 모델 자체는 초안 저장을 위해 관대하게 두고, 이 함수는 저장/테스트 전
    API 경계에서 호출한다.
    """

    seen_rule_ids: set[str] = set()
    for rule in policy.rules:
        rule_key = _normalise(rule.id)
        if not rule_key:
            if rule.enabled:
                raise ValueError("활성 규칙의 ID를 입력해 주세요.")
            continue
        if rule_key in seen_rule_ids:
            raise ValueError("규칙 ID는 서로 달라야 합니다.")
        seen_rule_ids.add(rule_key)

        if not rule.enabled:
            continue

        if not rule.name.strip():
            raise ValueError("활성 규칙의 이름을 입력해 주세요.")
        if not 2 <= len(rule.request_examples) <= 5 or any(
            not example.strip() for example in rule.request_examples
        ):
            raise ValueError("활성 규칙에는 요청 예시를 2~5개 입력해 주세요.")
        if not rule.why_ask.strip():
            raise ValueError("질문이 필요한 이유를 입력해 주세요.")
        if not rule.document_refs:
            raise ValueError("활성 규칙에는 근거 문서를 1개 이상 선택해 주세요.")
        for document_ref in rule.document_refs:
            if not document_ref.document_id.strip() or document_ref.document_id not in owned_document_ids:
                raise ValueError("선택한 근거 문서가 이 봇에 연결되어 있지 않습니다.")

        if not 1 <= len(rule.required_slots) <= 3:
            raise ValueError("활성 규칙에는 필수 확인 항목을 1~3개 등록해 주세요.")

        slot_ids: set[str] = set()
        for slot in rule.required_slots:
            slot_key = _normalise(slot.id)
            if not slot_key or slot_key in slot_ids:
                raise ValueError("필수 확인 항목 ID는 비어 있지 않고 서로 달라야 합니다.")
            slot_ids.add(slot_key)
            if not slot.label.strip() or not slot.question.strip():
                raise ValueError("필수 확인 항목의 이름과 질문을 입력해 주세요.")
            if not 2 <= len(slot.options) <= 5:
                raise ValueError("각 필수 확인 항목에는 선택지를 2~5개 등록해 주세요.")

            option_ids: set[str] = set()
            option_labels: set[str] = set()
            for option in slot.options:
                option_id = _normalise(option.id)
                option_label = _normalise(option.label)
                if not option_id or option_id in option_ids:
                    raise ValueError("선택지 ID는 비어 있지 않고 서로 달라야 합니다.")
                if not option_label or option_label in option_labels:
                    raise ValueError("선택지 문구는 비어 있지 않고 서로 달라야 합니다.")
                option_ids.add(option_id)
                option_labels.add(option_label)


class ClarificationPolicyTestRequest(BaseModel):
    """저장 전 관리자 테스트에 쓰는 정책과 사용자 요청."""

    clarification_policy: ClarificationPolicy
    message: str = Field(min_length=1, max_length=2_000)


class ClarificationPolicyTestResponse(BaseModel):
    """관리자 화면에만 노출하는 이해하기 쉬운 테스트 결과."""

    status: Literal["ask", "ready", "handoff"]
    applied_rule_name: str | None = None
    matched: bool = False
    missing_slots: list[str] = Field(default_factory=list)
    questions: list[ClarificationRequiredSlot] = Field(default_factory=list)
    document_refs: list[ClarificationPolicyDocumentRef] = Field(default_factory=list)
    message: str
