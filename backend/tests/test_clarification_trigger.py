"""재질문 트리거 — LLM 호출 0. 판정기 응답은 가짜로 주입한다.

기존 `test_clarification_service.py:37 _FakeRAG` 와 같은 방식이되, 트리거는
File Search 없는 `generate_structured` 를 쓰므로 그쪽 이름으로 받는다.
"""

import asyncio
from types import SimpleNamespace

import pytest

from app.schemas.clarification_policy import (
    ClarificationPolicy,
    ClarificationPolicyOption,
    ClarificationPolicyRule,
    ClarificationRequiredSlot,
)
from app.services import clarification_trigger
from app.services.wiki.store import SourceUnit

BOT = SimpleNamespace(
    id=11,
    llm_model="gemini-3.5-flash-lite",
    system_prompt="테스트 봇",
    clarification_policy=None,
)

UNITS = [
    SourceUnit(src_id="reg-16", doc="규정집v20", locator="제16조", text="축복식 참가 자격은 …"),
    SourceUnit(src_id="reg-47", doc="규정집v20", locator="제47조", text="은사 축복 신청은 …"),
]


class _FakeJudge:
    """`generate_structured` 만 흉내 낸다. 호출 인자를 남겨 검증에 쓴다."""

    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    async def generate_structured(self, **kwargs):
        self.calls.append(kwargs)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return kwargs["response_schema"](**response)


def _rule(rule_id: str, name: str, examples: list[str]) -> ClarificationPolicyRule:
    return ClarificationPolicyRule(
        id=rule_id,
        name=name,
        enabled=True,
        priority=0,
        request_examples=examples,
        why_ask="축복 종류에 따라 규정이 갈린다",
        required_slots=[
            ClarificationRequiredSlot(
                id="blessing_type",
                label="축복 종류",
                question="어떤 축복에 대한 질문인가요?",
                options=[
                    ClarificationPolicyOption(id="second_gen", label="2세 축복"),
                    ClarificationPolicyOption(id="matured", label="기성 축복"),
                ],
            )
        ],
    )


def _policy(*rules: ClarificationPolicyRule) -> ClarificationPolicy:
    return ClarificationPolicy(enabled=True, rules=list(rules))


# ---- B 판정 -------------------------------------------------------------


async def test_no_user_input_needed_lets_the_answer_through():
    judge = _FakeJudge([{"needs_user_input": False, "missing": [], "evidence": ["reg-16"]}])

    decision = await clarification_trigger.decide(
        question="축복식 참가 자격이 뭔가요?", units=UNITS, bot=BOT, rag_service=judge
    )

    assert decision.status == "answer"
    assert len(judge.calls) == 1
    # 판정기는 주입될 원문을 그대로 봐야 한다 — 답변이 보는 것과 갈리면 판정이 무의미하다.
    assert "reg-16" in judge.calls[0]["prompt"]
    assert "reg-47" in judge.calls[0]["prompt"]


async def test_evidence_outside_injected_units_fails_open():
    """주입되지 않은 src_id 를 근거로 대면 판정을 버리고 답변을 진행한다."""
    judge = _FakeJudge([{"needs_user_input": True, "missing": ["축복 종류"], "evidence": ["reg-999"]}])

    decision = await clarification_trigger.decide(
        question="기성축복이 무효인가요?",
        units=UNITS,
        bot=BOT,
        policy_override=_policy(_rule("blessing-type", "축복 종류", ["기성축복 무효", "2세 축복"])),
        rag_service=judge,
    )

    assert decision.status == "answer"
    assert "fail-open" in decision.reason


async def test_missing_empty_fails_open():
    judge = _FakeJudge([{"needs_user_input": True, "missing": [" "], "evidence": ["reg-16"]}])

    decision = await clarification_trigger.decide(
        question="축복식 참가 자격이 뭔가요?", units=UNITS, bot=BOT, rag_service=judge
    )

    assert decision.status == "answer"


@pytest.mark.parametrize("boom", [RuntimeError("[PLAN] 없음"), TimeoutError(), ValueError("공급자")])
async def test_judge_failure_never_silences_the_product(boom):
    judge = _FakeJudge([boom])

    decision = await clarification_trigger.decide(
        question="축복식 참가 자격이 뭔가요?", units=UNITS, bot=BOT, rag_service=judge
    )

    assert decision.status == "answer"


async def test_매달린_판정은_상한에서_끊고_답변을_진행한다(monkeypatch):
    """`TimeoutError` 를 받는 except 는 있었지만 **던지는 것이 없었다.**

    공급자 SDK 에 클라이언트 타임아웃이 없어 2026-08-10 측정에서 한 호출이 12분 46초간
    매달렸다. 되묻기는 사용자 응답 경로에 있으므로 그대로 켜면 그 시간이 사용자 대기가 된다.
    """
    started = asyncio.Event()

    class _HangingJudge:
        async def generate_structured(self, **kwargs):
            started.set()
            await asyncio.sleep(300)  # 영원히 — 상한이 없으면 이 테스트가 멈춘다
            raise AssertionError("여기에 도달하면 상한이 걸리지 않은 것이다")

    monkeypatch.setattr(clarification_trigger, "JUDGE_TIMEOUT_SEC", 0.05)
    loop = asyncio.get_running_loop()
    began = loop.time()
    decision = await clarification_trigger.decide(
        question="축복식 참가 자격이 뭔가요?", units=UNITS, bot=BOT, rag_service=_HangingJudge()
    )
    elapsed = loop.time() - began

    assert started.is_set()          # 모델을 실제로 불렀다
    assert decision.status == "answer"  # fail-open — 판정이 죽어도 답변은 나간다
    assert elapsed < 5               # 300초를 기다리지 않았다


def test_상한은_사용자가_기다릴_수_있는_값이다():
    """하네스 값(90초)을 그대로 프로덕션에 옮기지 않았다는 것을 실행으로 남긴다.

    측정 분포(판정 181회): 중앙 4.24s · p95 4.61s · 건강한 최대 5.6s.
    그 위는 61.8s · 149.8s · 766.2s 로 절벽이라 「느린 호출」이 아니라 멈춘 것이다.
    """
    assert 5.6 < clarification_trigger.JUDGE_TIMEOUT_SEC <= 15


async def test_empty_retrieval_answers_without_calling_the_model():
    judge = _FakeJudge([])

    decision = await clarification_trigger.decide(
        question="Blessing4u 등록은 어떻게 해요?", units=[], bot=BOT, rag_service=judge
    )

    assert decision.status == "answer"
    assert judge.calls == []


# ---- A 문구 조달 ---------------------------------------------------------


async def test_matched_rule_uses_admin_wording_verbatim():
    judge = _FakeJudge([{"needs_user_input": True, "missing": ["축복 종류"], "evidence": ["reg-47"]}])
    rule = _rule("blessing-type", "축복 종류", ["기성축복을 받았는데 무효인가요", "2세 축복 자격"])

    decision = await clarification_trigger.decide(
        question="오래전 2세가 1세와 사회결혼을 하고 기성축복을 받았는데 무효인가요?",
        units=UNITS,
        bot=BOT,
        policy_override=_policy(rule),
        rag_service=judge,
    )

    assert decision.status == "ask"
    assert decision.rule_id == "blessing-type"
    assert [q.question for q in decision.questions] == ["어떤 축복에 대한 질문인가요?"]
    assert decision.questions[0].options == ["2세 축복", "기성 축복"]
    assert decision.questions[0].policy is True
    assert decision.missing == ["축복 종류"]


async def test_no_matching_rule_hands_off_instead_of_inventing_wording():
    judge = _FakeJudge([{"needs_user_input": True, "missing": ["등록 절차"], "evidence": ["reg-16"]}])

    decision = await clarification_trigger.decide(
        question="Blessing4u 등록은 어떻게 해요?",
        units=UNITS,
        bot=BOT,
        policy_override=_policy(_rule("blessing-type", "축복 종류", ["기성축복 무효 여부"])),
        rag_service=judge,
    )

    assert decision.status == "handoff"
    assert decision.questions == []


async def test_disabled_policy_hands_off():
    judge = _FakeJudge([{"needs_user_input": True, "missing": ["축복 종류"], "evidence": ["reg-47"]}])
    policy = ClarificationPolicy(enabled=False, rules=[_rule("blessing-type", "축복 종류", ["기성축복"])])

    decision = await clarification_trigger.decide(
        question="기성축복 무효인가요?",
        units=UNITS,
        bot=BOT,
        policy_override=policy,
        rag_service=judge,
    )

    assert decision.status == "handoff"


# ---- 규칙 매칭 (LLM 무관) -------------------------------------------------


def test_ambiguous_match_picks_nothing():
    """1위가 2위를 확실히 못 이기면 고르지 않는다 — 엉뚱한 걸 되묻느니 넘긴다."""
    policy = _policy(
        _rule("a", "축복 종류", ["기성축복 자격이 궁금합니다"]),
        _rule("b", "축복 자격", ["기성축복 자격이 궁금합니다"]),
    )

    rule, _score = clarification_trigger.match_policy_rule("기성축복 자격이 궁금합니다", policy)

    assert rule is None


def test_no_lexical_overlap_matches_nothing():
    policy = _policy(_rule("a", "축복 종류", ["기성축복 자격"]))

    rule, score = clarification_trigger.match_policy_rule("보험금은 얼마예요", policy)

    assert rule is None
    assert score == 0.0


async def test_corpus_gap_without_a_dividing_clause_fails_open():
    """되물을 근거를 못 대면 그건 코퍼스 결손이지 질문 모호성이 아니다.

    v1 을 죽인 실패 모드다 — 「당해 연도 공문의 기준」처럼 질문자가 모르는 것을
    결손으로 뱉으면 되물어도 안 나온다. 가리킬 대목이 없으면 답변을 진행한다.
    """
    judge = _FakeJudge([{"needs_user_input": True, "missing": ["공문 기준"], "evidence": []}])

    decision = await clarification_trigger.decide(
        question="내년 축복식 참석 기준이 뭔가요?",
        units=UNITS,
        bot=BOT,
        policy_override=_policy(_rule("blessing-type", "축복 종류", ["축복식 참석 기준"])),
        rag_service=judge,
    )

    assert decision.status == "answer"


async def test_scalar_evidence_from_the_model_is_coerced_not_dropped():
    """모델이 항목 하나일 때 배열 대신 문자열을 준다. 45문항 중 31건이 이걸로 죽었다."""
    judge = _FakeJudge([{"needs_user_input": True, "missing": "축복 종류", "evidence": "reg-47"}])

    decision = await clarification_trigger.decide(
        question="기성축복을 받았는데 무효인가요?",
        units=UNITS,
        bot=BOT,
        policy_override=_policy(_rule("blessing-type", "축복 종류", ["기성축복을 받았는데 무효인가요"])),
        rag_service=judge,
    )

    assert decision.status == "ask"
    assert decision.missing == ["축복 종류"]
