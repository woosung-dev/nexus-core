"""봇별 strict 모드의 작은 정책 모음.

strict 모드는 답변의 최신성·공식성을 판정하지 않는다. 대신 일반 답변에는 이번
RAG 호출에서 받은 직접 인용을 요구하고, FAQ에는 운영자가 작성한 거절문만 허용한다.
"""

import re

from app.schemas.rag import RAGCitation
from app.services.wiki.store import SourceUnit


STRICT_EVIDENCE_MESSAGE = (
    "확인 가능한 직접 인용 근거가 없어 이 내용은 답변해 드릴 수 없습니다."
)

_REFUSAL_RE = re.compile(
    r"(?:답변|안내|도움).{0,16}(?:드리기|드릴|할).{0,16}(?:어렵|불가|않|못|없)|"
    r"답변할 수 없",
    re.IGNORECASE,
)


def has_direct_citation(citations: list[RAGCitation]) -> bool:
    """근사 백필이 아닌, 이번 RAG 응답의 식별 가능한 인용이 하나 이상인지 확인한다."""
    return any(
        not citation.approximate and bool(citation.title or citation.uri)
        for citation in citations
    )


def is_refusal_faq(answer: str) -> bool:
    """strict 봇에서 허용할 FAQ는 사용자를 안전하게 거절하는 안내문뿐이다."""
    return bool(_REFUSAL_RE.search(answer or ""))


# ── 어휘 경로 전용 게이트 ────────────────────────────────────────────────────
#
# `has_direct_citation()` 은 어휘 경로에서 **항상 참**이다. `wiki.service._citations()` 가
# 주입한 원문 유닛마다 `approximate=False` 인용을 만들기 때문이다 — 모델이 그 원문을
# 실제로 썼는지와 무관하다. 그래서 strict 를 켜도 보호가 하나도 늘지 않았다.
#
# 여기서는 대신 **모델이 답변에 남긴 근거 표기를 주입 목록과 대조한다.** 문자열 비교라
# LLM 추가 호출 0회 · 지연 0 · 결정론이다. 두 형식을 모두 받는다.
#
#     [[src: reg-3, glo-132]]        주입 블록의 [src_id] 라벨을 따라간 것
#     [근거: 규정집v20 제55조]        사람이 읽는 형식. `locator` 와 대조한다
#
# **조문 형식을 함께 받는 것이 핵심이다.** 봇 29(라이브 D-1 ver2 복제본) 20문항 × 2회
# 측정에서, src_id 만 보면 과잉 거절이 22.5%(9/40) 인데 조문을 함께 보면 5.0%(2/40) 로
# 떨어진다. 죽던 것은 「축복 헌금 얼마예요」(제55·56조) 같은 **정답**이었다.
# 같은 측정에서 주입 목록 밖 근거를 쓴 답변은 96셀 전부에서 0건이다.
_SRC_ID_RE = re.compile(r"\b(?:reg|glo)-\d+\b")
# 규정집 조문(`제55조`) 과 대사전 항목(`행정 134`). `locator` 가 그 형태로 저장돼 있다.
_ARTICLE_RE = re.compile(r"제\s*(\d+)\s*조")
_GLOSSARY_RE = re.compile(r"행정\s*(\d+)")


def _locator_keys(text: str) -> set[tuple[str, int]]:
    """조문·항목 번호를 대조용 키로 뽑는다. 0 채움을 지우려고 int 로 정규화한다 —
    모델이 「대사전 행정 002」라고 쓰는데 locator 는 「행정 2」다."""
    return {("조", int(m)) for m in _ARTICLE_RE.findall(text or "")} | {
        ("행", int(m)) for m in _GLOSSARY_RE.findall(text or "")
    }


def cited_ids(answer: str) -> set[str]:
    """답변이 표기한 원문 id. 마커 밖에 맨몸으로 쓴 것도 인용으로 친다."""
    return set(_SRC_ID_RE.findall(answer or ""))


def has_grounded_citation(answer: str, units: list[SourceUnit]) -> bool:
    """답변의 근거 표기가 **이번에 주입한 원문 안에 있는가.**

    하나라도 맞으면 참이다. 「모든 문장이 근거를 달았나」를 묻지 않는다 — 그렇게 걸면
    문장 하나가 마커를 빠뜨렸다는 이유로 답변 전체가 죽는다.
    """
    if not units:
        return False
    injected_ids = {u.src_id for u in units}
    if cited_ids(answer) & injected_ids:
        return True
    injected_loc: set[tuple[str, int]] = set()
    for unit in units:
        injected_loc |= _locator_keys(unit.locator)
    return bool(_locator_keys(answer) & injected_loc)
