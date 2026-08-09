from types import SimpleNamespace

import pytest

from app.schemas.clarification import ClarificationAnswer
from app.schemas.clarification_policy import ClarificationPolicy, validate_active_policy
from app.schemas.rag import RAGCitation
from app.services import clarification_service


def _policy(*, when_unknown="ask") -> ClarificationPolicy:
    return ClarificationPolicy.model_validate(
        {
            "enabled": True,
            "rules": [
                {
                    "id": "refund",
                    "name": "환불 가능 여부",
                    "enabled": True,
                    "priority": 100,
                    "request_examples": ["환불 가능한가요?", "헌금 환불이 되나요?"],
                    "why_ask": "유형과 진행 단계에 따라 안내가 달라집니다.",
                    "document_refs": [{"document_id": "doc-1", "label": "규정집 p.52"}],
                    "required_slots": [
                        {
                            "id": "type",
                            "label": "유형",
                            "question": "어떤 유형에 해당하시나요?",
                            "selection_mode": "single",
                            "options": [
                                {"id": "first", "label": "1세"},
                                {"id": "second", "label": "2세"},
                            ],
                            "allow_custom": False,
                        },
                        {
                            "id": "stage",
                            "label": "진행 단계",
                            "question": "현재 어느 단계인가요?",
                            "selection_mode": "single",
                            "options": [
                                {"id": "before", "label": "진행 전"},
                                {"id": "after", "label": "진행 후"},
                            ],
                            "allow_custom": True,
                        },
                    ],
                    "when_unknown": when_unknown,
                }
            ],
        }
    )


BOT = SimpleNamespace(
    id=11,
    llm_model="gemini-3.5-flash-lite",
    system_prompt="테스트 봇",
)


class _FakeRAG:
    def __init__(self, plan):
        self.plan = plan
        self.calls = []

    async def generate_structured_with_rag(self, **kwargs):
        self.calls.append(kwargs)
        return (
            kwargs["response_schema"](**self.plan),
            [RAGCitation(title="규정집", content="정책 근거")],
        )


def test_incomplete_draft_is_storable_but_active_rule_is_complete_and_owned():
    draft = ClarificationPolicy.model_validate(
        {"enabled": False, "rules": [{"id": "draft", "enabled": False}]}
    )
    validate_active_policy(draft, set())

    with pytest.raises(ValueError, match="이름"):
        validate_active_policy(
            ClarificationPolicy.model_validate(
                {"enabled": True, "rules": [{"id": "open", "enabled": True}]}
            ),
            set(),
        )

    with pytest.raises(ValueError, match="연결되어 있지"):
        validate_active_policy(_policy(), {"another-document"})

    validate_active_policy(_policy(), {"doc-1"})


@pytest.mark.asyncio
async def test_matching_policy_forces_its_missing_cards_even_when_plan_answers(monkeypatch):
    rag = _FakeRAG(
        {
            "decision": "answer",
            "policy_match": {
                "status": "matched",
                "rule_id": "refund",
                "slot_values": [{"slot_id": "type", "values": ["first"]}],
            },
        }
    )
    monkeypatch.setattr(clarification_service, "get_rag_service", lambda **_kwargs: rag)

    result = await clarification_service.live_decision(
        "환불 가능한가요?", [], 0, BOT, policy_override=_policy()
    )

    assert result.status == "ask"
    assert [question.id for question in result.questions] == ["stage"]
    assert result.questions[0].required is True
    assert result.questions[0].policy is True
    assert result.diagnostics.applied_rule_id == "refund"
    assert result.diagnostics.document_ref_ids == ["doc-1"]
    assert result.policy_context
    assert len(rag.calls) == 1


@pytest.mark.asyncio
async def test_complete_matching_policy_uses_verified_values_without_a_second_plan_call(monkeypatch):
    rag = _FakeRAG(
        {
            "decision": "answer",
            "policy_match": {
                "status": "matched",
                "rule_id": "refund",
                "slot_values": {
                    "type": ["first"],
                    "stage": ["진행 후"],
                },
            },
        }
    )
    monkeypatch.setattr(clarification_service, "get_rag_service", lambda **_kwargs: rag)

    result = await clarification_service.live_decision(
        "1세인데 이미 진행했어요. 환불이 되나요?", [], 0, BOT, policy_override=_policy()
    )

    assert result.status == "ready"
    assert "어떤 유형에 해당하시나요?: 1세" in (result.summary or "")
    assert "현재 어느 단계인가요?: 진행 후" in (result.summary or "")
    assert len(rag.calls) == 1


@pytest.mark.asyncio
async def test_policy_submission_revalidates_options_and_never_uses_client_question_text(monkeypatch):
    monkeypatch.setattr(
        clarification_service,
        "get_rag_service",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("계획 호출이 없어야 합니다.")),
    )
    policy = _policy()
    policy_context = clarification_service._policy_context_for_response(
        BOT, "환불 가능한가요?", "refund"
    )

    incomplete = await clarification_service.live_decision(
        "환불 가능한가요?",
        [
            ClarificationAnswer(question_id="type", question="바꾼 질문", values=["허용 안 됨"]),
            ClarificationAnswer(question_id="stage", question="바꾼 질문", values=["진행 후"]),
        ],
        1,
        BOT,
        policy_override=policy,
        policy_rule_id="refund",
        policy_context=policy_context,
    )
    assert incomplete.status == "ask"
    assert [question.id for question in incomplete.questions] == ["type"]

    complete = await clarification_service.live_decision(
        "환불 가능한가요?",
        [
            ClarificationAnswer(question_id="type", question="클라이언트 문구", values=["first"]),
            ClarificationAnswer(question_id="stage", question="클라이언트 문구", values=["진행 후"]),
        ],
        1,
        BOT,
        policy_override=policy,
        policy_rule_id="refund",
        policy_context=policy_context,
    )
    assert complete.status == "ready"
    assert "어떤 유형에 해당하시나요?" in (complete.summary or "")
    assert "클라이언트 문구" not in (complete.summary or "")


@pytest.mark.asyncio
async def test_policy_submission_without_the_issued_context_cannot_skip_cards():
    result = await clarification_service.live_decision(
        "환불 가능한가요?",
        [],
        1,
        BOT,
        policy_override=_policy(),
        policy_rule_id="refund",
    )

    assert result.status == "handoff"
    assert "다시 시작" in (result.handoff_message or "")


@pytest.mark.asyncio
async def test_unmatched_policy_keeps_existing_plan_flow(monkeypatch):
    rag = _FakeRAG(
        {
            "decision": "ask",
            "questions": [
                {
                    "id": "existing",
                    "question": "기존 질문인가요?",
                    "selection_mode": "single",
                    "options": ["예", "아니요"],
                    "evidence": ["규정집"],
                }
            ],
            "policy_match": {"status": "unmatched"},
        }
    )
    monkeypatch.setattr(clarification_service, "get_rag_service", lambda **_kwargs: rag)

    result = await clarification_service.live_decision(
        "일반 설명을 알려 주세요.", [], 0, BOT, policy_override=_policy()
    )

    assert result.status == "ask"
    assert result.questions[0].id == "existing"
    assert result.questions[0].policy is False
    assert result.diagnostics.policy_match_status == "unmatched"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("when_unknown", "expected"),
    [("ask", "ask"), ("handoff", "handoff"), ("allow_answer", "ready")],
)
async def test_uncertain_policy_follows_its_configured_handling(monkeypatch, when_unknown, expected):
    rag = _FakeRAG(
        {
            "decision": "answer",
            "policy_match": {"status": "uncertain", "rule_id": "refund"},
        }
    )
    monkeypatch.setattr(clarification_service, "get_rag_service", lambda **_kwargs: rag)

    result = await clarification_service.live_decision(
        "환불 관련 내용이 궁금해요.", [], 0, BOT, policy_override=_policy(when_unknown=when_unknown)
    )

    assert result.status == expected
    if expected == "ask":
        assert len(result.questions) == 2
    if expected == "handoff":
        assert result.handoff_message
