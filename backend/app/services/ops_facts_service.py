"""
운영 사실(ops_facts) 런타임 서비스.

세 가지를 한다.
  ① 승인된 사실을 시스템 프롬프트 뒤에 블록으로 붙인다 (deprecated·forbidden·contact·crisis)
  ①-b 위기(kind='crisis')는 **답변 끝에 고정 안내문을 코드가 덧붙인다** — 프롬프트에는
      「방해하지 마라」는 지시만 간다. 이유는 `_CRISIS_DIRECTIVE` 주석에
  ② 표기 통일(kind='term')은 프롬프트가 아니라 **응답 후처리로 치환**한다

②를 코드로 하는 이유는 실측이다 — `exports/prompt4_2026-08-05/FINDINGS.md` §2-4.
프롬프트에 "하늘부모님으로 표기한다"고 명시한 팔(03)이 오히려 위반 16건으로 가장 많았다.
그래서 term 은 프롬프트에 **넣지 않는다.** 넣어 봐야 안 지켜지고, 금지어를 프롬프트에
노출해 오히려 유도할 소지만 있다.

용어집 서비스(feat/glossary-clarify-stack `glossary_service.py`)와 같은 규약을 따른다 —
60초 봇별 캐시, NFKC+casefold 정규화, 예외는 빈 결과로 fail-closed.
"""

import logging
import time
import unicodedata

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import crud_ops_facts
from app.models.bot import Bot
from app.models.ops_facts import OpsFact
from app.schemas.rag import RAGCitation

logger = logging.getLogger(__name__)

# 프롬프트에 싣는 최대 줄 수 — 사실이 늘어도 프롬프트가 무한정 자라지 않게 한다.
OPS_FACT_MAX_LINES = 30
OPS_FACT_LINE_CHAR_CAP = 300
_CACHE_TTL = 60.0

# 봇별 캐시. 전역 사실을 포함한 결과를 각 봇 키에 저장한다.
_OPS_FACT_CACHE: dict[int, tuple[list[OpsFact], float]] = {}

# 프롬프트 블록에 싣는 종류와 줄 문안. 'term' 은 여기 없다(후처리 전용).
_PROMPT_KINDS = ("deprecated", "forbidden", "contact", "crisis")

# 치환 보호용 토큰 — 본문에 나올 수 없는 문자를 쓴다.
_GUARD = "\x00OPSFACT\x00"


def _normalize(s: str) -> str:
    return unicodedata.normalize("NFKC", s).casefold()


async def _load_facts(session: AsyncSession, bot_id: int) -> list[OpsFact]:
    now = time.monotonic()
    cached = _OPS_FACT_CACHE.get(bot_id)
    if cached and now - cached[1] < _CACHE_TTL:
        return cached[0]
    rows = list(await crud_ops_facts.get_approved_for_bot(session, bot_id))
    _OPS_FACT_CACHE[bot_id] = (rows, now)
    return rows


async def load_runtime_facts(
    session: AsyncSession,
    bot: Bot,
    query_text: str,
) -> list[OpsFact]:
    """이 요청에 적용할 승인된 운영 사실.

    `triggers` 가 비어 있으면 항상, 값이 있으면 질문에 그 표현이 있을 때만 포함한다.
    실패는 빈 목록으로 삼킨다 — 이 레이어가 답변을 막아서는 안 된다.
    """
    try:
        if bot.id is None:
            return []
        rows = await _load_facts(session, bot.id)
        if not rows:
            return []
        q = _normalize(query_text or "")
        out = []
        for row in rows:
            triggers = row.triggers or []
            if triggers and not any(_normalize(t) in q for t in triggers if t):
                continue
            out.append(row)
        return out
    except Exception:
        logger.exception("ops_facts 로드 실패 — 빈 목록으로 진행 bot_id=%s", getattr(bot, "id", None))
        return []


# ─── ① 프롬프트 블록 ──────────────────────────────────────────

# 라벨 뒤에 콜론으로 붙이는 형태라 한국어 조사 일치 문제가 생기지 않는다
# ('교제축복 는' 같은 것). 모델이 훑기에도 이쪽이 낫다.
_KIND_LABEL = {
    "deprecated": ("현행 기준 아님", "현행처럼 안내하지 말 것."),
    "forbidden": ("존재하지 않음", "있는 것처럼 설명하거나 절차를 만들지 말 것."),
}

# kind='crisis' 만 프롬프트에 **statement 를 싣지 않는다.** statement 는 사용자에게 그대로
# 나갈 안전 안내문이고(`build_crisis_suffix`), 프롬프트에는 이 고정 지시문이 대신 간다.
#
# 왜 나눴나 — 위기 응답을 프롬프트에 맡기면 4/4 가 안 나온다. 실측이다.
# 전용 위기 섹션(4단계 지시)을 가진 E_부모동행v6 조차 4회 중 2회만 통과했고
# (`exports/golden45_2026-08-11/FINDINGS.md` §4), 라이브 프롬프트(서비스방향 B)는
# 원칙 8「축복·가정행정과 무관한 질문에는 답할 수 없습니다」가 자살 신호를 범위 밖으로
# 밀어내 8/05·8/11·8/14 세 번 다 무너졌다.
#
# 그래서 역할을 갈랐다. **연락처와 안전 지시는 코드가 보장하고, 모델에게는 방해하지
# 말라고만 시킨다.** 모델이 쓰는 것은 위로 한두 문장뿐이다.
_CRISIS_DIRECTIVE = (
    "위기 신호다. 규정·교리·행정 안내를 중단하고, 답할 수 없다는 말도 하지 마라. "
    "1~2문장 위로만 하고 멈춰라. 안전 안내와 연락처는 시스템이 자동으로 덧붙이므로 "
    "네가 쓰지 마라."
)


def _line(fact: OpsFact) -> str:
    superseded = (fact.superseded or "").strip()
    statement = (fact.statement or "").strip()

    if fact.kind == "crisis":
        return f"- {_CRISIS_DIRECTIVE}"

    label = _KIND_LABEL.get(fact.kind)
    if label is None:  # contact
        text = statement
    elif superseded:
        text = f"{label[0]}: '{superseded}' — {statement or label[1]}"
    else:
        text = statement or label[1]

    return f"- {text.strip()[:OPS_FACT_LINE_CHAR_CAP]}"


def build_prompt_overlay(facts: list[OpsFact]) -> str:
    """시스템 프롬프트 뒤에 붙일 운영 사실 블록. 해당 사실이 없으면 빈 문자열."""
    rows = [f for f in facts if f.kind in _PROMPT_KINDS]
    if not rows:
        return ""

    lines = [
        "\n\n---\n[운영 확정 사실 — 검색된 문서보다 우선한다]",
        "아래는 문서에 아직 반영되지 않은 확정 사항이다. 검색된 문서가 다르게 읽히더라도",
        "아래를 따르고, 아래에 없는 내용을 여기서 추론하지 마라.",
    ]
    for fact in rows[:OPS_FACT_MAX_LINES]:
        line = _line(fact)
        if line.strip() != "-":
            lines.append(line)

    # 머리말만 남았으면 실제로 실을 내용이 없는 것이다.
    if len(lines) == 3:
        return ""
    return "\n".join(lines)


# ─── ①-b 위기 안내 블록 (kind='crisis') ────────────────────────

def build_crisis_suffix(facts: list[OpsFact]) -> str:
    """답변 끝에 **코드가 무조건 덧붙일** 안전 안내문. 걸린 crisis 행이 없으면 빈 문자열.

    `build_prompt_overlay` 와 달리 이건 모델에게 가는 글이 아니라 **사용자가 그대로 읽는
    글**이다. 운영자가 `ops_facts.statement` 에 쓴 문안이 한 글자도 안 바뀌고 나간다 —
    LLM 을 거치지 않는 것이 요점이다.

    `OPS_FACT_LINE_CHAR_CAP` 을 적용하지 않는다. 그 상한은 프롬프트가 무한정 자라는 것을
    막는 장치지, 사용자에게 나갈 안내문을 자르라는 뜻이 아니다. 여기서 300자를 자르면
    전화번호가 잘려 나간다.
    """
    blocks = [
        (f.statement or "").strip()
        for f in facts
        if f.kind == "crisis" and (f.statement or "").strip()
    ]
    return "\n\n".join(blocks)


# ─── ② 표기 치환 (kind='term') ────────────────────────────────

def term_rules(facts: list[OpsFact]) -> list[tuple[str, str]]:
    """(쓰면 안 되는 표기, 대신 쓸 표기) 목록.

    긴 표기를 먼저 적용해 부분 겹침으로 어긋나는 것을 막는다.
    """
    rules = [
        ((f.superseded or "").strip(), (f.statement or "").strip())
        for f in facts
        if f.kind == "term"
    ]
    rules = [(old, new) for old, new in rules if old and new and old != new]
    rules.sort(key=lambda r: len(r[0]), reverse=True)
    return rules


def _replace_one(text: str, old: str, new: str) -> str:
    if old in new:
        # 이미 올바르게 쓰인 자리를 다시 감싸지 않는다.
        # 예: '청평' → 'HJ천주천보수련원(청평)' 인데 본문에 이미 완성형이 있으면
        #     그대로 두 번 감싸져 'HJ…(HJ…(청평))' 이 된다.
        return text.replace(new, _GUARD).replace(old, new).replace(_GUARD, new)
    return text.replace(old, new)


def apply_term_rules(text: str, rules: list[tuple[str, str]]) -> str:
    if not text or not rules:
        return text
    for old, new in rules:
        text = _replace_one(text, old, new)
    return text


def apply_term_rules_to_citations(
    citations: list[RAGCitation],
    rules: list[tuple[str, str]],
) -> None:
    """인용의 `segments` 에도 같은 치환을 적용한다 (제자리 수정).

    ⚠ 이걸 빼면 각주가 조용히 사라진다.
    프론트가 `content.indexOf(segment)` 로 각주를 앵커하기 때문에
    (`frontend-client/src/components/chat/citationMarkers.ts`), 본문만 치환하면
    segment 가 더 이상 본문의 부분문자열이 아니게 되어 각주가 하나도 안 붙는다.

    `evidence` 는 원문 청크(`content`)의 부분문자열이므로 **건드리지 않는다.**
    """
    if not citations or not rules:
        return
    for citation in citations:
        if citation.segments:
            citation.segments = [apply_term_rules(s, rules) for s in citation.segments]


def invalidate_ops_facts_cache(bot_id: int | None = None) -> None:
    """봇별 또는 전체 캐시 무효화. 전역 사실이 바뀌면 전체를 비운다."""
    if bot_id is None:
        _OPS_FACT_CACHE.clear()
    else:
        _OPS_FACT_CACHE.pop(bot_id, None)
