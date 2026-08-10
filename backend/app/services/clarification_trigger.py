"""맥락 부족 시 되물을지 판정한다 — 근거를 읽은 **뒤**에.

**아직 배선되어 있지 않다. 호출자 0개다.** 붙이는 자리는
`docs/architecture/handoff-clarification-trigger-2026-08-11.md` §삽입점 참조.

두 갈래로 나뉜다.

    B  되물을지  검색이 끝나고 주입될 원문을 읽은 뒤 판정한다(`judge_answerability`).
    A  무엇을    관리자가 쓴 정책 슬롯 문구를 그대로 꺼낸다(`match_policy_rule` + `_policy_questions`).
                 LLM 은 문구를 만들지 않는다.

**되물을 조건은 「답을 모른다」가 아니라 「질문자만 아는 것이 빠졌다」다.** 이 구분이
전부다. 원문에 답이 없으면 되물어도 안 나온다 — 그건 「확인되지 않는다」로 답할 일이다.
처음엔 「원문이 이 사안을 결정하는가」로 물었고 음성 33건 중 24건에서 발동했다(73%).
뱉은 결손이 「당해 연도 공문의 기준」처럼 **질문자가 모르는 것**이었기 때문이다.

**측정 상태 — 값어치는 아직 증명되지 않았다.** 45문항 실측에서 이 판정기는 진짜로 덜 적힌
질문 6건(33·34·36·39·45·18)을 짚어냈지만, 그 6건은 기존 라벨(무주장·지어냄)에서 전부
「음성」이다. 그 라벨은 **코퍼스 커버리지**를 재고 재질문은 **질문 모호성**을 고치기 때문이다.
재질문용 라벨을 새로 만들기 전에는 이 모듈의 성능을 말할 수 없다 —
`docs/architecture/handoff-clarification-trigger-2026-08-11.md` §6.

**왜 검색 점수를 안 쓰나.** 45문항 실측에서 어느 검색 점수도 「되물었어야 할 질문」을
가르지 못했다. 22번은 코퍼스 최고 BM25(62.27)인데 아무 주장도 못 했고 44번은 최저(6.29)인데
역시 못 했다. BM25 는 「코퍼스가 이 단어를 다루는가」를 재지 「이 사안을 결정하는 조문이
있는가」를 재지 않는다. 게다가 RRF 점수는 `1/(60+rank)` 의 합이라 관측 범위가 1.22배뿐이고
코퍼스를 바꿔도 넓어지지 않는다. `Retrieved.top_score` 를 되살리지 마라.

**왜 PR #51 과 다른가.** #51 은 검색 **전** 원질문만 보고 경로를 골랐고 60문항 중 30건이
어긋나 클로즈됐다. 여기서는 검색 **후** 실제 주입 원문을 보고 이진 판정만 하며, 그 판정이
댄 근거가 정말 주입 목록 안에 있는지 대조한다. 대조에 실패하면 **답변을 진행한다**(fail-open)
— 판정기가 고장 나서 제품이 벙어리가 되는 쪽이 더 나쁘다.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Literal

from pydantic import BaseModel, ValidationError, field_validator

from app.schemas.clarification import ClarificationQuestion
from app.schemas.clarification_policy import ClarificationPolicy, ClarificationPolicyRule
from app.services.clarification_service import (
    CLARIFICATION_MODEL,
    _active_policy,
    _enabled_rules,
    _policy_questions,
)
from app.services.rag.factory import get_rag_service
from app.services.wiki.retrieval import BM25
from app.services.wiki.store import SourceUnit

logger = logging.getLogger(__name__)

# 규칙 매칭은 「질문 대 관리자가 쓴 예시질문」이라는 같은 어휘 공간의 비교다.
# 근거 충분성의 대리 지표가 아니므로 임계값을 두는 것이 정당하다. 절대 크기 대신
# 1위 규칙이 2위를 몇 배로 이겼는지만 본다 — BM25 원점수는 질문 길이에 딸려 움직인다.
MIN_RULE_DOMINANCE = 1.5

# 판정 1회 상한. **이 판정은 답변을 막고 서 있다** — shadow 판정과 달리 응답을 보내기
# 전에 부른다(`chat_service._clarification_for`). 상한이 없으면 매달린 시간을 사용자가
# 그대로 기다린다. 2026-08-10 측정에서 실제로 한 문항이 12분 매달려 진행이 멈췄다
# (네트워크는 정상이었다). Gemini SDK 에 클라이언트 타임아웃이 없다.
#
# 20초는 같은 워크로드 실측(45문항 · n=152)의 최대 4.19초에 4.8배 여유를 둔 값이다:
#     중앙값 1,474ms · p90 1,773ms · p95 1,929ms · 최대 4,189ms
# 더 길게 잡을 이유가 없다 — 타임아웃은 fail-open 이라 평소 답변으로 돌아갈 뿐이다.
# `clarification_service.CLARIFICATION_TIMEOUT_SEC`(150초)를 쓰지 않는 이유가 이것이다.
# 그건 File Search 계획 호출용이고 사용자를 막지 않는다.
JUDGE_TIMEOUT_SEC = 20.0

_JUDGE_SYSTEM_PROMPT = """너는 「이 질문은 되물어야 하는가」만 판정한다.

되물어야 하는 경우는 **하나뿐이다.**
아래 [원문]이 경우를 나눠 두었는데, 질문에 그 경우가 안 적혀 있을 때다.
예: 원문이 "2세 축복은 …, 기성 축복은 …" 으로 갈라 놓았는데 질문자가 어느 쪽인지 안 밝혔다.
이때만 needs_user_input=true.

**되물으면 안 되는 경우** (전부 false):
- 원문에 답이 아예 없다 → 되물어도 안 나온다. 「확인되지 않는다」로 답하면 될 일이다.
- 빠진 것이 규정·공문·기준·조항처럼 **우리가 찾아야 하는 것**이다 → 질문자는 모른다.
- 신학·가치·심경에 대한 질문이라 애초에 규정으로 갈리지 않는다.
- 원문만으로 답할 수 있다.

missing 에는 **질문자가 즉시 대답할 수 있는 것만** 적는다. 짧은 명사구, 최대 3개.
  좋음: "축복 종류", "본인 세대(1세/2세)", "3일행사 진행 단계"
  나쁨: "당해 연도 공문의 기준", "무효화 여부 규정", "재시행 기준"  ← 질문자가 모른다

evidence 에는 **경우를 나누고 있는 그 대목**의 src_id 를 적는다. needs_user_input=true 인데
가리킬 대목이 없으면 그건 되물을 일이 아니다. 원문에 없는 id 를 지어내지 마라.

답을 만들지 마라. 판정만 한다."""


class AnswerabilityVerdict(BaseModel):
    """B 판정의 계약. 모델이 이 JSON 만 낸다.

    `needs_user_input` 은 「답할 수 있는가」가 아니라 **「질문자만 아는 것이 빠졌는가」**다.
    이 구분이 v1 을 죽였다 — v1 은 「원문이 이 사안을 결정하는가」를 물었고, 45문항 중
    33개 음성에서 24개가 발동했다(73%). 뱉은 missing 이 「당해 연도 공문의 기준」처럼
    **질문자가 모르는 것**이었다. 되물어도 안 나오는 것을 되물으면 안 된다.
    """

    needs_user_input: bool
    missing: list[str] = []
    evidence: list[str] = []

    @field_validator("missing", "evidence", mode="before")
    @classmethod
    def _as_list(cls, value):
        """모델이 항목 하나일 때 배열 대신 문자열을 준다 — `evidence: "reg-90"`.

        45문항 중 31건이 이걸로 죽어 전부 fail-open 됐다. 판정이 아니라 모양 문제였다.
        `_RawClarificationPlan` → `_normalise_plan`(clarification_service.py) 과 같은 규약 —
        모델 출력은 너그럽게 받고 계약은 여기서 세운다.
        """
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value.strip() else []
        return value


@dataclass
class TriggerDecision:
    """되물을지·무엇을 되물을지. `reason` 은 측정과 디버깅용이다."""

    status: Literal["answer", "ask", "handoff"]
    reason: str
    questions: list[ClarificationQuestion] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    rule_id: str | None = None


def _units_block(units: list[SourceUnit], max_chars: int) -> str:
    """판정기가 보는 원문. 답변 생성이 보는 것과 **같은 목록이어야 한다.**"""
    return "\n\n".join(f"[{u.src_id}] {u.doc} {u.locator}\n{u.text[:max_chars]}" for u in units)


def _validate_verdict(verdict: AnswerabilityVerdict, units: list[SourceUnit]) -> str | None:
    """검증 실패 사유를 돌려준다. None 이면 통과.

    `evidence_matches_current_retrieval`(clarification_service.py) 와 같은 발상 —
    판정이 댄 근거가 이번 검색 결과 안에 실제로 있어야 한다.
    """
    known = {u.src_id for u in units}
    unknown = [src_id for src_id in verdict.evidence if src_id not in known]
    if unknown:
        return f"주입되지 않은 근거 id: {', '.join(unknown[:3])}"
    if not verdict.needs_user_input:
        return None
    if not [m for m in verdict.missing if m.strip()]:
        return "needs_user_input=true 인데 missing 이 비었다"
    # 되물을 근거는 「원문이 경우를 나눈 대목」이다. 가리킬 대목이 없으면 그건 코퍼스
    # 결손이지 질문 모호성이 아니다 — 되물어도 안 나온다.
    if not verdict.evidence:
        return "needs_user_input=true 인데 경우를 나눈 대목을 못 댄다"
    return None


async def judge_answerability(
    *,
    question: str,
    units: list[SourceUnit],
    bot: SimpleNamespace,
    rag_service=None,
    max_unit_chars: int = 2_000,
    timeout: float = JUDGE_TIMEOUT_SEC,
) -> AnswerabilityVerdict | None:
    """주입될 원문만 보고 답할 수 있는지 판정한다. 실패하면 None(=답변 진행)."""
    if not units:
        # 1단이 빈손이면 되물을 「경우를 나눈 대목」도 없다. 답변 경로가 스스로
        # 「확인되지 않는다」를 내게 둔다 — 되물어도 안 나오기 때문이다. 모델도 안 부른다.
        return AnswerabilityVerdict(needs_user_input=False, missing=[], evidence=[])

    model_name = getattr(bot, "llm_model", None) or CLARIFICATION_MODEL
    service = rag_service or get_rag_service(provider=model_name)
    prompt = f"[질문]\n{question}\n\n[원문]\n{_units_block(units, max_unit_chars)}"
    try:
        # `asyncio.TimeoutError` 는 `TimeoutError` 다(3.11+). 아래 except 가 그대로 받아
        # fail-open 한다 — 상한을 두는 것이 판정을 더 엄격하게 만들지 않는다.
        verdict = await asyncio.wait_for(
            service.generate_structured(
                prompt=prompt,
                system_prompt=_JUDGE_SYSTEM_PROMPT,
                model_name=model_name,
                response_schema=AnswerabilityVerdict,
            ),
            timeout=timeout,
        )
    except TimeoutError:
        # `asyncio.TimeoutError` 는 메시지가 비어 있어, 위 줄과 같이 찍으면 로그에
        # 사유가 안 남는다. 매달림을 진단하려고 둔 상한이므로 별도로 적는다.
        logger.warning("재질문 판정 %.0f초 초과 — 답변 진행", timeout)
        return None
    except (ValidationError, RuntimeError) as exc:
        logger.warning("재질문 판정 실패 — 답변 진행: %s", exc)
        return None
    except Exception as exc:  # 공급자 예외 전반. 판정 실패가 답변을 막으면 안 된다.
        logger.warning("재질문 판정 공급자 오류 — 답변 진행: %s", exc)
        return None

    invalid = _validate_verdict(verdict, units)
    if invalid:
        logger.warning("재질문 판정 검증 실패 — 답변 진행: %s", invalid)
        return None
    return verdict


def match_policy_rule(
    question: str,
    policy: ClarificationPolicy,
    *,
    min_dominance: float = MIN_RULE_DOMINANCE,
    min_score: float = 0.0,
) -> tuple[ClarificationPolicyRule | None, float]:
    """질문에 맞는 정책 규칙을 어휘로 고른다. LLM 을 쓰지 않는다.

    예시질문 하나하나를 문서로 색인하고, 규칙 점수 = 그 규칙 예시들의 최고점으로 본다.
    1위가 2위를 `min_dominance` 배 이상 이겨야 채택한다 — 애매하면 안 고르는 쪽이 낫다.

    `min_score` 기본값은 0 이다. **절대 하한을 임의로 박지 않는다** — BM25 원점수는
    질문이 길수록 커져서(45문항에서 4.4~58.7) 길이 편향이 있고, 하한을 정하려면 스윕한
    근거가 있어야 한다. 하네스가 이 인자로 쓸어 본다.
    """
    rules = _enabled_rules(policy)
    docs: list[tuple[str, str]] = []
    for index, rule in enumerate(rules):
        for example_index, example in enumerate(rule.request_examples):
            if example.strip():
                docs.append((f"{index}:{example_index}", example))
    if not docs:
        return None, 0.0

    best: dict[int, float] = {}
    for doc_id, score in BM25(docs).search(question, depth=len(docs)):
        if score <= 0:
            continue
        index = int(doc_id.split(":")[0])
        best[index] = max(best.get(index, 0.0), score)
    if not best:
        return None, 0.0

    ranked = sorted(best.items(), key=lambda kv: kv[1], reverse=True)
    top_index, top_score = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
    if top_score < min_score:
        return None, top_score
    if runner_up > 0 and top_score < runner_up * min_dominance:
        return None, top_score
    return rules[top_index], top_score


async def decide(
    *,
    question: str,
    units: list[SourceUnit],
    bot: SimpleNamespace,
    policy_override: ClarificationPolicy | None = None,
    rag_service=None,
    min_dominance: float = MIN_RULE_DOMINANCE,
    min_score: float = 0.0,
) -> TriggerDecision:
    """B 로 판정하고, 되물어야 하면 A 로 문구를 꺼낸다."""
    verdict = await judge_answerability(
        question=question, units=units, bot=bot, rag_service=rag_service
    )
    if verdict is None:
        return TriggerDecision(status="answer", reason="판정 실패 — fail-open")
    if not verdict.needs_user_input:
        return TriggerDecision(status="answer", reason="되물을 것 없음")

    missing = [m.strip() for m in verdict.missing if m.strip()]
    rule, score = match_policy_rule(
        question,
        _active_policy(bot, policy_override),
        min_dominance=min_dominance,
        min_score=min_score,
    )
    if rule is None:
        # 되물을 항목을 관리자가 정해 두지 않았다. 문구를 지어내느니 사람에게 넘긴다.
        return TriggerDecision(status="handoff", reason="매칭 규칙 없음", missing=missing)

    return TriggerDecision(
        status="ask",
        reason=f"근거 부족 · 규칙 {rule.id} (BM25 {score:.2f})",
        questions=_policy_questions(rule.required_slots),
        missing=missing,
        rule_id=rule.id,
    )
