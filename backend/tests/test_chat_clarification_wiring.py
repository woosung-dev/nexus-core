"""되묻기 배선 — `_clarification_for` 의 계약과 strict 게이트와의 순서.

`decide()` 는 가짜로 갈아 끼운다. 여기서 지키는 것은 「언제 판정기를 부르는가」와
「부른 결과를 어떻게 응답으로 바꾸는가」다. 판정 자체는
`test_clarification_trigger.py` 가 본다.
"""

from types import SimpleNamespace

import pytest

from app.schemas.clarification import ClarificationQuestion
from app.schemas.rag import RAGResponse
from app.services import chat_service
from app.services.clarification_trigger import TriggerDecision
from app.services.strict_mode import has_direct_citation
from app.services.unanswered import RetrievalTrace
from app.services.wiki.store import SourceUnit

UNITS = [
    SourceUnit(src_id="reg-43", doc="규정집v20", locator="제43조", text="12일 가정출발의식은 …"),
]

ASK = TriggerDecision(
    status="ask",
    reason="근거 부족 · 규칙 family-start-12day (BM25 27.13)",
    questions=[ClarificationQuestion(id="blessing_type", question="어떤 축복에 대한 질문인가요?")],
    missing=["축복 유형"],
    rule_id="family-start-12day",
)


def _bot(**kwargs):
    fields = {
        "id": 29,
        "llm_model": "gemini-3.5-flash-lite",
        "clarify_enabled": True,
        "evidence_policy_mode": "legacy",
    }
    return SimpleNamespace(**(fields | kwargs))


def _trace():
    trace = RetrievalTrace()
    trace.units = list(UNITS)
    return trace


@pytest.fixture
def spy_decide(monkeypatch):
    """`decide` 를 갈아 끼우고 호출 여부를 기록한다."""
    calls = []

    def install(result):
        async def fake(**kwargs):
            calls.append(kwargs)
            if isinstance(result, Exception):
                raise result
            return result

        monkeypatch.setattr("app.services.clarification_trigger.decide", fake)
        return calls

    return install


@pytest.mark.asyncio
async def test_disabled_bot_never_calls_the_judge(spy_decide):
    """`clarify_enabled` 가 거짓이면 **호출조차 하지 않는다** — Gemini 쿼터가 걸려 있다."""
    calls = spy_decide(ASK)
    result = await chat_service._clarification_for(_bot(clarify_enabled=False), "질문", _trace(), 0)
    assert result is None
    assert calls == []


@pytest.mark.asyncio
async def test_second_round_never_calls_the_judge(spy_decide):
    """되묻기는 한 번까지다. 카드에 답해서 온 요청은 판정을 건너뛴다."""
    calls = spy_decide(ASK)
    result = await chat_service._clarification_for(_bot(), "질문", _trace(), 1)
    assert result is None
    assert calls == []


@pytest.mark.asyncio
async def test_answer_verdict_leaves_the_response_alone(spy_decide):
    spy_decide(TriggerDecision(status="answer", reason="되물을 것 없음"))
    assert await chat_service._clarification_for(_bot(), "질문", _trace(), 0) is None


@pytest.mark.asyncio
async def test_ask_carries_admin_wording_and_the_min_score(spy_decide):
    calls = spy_decide(ASK)
    result = await chat_service._clarification_for(_bot(), "질문", _trace(), 0)

    assert result is not None
    assert result.status == "ask"
    assert result.rule_id == "family-start-12day"
    assert [q.question for q in result.questions] == ["어떤 축복에 대한 질문인가요?"]
    assert result.round == 0
    # 스윕으로 정한 하한이 실제로 넘어가는지 — 기본값 0 으로 새면 #39 가 잘못 걸린다.
    assert calls[0]["min_score"] == chat_service.CLARIFICATION_MIN_SCORE
    assert calls[0]["units"] == UNITS


@pytest.mark.asyncio
async def test_judge_failure_never_silences_the_product(spy_decide):
    """판정이 터져도 답변은 나간다 — `decide` 안팎 모두 fail-open 이다."""
    spy_decide(RuntimeError("공급자 폭발"))
    assert await chat_service._clarification_for(_bot(), "질문", _trace(), 0) is None


def test_clarification_must_come_after_the_strict_gate():
    """되묻기 응답을 strict 게이트 **앞**에 놓으면 안 되는 이유를 실행으로 남긴다.

    되묻기 본문은 인용 0건이고 거절문도 아니다. 그래서 `_strict_blocks` 가 참이 되어
    `STRICT_EVIDENCE_MESSAGE` 로 통째로 치환된다 — 봇이 되물은 질문이 삼켜진다.
    지금은 라이브 11봇이 전부 legacy 라 안 터지지만 strict 를 켜는 순간 터진다.
    """
    asked = RAGResponse(answer=chat_service.CLARIFICATION_ASK_MESSAGE, citations=[], followups=[])

    assert not has_direct_citation(asked.citations)
    assert chat_service._strict_blocks("lexical", _trace(), asked) is True
    assert chat_service._strict_blocks("file_search", _trace(), asked) is True
