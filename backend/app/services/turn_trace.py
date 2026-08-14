"""한 턴이 어느 단계를 어떻게 지나갔는지 남긴다.

지금까지 우리가 잰 것은 답변 생성 하나였다(`exports/regression/_run.py` 는 `chat_service`
를 통째로 우회한다). 그런데 사용자가 실제로 받는 문장은 여덟 단계의 합작이다 — FAQ 가
가로챌 수도 있고, strict 게이트가 막을 수도 있고, 빈 답변이 고정 문구로 바뀔 수도 있다.
**「유보율」은 4번과 6번이 만드는 값이지 생성기의 속성이 아니다.** 그걸 데이터로 남긴다.

## 규칙 셋 — 어기면 느려진다

1. **원문 텍스트를 넣지 마라.** 참조만 남긴다(`src_id` · `locator` · 점수). 주입 원문은
   건당 3,000자까지 가고 그게 매 턴 행에 박히면 관리자 화면이 먼저 죽는다.
2. **여기서 DB 를 만지지 마라.** 어시스턴트 메시지 INSERT 에 컬럼 하나로 얹는다.
   왕복이 늘지 않아야 추가 비용이 1~5ms 에 머문다(생성이 1,600~7,000ms 다).
3. **trace 를 만들려고 LLM 을 부르지 마라.** 되묻기 판정기가 매 턴 +4.2초를 먹다가
   #68 에서 통째로 제거됐다. 여기 들어가는 값은 전부 **이미 결정된 것을 받아 적는 것**이다.

## 왜 설정 스냅샷을 같이 박나

같은 질문에 다른 답이 나왔을 때 **무엇이 달랐는지 되짚을 방법이 지금 없다.** 로컬 봇 11 과
라이브 봇 11 이 서로 다른 봇이고, 태그를 재사용하면 옛 결과가 섞이고, 회차가 6일 간격으로
갈라져도 파일명만 봐서는 모른다 — 이 셋 다 실제로 물린 적이 있다.
`prompt_sha8` 하나만 있어도 「이 답변이 어느 프롬프트에서 나왔나」가 끝난다.

## 아직 못 남기는 것

**예외로 죽은 턴.** trace 는 어시스턴트 메시지 행에 얹히는데, 생성이 터지면 그 행이 없다.
429·타임아웃이 여전히 로그 한 줄로만 남는다는 뜻이다. 별도 테이블을 파야 풀리는 문제라
여기서는 손대지 않았다.

**스트리밍 경로.** `_generate_*_stream` 세 갈래는 배선하지 않았다. 지금 스트리밍은
`retrieval_mode == "file_search"` 일 때만 켜지고(`chat_service.py` 의 `stream_ok`),
주력 봇 11 은 `lexical` 이라 타지 않는다. file_search 봇을 재려면 그때 배선해야 한다.

⚠ 같은 구멍에 **위기 안내 블록도 빠져 있다**(`CRISIS` 단계). 스트리밍을 켜는 순간
자살 신호에 안전 안내가 안 나간다. file_search 봇을 내보낼 때 trace 배선과 **반드시
같이** 해야 한다 — 이쪽은 관측 누락이지만 저쪽은 안전 결함이다.
"""

import hashlib
import os
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Any

# 단계 이름. 순서가 곧 파이프라인 순서다.
FAQ = "faq"
OPS_FACTS = "ops_facts"
RETRIEVAL = "retrieval"
STRICT = "strict"
STRIP = "strip"
UNANSWERED = "unanswered"
TERM = "term"
# 위기 안내. **걸린 턴에서만 낸다** — 안 걸린 턴은 단계 자체가 없다.
# 그래서 위 여덟 단계의 순서 계약(`tests/test_turn_trace.py`)이 그대로 유지된다.
CRISIS = "crisis"
RECORD = "record"

# 한 턴의 trace 가 이보다 커지면 잘라 낸다. 관리자 화면 한 행이 감당할 상한이고,
# 넘는다는 것은 규칙 1(원문 금지)을 어겼다는 뜻이라 신호이기도 하다.
MAX_STAGES = 24
MAX_LIST = 12


def prompt_sha8(text: str) -> str:
    """프롬프트 지문. NFKC 로 맞춘 뒤 sha256 앞 8자."""
    norm = unicodedata.normalize("NFKC", text or "")
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:8]


def _clip(v: Any) -> Any:
    """리스트는 길이를 자르고 남은 수를 알린다. 문자열은 길이만 줄인다."""
    if isinstance(v, list) and len(v) > MAX_LIST:
        return v[:MAX_LIST] + [f"…+{len(v) - MAX_LIST}"]
    if isinstance(v, str) and len(v) > 200:
        return v[:200] + "…"
    return v


@dataclass
class TurnTrace:
    """단계별 관찰 기록. `chat_service` 가 들고 다니며 채운다.

    사용자 응답 스키마(`ChatCompletionResponse`)에 **절대 넣지 않는다** — 기계 id 가 화면에
    새어 나간 전례가 있다(#63). `tests/test_turn_trace.py` 가 그 부재를 검증한다.
    """

    config: dict[str, Any] = field(default_factory=dict)
    stages: list[dict[str, Any]] = field(default_factory=list)
    _t0: float = field(default_factory=time.perf_counter)
    _last: float = field(default_factory=time.perf_counter)

    def snapshot(self, bot, system_prompt: str, request) -> None:
        """무엇으로 답했는지. 봇 설정이 런타임에 갈리므로 저장값이 아니라 **실효값**을 박는다."""
        self.config = {
            "bot_id": bot.id,
            "bot_name": bot.name,
            "model": bot.llm_model,
            "retrieval_mode": getattr(bot, "retrieval_mode", None),
            "evidence_policy_mode": bot.evidence_policy_mode,
            "use_rag": bool(bot.use_rag and getattr(request, "use_rag", True)),
            "history_window": bot.history_window or 0,
            "prompt_sha8": prompt_sha8(system_prompt),
            "prompt_len": len(system_prompt or ""),
            "stream": bool(getattr(request, "stream", False)),
        }
        rev = os.getenv("GIT_SHA", "")
        if rev:
            self.config["code_rev"] = rev[:8]

    def stage(self, name: str, decision: str, **facts: Any) -> None:
        """단계 하나를 닫는다. `decision` 은 **다음 단계로 무엇을 들고 갔나**를 한 낱말로."""
        if len(self.stages) >= MAX_STAGES:
            return
        now = time.perf_counter()
        row: dict[str, Any] = {
            "stage": name,
            "decision": decision,
            "ms": round((now - self._last) * 1000, 1),
        }
        for k, v in facts.items():
            if v is not None:
                row[k] = _clip(v)
        self.stages.append(row)
        self._last = now

    def to_json(self) -> dict[str, Any]:
        return {
            "v": 1,
            "total_ms": round((time.perf_counter() - self._t0) * 1000, 1),
            "config": self.config,
            "stages": self.stages,
        }


def unit_refs(units: list) -> list[str]:
    """주입된 원문을 **참조로만** 남긴다. 규칙 1 — 본문은 넣지 않는다."""
    out = []
    for u in units or []:
        loc = getattr(u, "locator", None)
        out.append(f"{u.src_id}:{loc}" if loc else str(u.src_id))
    return out
