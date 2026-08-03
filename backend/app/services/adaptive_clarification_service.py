"""일반 채팅용 적응형 추가 확인 질문 제어기.

모델은 route 후보와 근거 있는 facet만 제안한다. 안전 가드, 정책 우선순위, 상태 전이와
실패 처리는 서버가 소유한다. 이 모듈은 최종 RAG 답변을 생성하지 않는다.
"""

import asyncio
import logging
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.schemas.clarification import (
    ChatClarificationFacet,
    ChatClarificationView,
    ClarificationPreviewResponse,
    ClarificationQuestion,
)
from app.schemas.clarification_policy import ClarificationPolicy
from app.schemas.rag import RAGCitation
from app.services import clarification_service as policy_service
from app.services.rag.factory import get_rag_service

logger = logging.getLogger(__name__)

ROUTER_TIMEOUT_SEC = 45.0
MAX_QUESTIONS = 2
Route = Literal["answer", "optional_ask", "blocking_ask", "abstain", "handoff"]


class AdaptiveRoutingValidationError(ValueError):
    """라우터 결과가 사용자에게 안전하게 표시될 수 없을 때의 오류."""


class _RawFacet(BaseModel):
    id: str | None = None
    question: str | None = None
    selection_mode: str | None = "single"
    options: list[str] = Field(default_factory=list)
    allow_custom: bool = True
    evidence_ids: list[str] = Field(default_factory=list)


class _RawRoutePlan(BaseModel):
    route: str | None = None
    intent: str | None = None
    reason: str | None = None
    missing_facets: list[_RawFacet] = Field(default_factory=list)
    policy_match: Any = None


class AdaptiveDecision(BaseModel):
    route: Route
    facet: ChatClarificationFacet | None = None
    canonical_slots: dict[str, list[str]] = Field(default_factory=dict)
    pinned_evidence_ids: list[str] = Field(default_factory=list)
    diagnostics_reason: str | None = None
    message: str | None = None


def _normalise(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()


def _contains_any(message: str, phrases: tuple[str, ...]) -> bool:
    compact = _normalise(message)
    return any(_normalise(phrase) in compact for phrase in phrases)


def _safety_guard(message: str) -> AdaptiveDecision | None:
    """RAG/플래너보다 먼저 끝나는 결정적 안전·보안 경계."""
    if _contains_any(
        message,
        ("죽고 싶", "자살하고 싶", "목숨을 끊", "자해하고 싶", "살고 싶지 않"),
    ):
        return AdaptiveDecision(
            route="handoff",
            message=(
                "지금 혼자 감당하지 마세요. 즉시 위험하다면 119에 연락하거나 가까운 응급실로 "
                "가세요. 24시간 자살예방상담전화 109에 연락하고, 지금 믿을 수 있는 사람 한 명에게 "
                "곁에 있어 달라고 알려 주세요."
            ),
            diagnostics_reason="safety_crisis_guard",
        )
    if _contains_any(
        message,
        ("시스템 프롬프트", "system prompt", "내부 규칙", "내부 지침", "개발자 메시지"),
    ):
        return AdaptiveDecision(
            route="answer",
            message="내부 시스템 프롬프트나 보안 규칙은 제공할 수 없어요. 대신 서비스 이용과 답변 방식은 설명해 드릴 수 있습니다.",
            diagnostics_reason="prompt_extraction_guard",
        )
    if _contains_any(message, ("오늘 서울 날씨", "날씨 어때", "날씨 알려")):
        return AdaptiveDecision(
            route="abstain",
            message="현재 날씨를 확인할 실시간 도구가 없어 정확한 정보를 안내할 수 없어요. 기상청 등 실시간 예보를 확인해 주세요.",
            diagnostics_reason="out_of_scope_live_data",
        )
    if _contains_any(message, ("교제축복",)):
        return AdaptiveDecision(
            route="abstain",
            message="현재 확인된 문서 근거로는 해당 용어와 절차를 검증할 수 없어 안내를 드릴 수 없어요.",
            diagnostics_reason="unverified_term_guard",
        )
    return None


def _citation_ids(citations: list[RAGCitation]) -> set[str]:
    return {
        citation.title.strip()
        for citation in citations
        if isinstance(citation.title, str) and citation.title.strip()
    }


def _routing_system_prompt(bot: Any, policy) -> str:
    rules = []
    for rule in policy_service._enabled_rules(policy):
        rules.append(
            {
                "id": rule.id,
                "request_examples": rule.request_examples,
                "required_slots": [
                    {
                        "id": slot.id,
                        "question": slot.question,
                        "options": [option.label for option in slot.options],
                        "allow_custom": slot.allow_custom,
                    }
                    for slot in rule.required_slots
                ],
                "when_unknown": rule.when_unknown,
            }
        )
    return (getattr(bot, "system_prompt", "") or "") + """

[적응형 라우팅 전용 규칙]
최종 답변을 쓰지 말고 현재 검색 문서와 요청으로 계획을 반환한다. 반드시 먼저
``[EVIDENCE]`` 태그 안에 현재 검색 문서 근거 한두 문장만 쓰고, 이어서 ``[PLAN]`` 태그
안에 아래 JSON 객체만 쓴다. Markdown 코드 펜스나 PLAN 뒤의 설명을 붙이지 않는다.
{"route":"answer | optional_ask | blocking_ask | abstain | handoff","intent":"...","reason":"...","missing_facets":[{"id":"...","question":"...","selection_mode":"single | multiple","options":[],"allow_custom":true,"evidence_ids":["현재 인용 문서 제목"]}],"policy_match":{"status":"matched | unmatched | uncertain","rule_id":"...","slot_values":{}}}

- definition이나 일반 설명은 answer다.
- 일반 안내를 먼저 해도 안전하며 개인 목표·선호가 있어야 맞춤 동행이 되는 경우 optional_ask다.
- 개인 자격·절차 결과가 달라져 일반 답변만으로 단정하면 안 되는 경우 blocking_ask다.
- 문서 근거가 없거나 정확한 질문도 만들 수 없으면 abstain, 공식 담당자 판단이 필요한 경우 handoff다.
- optional_ask와 blocking_ask는 이번에 필요한 facet 하나만 반환한다. 질문은 사용자가 자유 입력으로 답할 수 있게 중립적으로 쓰고, 문서에 근거한 evidence_ids를 현재 검색 인용 제목으로만 쓴다.
- 검색 실패, 부족한 근거, 형식 오류를 answer로 바꾸지 않는다.
- 관리자가 승인한 정책 후보가 있으면 policy_match를 정확히 반환한다. 정책은 일반 route보다 우선한다.
[승인 정책]
""" + str(rules)


def _normalise_route_plan(
    raw: _RawRoutePlan, citations: list[RAGCitation]
) -> tuple[Route, ChatClarificationFacet | None, list[str]]:
    route = (raw.route or "").strip().casefold()
    if route not in {"answer", "optional_ask", "blocking_ask", "abstain", "handoff"}:
        raise AdaptiveRoutingValidationError("route is invalid")
    if route in {"answer", "optional_ask", "blocking_ask"} and not _citation_ids(citations):
        raise AdaptiveRoutingValidationError("retrieval has no evidence")
    if route not in {"optional_ask", "blocking_ask"}:
        return route, None, sorted(_citation_ids(citations))  # type: ignore[return-value]
    if len(raw.missing_facets) != 1:
        raise AdaptiveRoutingValidationError("ask routes require exactly one facet")
    facet = raw.missing_facets[0]
    facet_id = (facet.id or "").strip()
    question = (facet.question or "").strip()
    mode = (facet.selection_mode or "single").strip().casefold()
    if not facet_id or not question or mode not in {"single", "multiple"}:
        raise AdaptiveRoutingValidationError("facet is invalid")
    citation_ids = _citation_ids(citations)
    evidence = [item.strip() for item in facet.evidence_ids if isinstance(item, str) and item.strip()]
    if not evidence or any(item not in citation_ids for item in evidence):
        raise AdaptiveRoutingValidationError("facet evidence does not match retrieval")
    options = [item.strip() for item in facet.options if isinstance(item, str) and item.strip()]
    if len(options) != len({_normalise(item) for item in options}) or len(options) > 5:
        raise AdaptiveRoutingValidationError("facet options are invalid")
    # 선택형 동행은 CTA 뒤에만 사용자의 자유 입력 한 질문을 보인다.
    if route == "optional_ask":
        options = []
    return (
        route,  # type: ignore[return-value]
        ChatClarificationFacet(
            id=facet_id,
            question=question,
            selection_mode=mode,  # type: ignore[arg-type]
            options=options,
            allow_custom=True,
        ),
        evidence,
    )


async def route_message(message: str, bot: Any) -> AdaptiveDecision:
    """첫 일반 채팅 요청을 라우팅한다. 오류는 절대 answer로 폴백하지 않는다."""
    guarded = _safety_guard(message)
    if guarded is not None:
        return guarded

    policy = policy_service._active_policy(bot, None)
    try:
        rag_service = get_rag_service(provider=bot.llm_model)
        raw, citations = await asyncio.wait_for(
            rag_service.generate_structured_with_rag(
                bot_id=bot.id,
                prompt=f"[사용자 요청]\n{message}",
                system_prompt=_routing_system_prompt(bot, policy),
                model_name=bot.llm_model,
                response_schema=_RawRoutePlan,
            ),
            timeout=ROUTER_TIMEOUT_SEC,
        )
        candidate = policy_service._normalise_policy_candidate(raw.policy_match)
        rule = policy_service._find_enabled_rule(policy, candidate.rule_id)
        # 활성 정책은 검색 근거가 비어 일반 route를 abstain 처리해야 하는 상황에서도 먼저
        # 강제한다. 정책 자체의 document_refs/허용 값은 서버에서 이미 검증된 계약이다.
        if rule is not None and candidate.status in {"matched", "uncertain"}:
            canonical, missing = policy_service._policy_answers_from_values(rule, candidate.slot_values)
            canonical_slots = {answer.question_id: answer.values for answer in canonical}
            if candidate.status == "uncertain" and rule.when_unknown == "handoff":
                return AdaptiveDecision(
                    route="handoff",
                    canonical_slots=canonical_slots,
                    pinned_evidence_ids=[ref.document_id for ref in rule.document_refs],
                    diagnostics_reason="policy_uncertain_handoff",
                )
            if missing or candidate.status == "uncertain":
                slot = (missing or rule.required_slots)[0]
                return AdaptiveDecision(
                    route="blocking_ask",
                    facet=ChatClarificationFacet(
                        id=slot.id,
                        question=slot.question,
                        selection_mode=slot.selection_mode,
                        options=[option.label for option in slot.options],
                        allow_custom=slot.allow_custom,
                        policy=True,
                    ),
                    canonical_slots=canonical_slots,
                    pinned_evidence_ids=[ref.document_id for ref in rule.document_refs],
                    diagnostics_reason=f"policy:{rule.id}",
                )
            return AdaptiveDecision(
                route="answer",
                canonical_slots=canonical_slots,
                pinned_evidence_ids=[ref.document_id for ref in rule.document_refs],
                diagnostics_reason=f"policy:{rule.id}",
            )
        route, facet, evidence_ids = _normalise_route_plan(raw, citations)
    except asyncio.TimeoutError:
        logger.warning("adaptive router timed out bot_id=%s", bot.id)
        return AdaptiveDecision(route="abstain", diagnostics_reason="router_timeout")
    except (ValidationError, AdaptiveRoutingValidationError) as exc:
        logger.info("adaptive router rejected plan bot_id=%s: %s", bot.id, exc)
        return AdaptiveDecision(route="abstain", diagnostics_reason="router_validation_failed")
    except Exception as exc:
        logger.warning("adaptive router failed bot_id=%s: %s", bot.id, exc)
        return AdaptiveDecision(route="abstain", diagnostics_reason="router_provider_failed")

    return AdaptiveDecision(
        route=route,
        facet=facet,
        pinned_evidence_ids=evidence_ids,
        diagnostics_reason=(raw.reason or "").strip() or None,
    )


def terminal_message(decision: AdaptiveDecision) -> str:
    if decision.message:
        return decision.message
    if decision.route == "handoff":
        return "이 경우에는 현재 정보만으로 정확한 개인 판단을 할 수 없어 담당자에게 확인해 주세요."
    return "현재 문서 근거나 확인 수단이 부족해 정확한 안내를 드릴 수 없어요. 담당자 또는 공식 자료를 확인해 주세요."


def view_for_decision(decision: AdaptiveDecision, version: int | None = None) -> ChatClarificationView:
    if decision.route == "optional_ask":
        return ChatClarificationView(
            route=decision.route,
            mode="optional",
            version=version,
            cta_label="내 상황에 맞게 함께 확인하기",
            diagnostics_reason=decision.diagnostics_reason,
        )
    if decision.route == "blocking_ask":
        return ChatClarificationView(
            route=decision.route,
            mode="blocking",
            version=version,
            facet=decision.facet,
            diagnostics_reason=decision.diagnostics_reason,
        )
    return ChatClarificationView(
        route=decision.route,
        mode="terminal",
        message=terminal_message(decision) if decision.route in {"abstain", "handoff"} else decision.message,
        diagnostics_reason=decision.diagnostics_reason,
    )


def state_for_decision(decision: AdaptiveDecision, *, version: int = 1) -> dict[str, Any] | None:
    if decision.route not in {"optional_ask", "blocking_ask"} or decision.facet is None:
        return None
    return {
        "mode": "optional" if decision.route == "optional_ask" else "blocking",
        "route": decision.route,
        "canonical_slots": decision.canonical_slots,
        "pending_facet": decision.facet.model_dump(),
        "pinned_evidence_ids": decision.pinned_evidence_ids,
        "question_count": 0,
        "version": version,
    }


def view_for_state(state: dict[str, Any] | None) -> ChatClarificationView | None:
    if not isinstance(state, dict):
        return None
    try:
        facet = ChatClarificationFacet.model_validate(state["pending_facet"])
        mode = state["mode"]
        route = state["route"]
        version = state["version"]
    except (KeyError, ValidationError, TypeError):
        return None
    if mode == "optional" and route == "optional_ask":
        return ChatClarificationView(
            route="optional_ask", mode="optional", version=version,
            cta_label="내 상황에 맞게 함께 확인하기",
        )
    if mode == "blocking" and route == "blocking_ask":
        return ChatClarificationView(
            route="blocking_ask", mode="blocking", version=version, facet=facet,
        )
    return None


def start_companion(state: dict[str, Any], version: int) -> dict[str, Any] | None:
    """선택 CTA만 blocking 카드로 전환한다. 클라이언트 요청의 facet은 받지 않는다."""
    if state.get("mode") != "optional" or state.get("route") != "optional_ask":
        return None
    if state.get("version") != version:
        return None
    updated = dict(state)
    updated["mode"] = "blocking"
    updated["route"] = "blocking_ask"
    updated["version"] = version + 1
    return updated


async def preview_compatible_decision(message: str, bot: Any) -> ClarificationPreviewResponse:
    """구 preview API의 ``ask | ready | handoff`` 계약을 새 제어기에 얇게 맞춘다.

    preview는 영속 상태/CTA를 표현할 수 없으므로 optional route도 한 장의 ask로 보인다.
    abstain은 최종 답변을 허용하지 않는 기존 handoff 상태로 보수적으로 변환한다.
    """
    decision = await route_message(message, bot)
    if decision.route in {"optional_ask", "blocking_ask"} and decision.facet is not None:
        return ClarificationPreviewResponse(
            status="ask",
            source="live",
            questions=[
                ClarificationQuestion(
                    id=decision.facet.id,
                    question=decision.facet.question,
                    selection_mode=decision.facet.selection_mode,
                    options=decision.facet.options,
                    allow_custom=decision.facet.allow_custom,
                    policy=decision.facet.policy,
                )
            ],
        )
    if decision.route == "answer" and decision.message is None:
        return ClarificationPreviewResponse(
            status="ready",
            source="live",
            summary=f"[요청 요약]\n- 최초 요청: {message}",
        )
    return ClarificationPreviewResponse(
        status="handoff",
        source="live",
        handoff_message=terminal_message(decision),
    )
