from types import SimpleNamespace

import pytest

from app.schemas.clarification import ClarificationAnswer
from app.schemas.rag import RAGCitation
from app.services import clarification_service


BOT = SimpleNamespace(
    id=11,
    llm_model="gemini-3.5-flash-lite",
    system_prompt="테스트 봇",
)


def _ask_plan(**overrides):
    plan = {
        "decision": "ask",
        "questions": [
            {
                "id": "goal",
                "title": "어떤 목적이신가요?",
                "selection_mode": "single",
                "options": [
                    {"label": "예약", "value": "reservation"},
                    {"label": "문의", "value": "inquiry"},
                ],
                "evidence": ["근거 문서"],
            }
        ],
    }
    plan.update(overrides)
    return plan


class _FakeRAG:
    def __init__(self, responses, citations=None):
        self.responses = iter(responses)
        self.citations = citations or [RAGCitation(title="근거 문서", content="문서 근거")]
        self.calls = []

    async def generate_structured_with_rag(self, **kwargs):
        self.calls.append(kwargs)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return kwargs["response_schema"](**response), self.citations


def test_fixture_uses_one_card_then_returns_deterministic_summary():
    message = "우리 서비스에 예약 기능을 넣고 싶어요."
    first = clarification_service.fixture_decision(message, [], 0)

    assert first.status == "ask"
    assert len(first.questions) == 3
    assert first.questions[0].selection_mode == "multiple"

    answers = [
        ClarificationAnswer(
            question_id="reservation_target",
            question="어떤 예약 기능이 필요한가요?",
            values=["클래스", "공간 대여"],
        )
    ]
    ready = clarification_service.fixture_decision(message, answers, 1)

    assert ready.status == "ready"
    assert "클래스, 공간 대여" in (ready.summary or "")


@pytest.mark.asyncio
async def test_live_decision_normalises_title_and_object_options(monkeypatch):
    rag = _FakeRAG([_ask_plan()])
    monkeypatch.setattr(clarification_service, "get_rag_service", lambda **_kwargs: rag)

    result = await clarification_service.live_decision("기능을 추가하고 싶어요.", [], 0, BOT)

    assert result.status == "ask"
    assert result.source == "live"
    assert result.questions[0].question == "어떤 목적이신가요?"
    assert result.questions[0].options == ["예약", "문의"]
    assert result.questions[0].allow_custom is True
    assert result.citations[0].title == "근거 문서"
    assert len(rag.calls) == 1
    assert rag.calls[0]["model_name"] == "gemini-3.5-flash-lite"
    assert "evidence 배열" in rag.calls[0]["system_prompt"]
    assert "개인의 자격·행정 절차·금액·예외·사후 조치" in rag.calls[0]["system_prompt"]


@pytest.mark.asyncio
async def test_live_decision_normalises_string_options(monkeypatch):
    plan = _ask_plan()
    plan["questions"][0]["options"] = ["첫 번째", "두 번째"]
    rag = _FakeRAG([plan])
    monkeypatch.setattr(clarification_service, "get_rag_service", lambda **_kwargs: rag)

    result = await clarification_service.live_decision("기능을 추가하고 싶어요.", [], 0, BOT)

    assert result.status == "ask"
    assert result.questions[0].options == ["첫 번째", "두 번째"]


@pytest.mark.asyncio
async def test_live_decision_accepts_evidence_named_inside_current_citation(monkeypatch):
    plan = _ask_plan()
    plan["questions"][0]["evidence"] = ["2022 축복행정 국제 규정집"]
    rag = _FakeRAG(
        [plan],
        citations=[
            RAGCitation(
                title="신한국 축복가정행정 규정집 개정초안 2026.pdf",
                content="근거: 2022 축복행정 국제 규정집 07. 축복에 관한 지도",
            )
        ],
    )
    monkeypatch.setattr(clarification_service, "get_rag_service", lambda **_kwargs: rag)

    result = await clarification_service.live_decision("상황에 맞는 안내가 필요해요.", [], 0, BOT)

    assert result.status == "ask"
    assert len(rag.calls) == 1


@pytest.mark.asyncio
async def test_live_decision_maps_legacy_ready_to_answer_without_reusing_model(monkeypatch):
    rag = _FakeRAG([{"status": "ready"}])
    monkeypatch.setattr(clarification_service, "get_rag_service", lambda **_kwargs: rag)

    result = await clarification_service.live_decision("가정출발이 뭐야?", [], 0, BOT)

    assert result.status == "ready"
    assert result.source == "live"
    assert result.fallback is False
    assert "가정출발이 뭐야?" in (result.summary or "")
    assert len(rag.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_plan",
    [
        {"decision": "ask", "questions": "not-a-list"},
        _ask_plan(questions=[]),
        _ask_plan(questions=[_ask_plan()["questions"][0]] * 4),
        _ask_plan(
            questions=[
                _ask_plan()["questions"][0],
                {**_ask_plan()["questions"][0], "title": "중복 ID"},
            ]
        ),
        _ask_plan(
            questions=[{**_ask_plan()["questions"][0], "evidence": ["다른 문서"]}]
        ),
    ],
)
async def test_live_decision_corrects_invalid_plan_once(monkeypatch, invalid_plan):
    rag = _FakeRAG([invalid_plan, _ask_plan()])
    monkeypatch.setattr(clarification_service, "get_rag_service", lambda **_kwargs: rag)

    result = await clarification_service.live_decision("상황에 맞는 안내가 필요해요.", [], 0, BOT)

    assert result.status == "ask"
    assert len(rag.calls) == 2
    assert "[형식 교정]" in rag.calls[1]["prompt"]


@pytest.mark.asyncio
async def test_live_decision_uses_summary_when_the_one_correction_is_also_invalid(monkeypatch):
    invalid = _ask_plan(questions=[])
    rag = _FakeRAG([invalid, invalid])
    monkeypatch.setattr(clarification_service, "get_rag_service", lambda **_kwargs: rag)

    result = await clarification_service.live_decision("기능을 추가하고 싶어요.", [], 0, BOT)

    assert result.status == "ready"
    assert result.source == "fallback"
    assert result.fallback is True
    assert len(rag.calls) == 2


@pytest.mark.asyncio
async def test_live_decision_does_not_retry_provider_errors(monkeypatch):
    rag = _FakeRAG([RuntimeError("provider unavailable")])
    monkeypatch.setattr(clarification_service, "get_rag_service", lambda **_kwargs: rag)

    result = await clarification_service.live_decision("기능을 추가하고 싶어요.", [], 0, BOT)

    assert result.status == "ready"
    assert result.source == "fallback"
    assert result.fallback is True
    assert len(rag.calls) == 1


@pytest.mark.asyncio
async def test_live_decision_does_not_call_rag_again_after_answers(monkeypatch):
    class NoPlanningRAG:
        async def generate_structured_with_rag(self, **_kwargs):
            raise AssertionError("답변 후에는 질문 계획을 다시 만들면 안 됩니다.")

    monkeypatch.setattr(
        clarification_service, "get_rag_service", lambda **_kwargs: NoPlanningRAG()
    )

    result = await clarification_service.live_decision(
        "기능을 추가하고 싶어요.",
        [ClarificationAnswer(question_id="goal", question="목적", values=["예약"])],
        1,
        BOT,
    )

    assert result.status == "ready"
    assert "예약" in (result.summary or "")
