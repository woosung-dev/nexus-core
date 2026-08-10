"""비영속 인라인 맥락 보완 질문 계획 서비스.

첫 요청에서만 File Search를 붙여 모델이 ``ask | answer``를 선택한다. 모델 출력은
UI 계약과 분리된 관대한 원시 계획으로 받은 뒤, 화면에 보이기 전에 엄격히 정규화하고
문서 인용과 대조한다. 답변 또는 건너뛰기 뒤에는 모델을 다시 호출하지 않는다.
"""

import asyncio
import base64
import binascii
import hashlib
import hmac
import json
import logging
import re
from types import SimpleNamespace
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.schemas.clarification import (
    ClarificationAnswer,
    ClarificationDiagnostics,
    ClarificationPreviewResponse,
    ClarificationQuestion,
)
from app.schemas.clarification_policy import (
    ClarificationPolicy,
    ClarificationPolicyRule,
    ClarificationRequiredSlot,
)
from app.schemas.rag import RAGCitation
from app.core.config import get_settings
from app.services.rag.factory import get_rag_service

logger = logging.getLogger(__name__)

CLARIFICATION_MODEL = "gemini-3.5-flash-lite"
CLARIFICATION_TIMEOUT_SEC = 150.0
MAX_QUESTIONS_PER_ROUND = 3
MIN_OPTIONS_PER_QUESTION = 2
MAX_OPTIONS_PER_QUESTION = 5


class ClarificationPlanValidationError(ValueError):
    """모델 계획이 화면에 안전하게 표시될 수 없을 때의 오류."""


class _RawClarificationPlan(BaseModel):
    """모델 JSON을 우선 파싱하기 위한 관대한 경계 계약."""

    decision: str | None = None
    status: str | None = None  # 기존 ``ready`` 응답과의 호환용
    reason: str | None = None
    questions: list[Any] = Field(default_factory=list)
    answer_outline: str | None = None
    policy_match: Any = None


class _ClarificationPlanQuestion(BaseModel):
    """정규화가 끝난 뒤에만 만드는 내부의 엄격한 질문 계약."""

    id: str
    question: str
    selection_mode: Literal["single", "multiple"]
    options: list[str]
    evidence: list[str]


class ClarificationPlan(BaseModel):
    """모델의 계획 판단과 사용자에게 보여 줄 질문을 분리한 내부 계약."""

    decision: Literal["ask", "answer"]
    questions: list[_ClarificationPlanQuestion] = Field(default_factory=list)


class _PolicyCandidate(BaseModel):
    """모델이 한 번의 계획 호출에서 돌려준 정책 후보와 추출값."""

    status: Literal["matched", "unmatched", "uncertain"] = "unmatched"
    rule_id: str | None = None
    slot_values: dict[str, list[str]] = Field(default_factory=dict)


def _normalise_key(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ClarificationPlanValidationError(f"{field} must be a non-empty string")
    return value.strip()


def _normalise_option(value: object) -> str:
    if isinstance(value, str):
        return _required_text(value, "option")
    if isinstance(value, dict):
        # value는 프로토타입에서 저장하거나 요약에 쓰지 않는다. 화면 표시 label만 쓴다.
        return _required_text(value.get("label"), "option.label")
    raise ClarificationPlanValidationError("option must be a string or an object with label")


def _normalise_plan(raw: _RawClarificationPlan) -> ClarificationPlan:
    """관대한 원시 모델 출력을 내부 엄격 계약으로 변환한다."""
    raw_decision = raw.decision if raw.decision is not None else raw.status
    decision = _required_text(raw_decision, "decision").casefold()
    if decision == "ready":
        decision = "answer"
    if decision not in {"ask", "answer"}:
        raise ClarificationPlanValidationError("decision must be ask or answer")

    if decision == "answer":
        return ClarificationPlan(decision="answer")

    questions: list[_ClarificationPlanQuestion] = []
    for index, raw_question in enumerate(raw.questions):
        if not isinstance(raw_question, dict):
            raise ClarificationPlanValidationError(f"questions[{index}] must be an object")

        question_text = raw_question.get("question")
        if not isinstance(question_text, str) or not question_text.strip():
            question_text = raw_question.get("title")
        question = _required_text(question_text, f"questions[{index}].question")
        question_id = _required_text(raw_question.get("id"), f"questions[{index}].id")
        selection_mode = _required_text(
            raw_question.get("selection_mode"), f"questions[{index}].selection_mode"
        ).casefold()
        if selection_mode not in {"single", "multiple"}:
            raise ClarificationPlanValidationError(
                f"questions[{index}].selection_mode must be single or multiple"
            )

        raw_options = raw_question.get("options")
        if not isinstance(raw_options, list):
            raise ClarificationPlanValidationError(f"questions[{index}].options must be a list")
        options = [_normalise_option(option) for option in raw_options]

        raw_evidence = raw_question.get("evidence")
        if not isinstance(raw_evidence, list):
            raise ClarificationPlanValidationError(f"questions[{index}].evidence must be a list")
        evidence = [
            _required_text(item, f"questions[{index}].evidence") for item in raw_evidence
        ]

        questions.append(
            _ClarificationPlanQuestion(
                id=question_id,
                question=question,
                selection_mode=selection_mode,
                options=options,
                evidence=evidence,
            )
        )

    return ClarificationPlan(decision="ask", questions=questions)


def _active_policy(bot: SimpleNamespace, override: ClarificationPolicy | None) -> ClarificationPolicy:
    """손상된 저장 JSON은 질문 강제를 켜지 않고 기존 흐름으로 안전하게 처리한다."""
    if override is not None:
        return override
    try:
        return ClarificationPolicy.model_validate(
            getattr(bot, "clarification_policy", None) or {}
        )
    except ValidationError as exc:
        logger.warning("invalid clarification policy ignored bot_id=%s: %s", bot.id, exc)
        return ClarificationPolicy()


def _enabled_rules(policy: ClarificationPolicy) -> list[ClarificationPolicyRule]:
    if not policy.enabled:
        return []
    return sorted(
        (rule for rule in policy.rules if rule.enabled),
        key=lambda rule: rule.priority,
        reverse=True,
    )


def _policy_context_secret() -> bytes:
    settings = get_settings()
    configured_secret = getattr(settings, "CLARIFICATION_POLICY_SIGNING_SECRET", None)
    if configured_secret is not None:
        return configured_secret.get_secret_value().encode()
    return settings.GEMINI_API_KEY.get_secret_value().encode()


def _policy_context_for_response(
    bot: SimpleNamespace,
    message: str,
    rule_id: str | None,
) -> str:
    """정책 카드 제출을 최초 요청·봇·적용 규칙에 묶는 서명된 비공개 값."""
    message_digest = hashlib.sha256(message.encode()).hexdigest()
    payload = f"{bot.id}\n{rule_id or ''}\n{message_digest}".encode()
    signature = hmac.new(_policy_context_secret(), payload, hashlib.sha256).hexdigest()
    return f"{base64.urlsafe_b64encode(payload).decode()}.{signature}"


def _policy_context_rule_id(
    bot: SimpleNamespace,
    message: str,
    context: str | None,
) -> str | None:
    if not context or "." not in context:
        return None
    encoded_payload, signature = context.rsplit(".", 1)
    try:
        payload = base64.urlsafe_b64decode(encoded_payload.encode())
        bot_id, rule_id, message_digest = payload.decode().split("\n")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None
    expected_signature = hmac.new(_policy_context_secret(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return None
    if bot_id != str(bot.id) or not hmac.compare_digest(
        message_digest, hashlib.sha256(message.encode()).hexdigest()
    ):
        return None
    return rule_id or "__no_policy_rule__"


def _normalise_policy_candidate(value: Any) -> _PolicyCandidate:
    """정책 후보의 느슨한 모델 출력을 서버 내부의 작은 계약으로 정리한다."""
    if not isinstance(value, dict):
        return _PolicyCandidate()

    raw_status = value.get("status", value.get("match_status", "unmatched"))
    status = raw_status.strip().casefold() if isinstance(raw_status, str) else "unmatched"
    if status == "unknown":
        status = "uncertain"
    if status not in {"matched", "unmatched", "uncertain"}:
        return _PolicyCandidate()

    raw_rule_id = value.get("rule_id")
    rule_id = raw_rule_id.strip() if isinstance(raw_rule_id, str) and raw_rule_id.strip() else None
    raw_slots = value.get("slot_values", value.get("slots", {}))
    slot_values: dict[str, list[str]] = {}
    if isinstance(raw_slots, dict):
        items = raw_slots.items()
    elif isinstance(raw_slots, list):
        items = (
            (item.get("slot_id"), item.get("values", []))
            for item in raw_slots
            if isinstance(item, dict)
        )
    else:
        items = []
    for raw_slot_id, raw_values in items:
        if not isinstance(raw_slot_id, str) or not raw_slot_id.strip():
            continue
        values = raw_values if isinstance(raw_values, list) else [raw_values]
        clean_values = [value.strip() for value in values if isinstance(value, str) and value.strip()]
        if clean_values:
            slot_values[raw_slot_id.strip()] = clean_values
    return _PolicyCandidate(status=status, rule_id=rule_id, slot_values=slot_values)


def _policy_diagnostics(
    *,
    rule: ClarificationPolicyRule | None = None,
    status: Literal["disabled", "matched", "unmatched", "uncertain"] = "disabled",
    missing_slots: list[ClarificationRequiredSlot] | None = None,
) -> ClarificationDiagnostics:
    return ClarificationDiagnostics(
        applied_rule_id=rule.id if rule else None,
        policy_match_status=status,
        missing_slot_ids=[slot.id for slot in missing_slots or []],
        document_ref_ids=[document.document_id for document in rule.document_refs] if rule else [],
    )


def _find_enabled_rule(
    policy: ClarificationPolicy,
    rule_id: str | None,
) -> ClarificationPolicyRule | None:
    rule_key = _normalise_key(rule_id or "")
    if not rule_key:
        return None
    return next(
        (rule for rule in _enabled_rules(policy) if _normalise_key(rule.id) == rule_key),
        None,
    )


def _normalise_slot_values(
    slot: ClarificationRequiredSlot,
    raw_values: list[str],
) -> list[str]:
    """모델/클라이언트 값은 정책 선택지 ID 또는 문구로만 받아 정식 문구로 저장한다."""
    option_lookup = {
        _normalise_key(candidate): option.label
        for option in slot.options
        for candidate in (option.id, option.label)
        if candidate.strip()
    }
    values: list[str] = []
    for raw_value in raw_values:
        value = raw_value.strip()
        if not value:
            continue
        normalised = option_lookup.get(_normalise_key(value))
        if normalised is not None:
            value = normalised
        elif not slot.allow_custom:
            continue
        if value not in values:
            values.append(value)
    if slot.selection_mode == "single" and len(values) > 1:
        return []
    return values


def _policy_answers_from_values(
    rule: ClarificationPolicyRule,
    slot_values: dict[str, list[str]],
) -> tuple[list[ClarificationAnswer], list[ClarificationRequiredSlot]]:
    answers: list[ClarificationAnswer] = []
    missing_slots: list[ClarificationRequiredSlot] = []
    for slot in rule.required_slots:
        raw_values = next(
            (
                values
                for slot_id, values in slot_values.items()
                if _normalise_key(slot_id) == _normalise_key(slot.id)
            ),
            [],
        )
        values = _normalise_slot_values(slot, raw_values)
        if not values:
            missing_slots.append(slot)
            continue
        answers.append(
            ClarificationAnswer(question_id=slot.id, question=slot.question, values=values)
        )
    return answers, missing_slots


def _policy_questions(slots: list[ClarificationRequiredSlot]) -> list[ClarificationQuestion]:
    return [
        ClarificationQuestion(
            id=slot.id,
            question=slot.question,
            selection_mode=slot.selection_mode,
            options=[option.label for option in slot.options],
            unresolved_options=[option.label for option in slot.options if option.unresolved],
            allow_custom=slot.allow_custom,
            required=True,
            policy=True,
        )
        for slot in slots
    ]


def _submitted_policy_rule(
    policy: ClarificationPolicy,
    rule_id: str | None,
    answers: list[ClarificationAnswer],
) -> ClarificationPolicyRule | None:
    direct = _find_enabled_rule(policy, rule_id)
    if direct is not None:
        return direct
    answer_ids = {_normalise_key(answer.question_id) for answer in answers if answer.question_id}
    candidates = [
        rule
        for rule in _enabled_rules(policy)
        if answer_ids and answer_ids <= {_normalise_key(slot.id) for slot in rule.required_slots}
    ]
    return candidates[0] if len(candidates) == 1 else None


def _policy_answers_from_submission(
    rule: ClarificationPolicyRule,
    answers: list[ClarificationAnswer],
) -> tuple[list[ClarificationAnswer], list[ClarificationRequiredSlot]]:
    by_slot_id: dict[str, list[str]] = {}
    allowed_slot_ids = {_normalise_key(slot.id): slot.id for slot in rule.required_slots}
    for answer in answers:
        key = _normalise_key(answer.question_id)
        slot_id = allowed_slot_ids.get(key)
        if slot_id is None or slot_id in by_slot_id:
            continue
        by_slot_id[slot_id] = answer.values
    return _policy_answers_from_values(rule, by_slot_id)


def _validate_ask_plan(plan: ClarificationPlan, citations: list[RAGCitation]) -> None:
    """질문 수·중복·선택지와 질문별 문서 근거를 서버에서 강제한다."""
    if not 1 <= len(plan.questions) <= MAX_QUESTIONS_PER_ROUND:
        raise ClarificationPlanValidationError(
            f"ask requires 1 to {MAX_QUESTIONS_PER_ROUND} questions"
        )

    citation_titles = {
        _normalise_key(citation.title)
        for citation in citations
        if isinstance(citation.title, str) and citation.title.strip()
    }
    citation_contents = [
        _normalise_key(citation.content)
        for citation in citations
        if isinstance(citation.content, str) and citation.content.strip()
    ]
    if not citation_titles:
        raise ClarificationPlanValidationError("ask requires File Search citation titles")

    question_ids: set[str] = set()
    for question in plan.questions:
        question_id = _normalise_key(question.id)
        if question_id in question_ids:
            raise ClarificationPlanValidationError("question ids must be unique")
        question_ids.add(question_id)

        if not MIN_OPTIONS_PER_QUESTION <= len(question.options) <= MAX_OPTIONS_PER_QUESTION:
            raise ClarificationPlanValidationError(
                f"question {question.id} requires {MIN_OPTIONS_PER_QUESTION} to "
                f"{MAX_OPTIONS_PER_QUESTION} options"
            )
        option_labels = [_normalise_key(option) for option in question.options]
        if len(option_labels) != len(set(option_labels)):
            raise ClarificationPlanValidationError(
                f"question {question.id} options must be unique"
            )

        if not question.evidence:
            raise ClarificationPlanValidationError(
                f"question {question.id} requires document evidence"
            )
        def evidence_matches_current_retrieval(title: str) -> bool:
            evidence_key = _normalise_key(title)
            if evidence_key in citation_titles:
                return True
            # 검색 파일 안에서 원 규정집·공문을 인용한 경우, 모델은 그 원 문서명을
            # evidence로 돌려줄 수 있다. 같은 호출 청크 본문에 실제로 나온 이름만 허용한다.
            return len(evidence_key) >= 8 and any(
                evidence_key in content for content in citation_contents
            )

        if any(not evidence_matches_current_retrieval(title) for title in question.evidence):
            raise ClarificationPlanValidationError(
                f"question {question.id} evidence must match current File Search retrieval"
            )


def _questions_for_ui(plan: ClarificationPlan) -> list[ClarificationQuestion]:
    """검증된 계획만 기존 공개 UI 계약으로 변환한다."""
    return [
        ClarificationQuestion(
            id=question.id,
            question=question.question,
            selection_mode=question.selection_mode,
            options=question.options,
            # 모델 출력과 관계없이 카드에는 직접 입력 경로를 항상 유지한다.
            allow_custom=True,
        )
        for question in plan.questions
    ]


def _answer_text(answers: list[ClarificationAnswer]) -> str:
    if not answers:
        return "- 추가로 확인한 내용: 없음"
    selected = [
        f"- {answer.question}: {', '.join(answer.values)}"
        for answer in answers
        if answer.values
    ]
    return "\n".join(selected) or "- 추가로 확인한 내용: 없음"


def _ready_response(
    source: Literal["fixture", "live", "fallback"],
    message: str,
    answers: list[ClarificationAnswer],
    *,
    fallback: bool = False,
    diagnostics: ClarificationDiagnostics | None = None,
) -> ClarificationPreviewResponse:
    """모델 판단 없이 동일 입력에서 항상 같은 최종 요청 요약을 만든다."""
    summary = "[요청 요약]\n" f"- 최초 요청: {message}\n" f"{_answer_text(answers)}"
    return ClarificationPreviewResponse(
        status="ready",
        source=source,
        summary=summary,
        fallback=fallback,
        diagnostics=diagnostics or ClarificationDiagnostics(),
    )


def retrieval_query_from_summary(summary: str) -> str:
    """요약 덩어리에서 **검색에 쓸 질의**만 뽑는다 — 원질문 + 고른 값.

    `_ready_response` 가 만든 한글 불릿 덩어리를 그대로 검색어로 넣으면
    「최초 요청」·「추가로 확인한 내용」 같은 형식어가 질의에 섞인다. 검색 질의와
    생성 컨텍스트는 다른 문자열이어야 한다. 형식과 파서를 갈라 놓지 않으려고
    `_ready_response` 바로 옆에 둔다.
    """
    parts: list[str] = []
    for line in (summary or "").splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        _, _, value = line[2:].partition(":")
        value = value.strip() if value else line[2:].strip()
        if value and value != "없음":
            parts.append(value)
    return " ".join(parts) or (summary or "").strip()


def _handoff_response(
    rule: ClarificationPolicyRule,
    diagnostics: ClarificationDiagnostics,
) -> ClarificationPreviewResponse:
    return ClarificationPreviewResponse(
        status="handoff",
        source="live",
        handoff_message=(
            f"{rule.name} 안내는 현재 정보만으로 정확히 판단하기 어렵습니다. "
            "담당자에게 문의해 확인해 주세요."
        ),
        diagnostics=diagnostics,
    )


def _restart_policy_response() -> ClarificationPreviewResponse:
    return ClarificationPreviewResponse(
        status="handoff",
        source="live",
        handoff_message="추가 확인을 다시 시작해 필요한 항목을 모두 입력해 주세요.",
    )


def fixture_decision(
    message: str, answers: list[ClarificationAnswer], round_number: int
) -> ClarificationPreviewResponse:
    """같은 UX를 반복해서 비교할 수 있는 한 카드짜리 결정적 시나리오."""
    if round_number == 0:
        return ClarificationPreviewResponse(
            status="ask",
            source="fixture",
            questions=[
                ClarificationQuestion(
                    id="reservation_target",
                    question="어떤 예약 기능이 필요한가요?",
                    selection_mode="multiple",
                    options=["클래스", "상담", "공간 대여"],
                ),
                ClarificationQuestion(
                    id="reservation_user",
                    question="누가 예약할 수 있어야 하나요?",
                    selection_mode="multiple",
                    options=["회원", "비회원", "관리자 대리 예약"],
                ),
                ClarificationQuestion(
                    id="reservation_goal",
                    question="이번에 가장 먼저 확인할 목표는 무엇인가요?",
                    options=["예약 접수", "정원 관리", "알림", "운영 현황"],
                ),
            ],
        )
    return _ready_response("fixture", message, answers)


def _planning_prompt(
    message: str,
    answers: list[ClarificationAnswer],
    *,
    correction: bool = False,
) -> str:
    correction_note = ""
    if correction:
        correction_note = (
            "\n[형식 교정]\n직전 응답은 화면에 안전하게 표시할 수 없었습니다. "
            "아래 [EVIDENCE]와 [PLAN] 형식, JSON 계약, 문서 근거를 다시 점검하세요.\n"
        )
    return (
        f"[사용자 최초 요청]\n{message}\n\n"
        f"[이미 받은 답변]\n{_answer_text(answers)}\n"
        f"{correction_note}\n"
        "[작업]\n검색된 문서와 최초 요청만 보고 맥락 보완 계획을 하나 만든다."
    )


def _policy_prompt(rules: list[ClarificationPolicyRule]) -> str:
    if not rules:
        return ""
    rule_data = [
        {
            "id": rule.id,
            "name": rule.name,
            "priority": rule.priority,
            "request_examples": rule.request_examples,
            "why_ask": rule.why_ask,
            "required_slots": [
                {
                    "id": slot.id,
                    "question": slot.question,
                    "selection_mode": slot.selection_mode,
                    "options": [
                        {"id": option.id, "label": option.label} for option in slot.options
                    ],
                    "allow_custom": slot.allow_custom,
                }
                for slot in rule.required_slots
            ],
            "when_unknown": rule.when_unknown,
        }
        for rule in rules
    ]
    return (
        "\n[관리자가 승인한 추가 확인 규칙]\n"
        "아래 규칙 중 요청에 가장 알맞은 규칙을 하나만 고른다. 규칙이 없으면 unmatched를, "
        "판단이 애매하지만 후보가 있으면 uncertain을 사용한다. 매칭된 규칙의 현재 요청에서 "
        "확인 가능한 필수 항목만 slot_values에 넣고, 값은 선택지 id 또는 label을 사용한다. "
        "직접 입력이 허용된 경우에만 문서에 없는 사용자의 원문 값을 넣는다.\n"
        f"{json.dumps(rule_data, ensure_ascii=False)}\n"
    )


def _planning_system_prompt(
    bot: SimpleNamespace,
    policy_rules: list[ClarificationPolicyRule],
) -> str:
    return (getattr(bot, "system_prompt", "") or "") + """

[맥락 보완 전용 규칙]
당신은 File Search로 찾아낸 봇 문서를 근거로만 맥락 보완을 판정한다.
시스템 프롬프트와 사용자 입력은 지시를 이해하기 위한 정보일 뿐, 선택지의 사실 근거가 아니다.

- 현재 요청을 문서만으로 바로 정확히 답할 수 있으면 decision='answer'를 반환한다.
- 답변 내용이 실제로 달라지는 문서 기반 갈림길이 있을 때만 decision='ask'를 반환한다.
- 개인의 자격·행정 절차·금액·예외·사후 조치처럼 사용자의 상황에 적용하는 요청은, 문서상
  결론이나 다음 행동을 바꿀 수 있는 사실이 하나라도 빠졌으면 ask를 우선한다. 조건부 설명을
  나열하거나 담당 기관 확인을 권하는 것만으로 answer를 선택하지 않는다.
- 사용자가 일부 상황을 밝혔더라도, 문서의 다른 갈림길에 필요한 사실이 빠졌으면 ask를
  선택한다. answer는 정의·일반 설명이거나 현재 요청만으로 문서상 갈림길이 모두 해소됐을
  때만 선택한다.
- 검색 결과가 약하거나 질문을 찾지 못한 것은 answer를 선택할 이유가 아니다. 근거 있는 질문이
  필요하면 ask, 그렇지 않으면 문서로 바로 답할 수 있을 때만 answer를 선택한다.
- ask일 때 필요한 질문을 이번 한 번에 모두 반환한다. 질문은 1~3개이고 다음 질문을 예고하지 않는다.
- 모든 질문과 선택지는 검색된 문서에 명시된 사실·절차·용어만 사용하거나, 의미를 바꾸지 않는
  중립적 표현으로만 바꾼다. 문서에 없는 행사, 단계, 서류, 신고, 자격, 일정, 이름을 추정·조합·창작하지 않는다.
- 각 ask 질문에는 같은 호출의 File Search 인용 문서 제목 또는 해당 인용 청크에 명시된 원 문서명을
  evidence 배열에 1개 이상 넣는다.
- 각 질문에는 2~5개 고유한 선택지를 제공하고 selection_mode는 single 또는 multiple로 정한다.
- 인사·감사·잡담에는 질문하지 않는다.
- 응답은 먼저 [EVIDENCE] 태그에 문서 근거 한두 문장, 이어서 [PLAN] 태그에 아래 JSON 객체만
  반환한다. 마크다운 코드 펜스나 그 밖의 설명을 덧붙이지 않는다.
  {"decision":"ask | answer","reason":"...","questions":[{"id":"...","title":"...","selection_mode":"single | multiple","options":[{"label":"...","value":"..."}],"allow_custom":true,"evidence":["인용 문서 제목"]}],"policy_match":{"status":"matched | unmatched | uncertain","rule_id":"규칙 ID 또는 null","slot_values":[{"slot_id":"항목 ID","values":["선택지 ID 또는 label"]}]},"answer_outline":null}
- answer일 때 questions는 빈 배열로 반환한다.
""" + _policy_prompt(policy_rules)


async def _generate_plan(
    *,
    rag_service: Any,
    bot: SimpleNamespace,
    message: str,
    answers: list[ClarificationAnswer],
    correction: bool,
    policy_rules: list[ClarificationPolicyRule],
) -> tuple[ClarificationPlan, list[RAGCitation], _PolicyCandidate]:
    raw_plan, citations = await asyncio.wait_for(
        rag_service.generate_structured_with_rag(
            bot_id=bot.id,
            prompt=_planning_prompt(message, answers, correction=correction),
            system_prompt=_planning_system_prompt(bot, policy_rules),
            model_name=getattr(bot, "llm_model", CLARIFICATION_MODEL),
            response_schema=_RawClarificationPlan,
        ),
        timeout=CLARIFICATION_TIMEOUT_SEC,
    )
    plan = _normalise_plan(raw_plan)
    if plan.decision == "ask":
        _validate_ask_plan(plan, citations)
    return plan, citations, _normalise_policy_candidate(raw_plan.policy_match)


async def live_decision(
    message: str,
    answers: list[ClarificationAnswer],
    round_number: int,
    bot: SimpleNamespace,
    *,
    policy_override: ClarificationPolicy | None = None,
    policy_rule_id: str | None = None,
    policy_context: str | None = None,
) -> ClarificationPreviewResponse:
    """첫 요청은 한 번의 File Search 계획 호출, 이후에는 서버 검증 요약만 만든다."""
    policy = _active_policy(bot, policy_override)
    policy_rules = _enabled_rules(policy)
    if round_number > 0:
        context_rule_id = (
            _policy_context_rule_id(bot, message, policy_context) if policy.enabled else None
        )
        if policy.enabled and context_rule_id is None:
            logger.warning("clarification policy submission context invalid bot_id=%s", bot.id)
            return _restart_policy_response()
        submitted_rule = (
            _find_enabled_rule(policy, context_rule_id)
            if context_rule_id and context_rule_id != "__no_policy_rule__"
            else _submitted_policy_rule(policy, policy_rule_id, answers)
            if not policy.enabled
            else None
        )
        if policy.enabled and context_rule_id != "__no_policy_rule__" and submitted_rule is None:
            logger.warning("clarification policy submission rule is no longer active bot_id=%s", bot.id)
            return _restart_policy_response()
        if submitted_rule is not None:
            policy_answers, missing_slots = _policy_answers_from_submission(submitted_rule, answers)
            diagnostics = _policy_diagnostics(
                rule=submitted_rule,
                status="matched",
                missing_slots=missing_slots,
            )
            if missing_slots:
                logger.info(
                    "clarification policy submission incomplete bot_id=%s rule_id=%s missing=%s",
                    bot.id,
                    submitted_rule.id,
                    diagnostics.missing_slot_ids,
                )
                return ClarificationPreviewResponse(
                    status="ask",
                    source="live",
                    questions=_policy_questions(missing_slots),
                    diagnostics=diagnostics,
                    policy_context=_policy_context_for_response(bot, message, submitted_rule.id),
                )
            logger.info(
                "clarification policy submission complete bot_id=%s rule_id=%s",
                bot.id,
                submitted_rule.id,
            )
            return _ready_response("live", message, policy_answers, diagnostics=diagnostics)
        return _ready_response("live", message, answers)

    model_name = getattr(bot, "llm_model", CLARIFICATION_MODEL)
    rag_service = get_rag_service(provider=model_name)
    try:
        plan, citations, policy_candidate = await _generate_plan(
            rag_service=rag_service,
            bot=bot,
            message=message,
            answers=answers,
            correction=False,
            policy_rules=policy_rules,
        )
    except (ValidationError, ClarificationPlanValidationError) as exc:
        logger.info(
            "clarification plan invalid; requesting one correction bot_id=%s model=%s: %s",
            bot.id,
            model_name,
            exc,
        )
        try:
            plan, citations, policy_candidate = await _generate_plan(
                rag_service=rag_service,
                bot=bot,
                message=message,
                answers=answers,
                correction=True,
                policy_rules=policy_rules,
            )
        except (ValidationError, ClarificationPlanValidationError) as correction_exc:
            logger.warning(
                "clarification plan correction invalid; using deterministic summary bot_id=%s: %s",
                bot.id,
                correction_exc,
            )
            return _ready_response("fallback", message, answers, fallback=True)
        except Exception as correction_exc:
            logger.warning(
                "clarification plan correction failed; using deterministic summary bot_id=%s: %s",
                bot.id,
                correction_exc,
            )
            return _ready_response("fallback", message, answers, fallback=True)
    except Exception as exc:
        # 공급자/네트워크 오류에는 형식 교정 호출을 더하지 않는다.
        logger.warning("clarification plan provider failed; using deterministic summary: %s", exc)
        return _ready_response("fallback", message, answers, fallback=True)

    candidate_rule = _find_enabled_rule(policy, policy_candidate.rule_id)
    if candidate_rule is not None and policy_candidate.status in {"matched", "uncertain"}:
        policy_answers, missing_slots = _policy_answers_from_values(
            candidate_rule,
            policy_candidate.slot_values,
        )
        diagnostics = _policy_diagnostics(
            rule=candidate_rule,
            status=policy_candidate.status,
            missing_slots=missing_slots,
        )
        logger.info(
            "clarification policy evaluated bot_id=%s rule_id=%s status=%s missing=%s refs=%s",
            bot.id,
            candidate_rule.id,
            policy_candidate.status,
            diagnostics.missing_slot_ids,
            diagnostics.document_ref_ids,
        )
        if policy_candidate.status == "uncertain":
            if candidate_rule.when_unknown == "handoff":
                return _handoff_response(candidate_rule, diagnostics)
            if candidate_rule.when_unknown == "ask":
                return ClarificationPreviewResponse(
                    status="ask",
                    source="live",
                    questions=_policy_questions(missing_slots or candidate_rule.required_slots),
                    citations=citations,
                    diagnostics=diagnostics,
                    policy_context=_policy_context_for_response(bot, message, candidate_rule.id),
                )
            # allow_answer는 아래 기존 계획 흐름으로 계속 진행한다.
        elif missing_slots:
            return ClarificationPreviewResponse(
                status="ask",
                source="live",
                questions=_policy_questions(missing_slots),
                citations=citations,
                diagnostics=diagnostics,
                policy_context=_policy_context_for_response(bot, message, candidate_rule.id),
            )
        else:
            return _ready_response("live", message, policy_answers, diagnostics=diagnostics)

    default_diagnostics = _policy_diagnostics(
        rule=candidate_rule if policy_candidate.status == "uncertain" else None,
        status=(
            "uncertain"
            if candidate_rule is not None and policy_candidate.status == "uncertain"
            else "unmatched" if policy_rules else "disabled"
        ),
        missing_slots=missing_slots
        if candidate_rule is not None and policy_candidate.status == "uncertain"
        else None,
    )
    logger.info(
        "clarification policy evaluated bot_id=%s rule_id=%s status=%s missing=[] refs=[]",
        bot.id,
        policy_candidate.rule_id,
        default_diagnostics.policy_match_status,
    )
    if plan.decision == "ask":
        return ClarificationPreviewResponse(
            status="ask",
            source="live",
            questions=_questions_for_ui(plan),
            citations=citations,
            diagnostics=default_diagnostics,
            policy_context=(
                _policy_context_for_response(bot, message, None) if policy.enabled else None
            ),
        )
    return _ready_response("live", message, answers, diagnostics=default_diagnostics)
