"""
위키 경로 답변 생성 — 3-B 안.

기존 RAG(`GeminiRAGService`)와의 차이는 **검색을 누가 하느냐** 하나다.

    기존   질문 → Gemini file_search 가 스토어에서 검색 → 답변
    위키   질문 → 우리가 위키 요약으로 페이지 선택 → 그 페이지의 원문을 직접 주입 → 답변

file_search 호출이 없어 지연이 줄고, 무엇을 넣었는지 우리가 알기 때문에
Gemini 의 grounding 보고에 인용을 의존하지 않는다.

**근거로 표시하는 것은 언제나 원문이다.** 위키 사실 문장은 맥락으로만 넣고
인용에는 싣지 않는다 — 사용자에게 보일 근거가 우리가 만든 요약이 되면 안 된다.
"""

import logging
import time

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.schemas.rag import RAGCitation, RAGResponse
from app.services.wiki.store import Retrieved, SourceUnit, get_index

logger = logging.getLogger(__name__)

# 주입 상한 — 한 페이지가 sources 22개를 달고 있는 경우가 있어(가정공과금) 상한이 필요하다.
MAX_UNITS = 24
MAX_UNIT_CHARS = 2000

# `raw_budget` 모드의 예산. 팔 C 가 넣는 위키 3쪽 본문이 중앙값 ≈2,150자라, 거기에 맞췄다.
# 컨텍스트 크기를 맞춰야 "검색이 좋아졌다"와 "덜 넣었더니 좋아졌다"를 가를 수 있다.
BUDGET_CHARS = 3000
BUDGET_UNITS = 8
# 최소 보장 건수. 예산만 걸었더니 1위가 긴 조문일 때 **1건에서 끊겼다** —
# #12(금식)에서 1·2위 RRF 점수 차가 0.0003 인데 2위(정답 reg-33)가 잘려 나갔다.
# 상위 몇 건의 미세한 점수차로 답이 갈리면 안 된다. 바닥을 깔고 그 위에서 예산을 건다.
BUDGET_MIN_UNITS = 4


def _select_units(retrieved: Retrieved, context_mode: str) -> list[SourceUnit]:
    """무엇을 주입할지 고른다. 이 선택이 팔 B 와 B′ 를 가르는 전부다.

        raw         상위 페이지들의 sources 합집합 (최대 24건) — 기존 정책
        raw_budget  RRF 유닛 순위 상위, 예산 안에서만 — 페이지를 거치지 않아 부풀지 않는다
    """
    if context_mode != "raw_budget":
        return retrieved.units[:MAX_UNITS]

    picked: list[SourceUnit] = []
    total = 0
    for unit, _ in retrieved.ranked_units:
        if len(picked) >= BUDGET_UNITS:
            break
        size = len(unit.text[:MAX_UNIT_CHARS])
        # 바닥(4건)까지는 예산을 넘겨도 넣고, 그 위에서만 예산으로 끊는다.
        if len(picked) >= BUDGET_MIN_UNITS and total + size > BUDGET_CHARS:
            break
        picked.append(unit)
        total += size
    return picked


def _context_block(units: list[SourceUnit]) -> str:
    """원문 조각을 그대로 넣는다. 요약이 아니라 원문이어야 인용이 성립한다."""
    parts = []
    for unit in units:
        parts.append(f"[{unit.src_id}] {unit.doc} {unit.locator}\n{unit.text[:MAX_UNIT_CHARS]}")
    return "\n\n".join(parts)


async def build_hybrid_turns(bot_id: int, question: str, top_k: int = 3) -> list[dict[str, str]]:
    """팔 F — file_search 는 그대로 두고 BM25 로 뽑은 원문을 **앞선 턴**으로 얹는다.

    묻는 질문이 다르다. 위키 팔들은 「위키가 file_search 를 **대체**하나」이고,
    이 조합은 「BM25 원문이 file_search 를 **보완**하나」다. dense 를 우리 쪽에서 뺀 이상
    이쪽이 진짜 가설이다 — 의미 검색은 file_search 가, 어휘 검색은 우리가 맡는 구성.

    **질문 앞에 붙이지 않고 직전 턴으로 넣는 이유**: 앞에 붙이면 file_search 의 검색 질의가
    3,000자짜리 원문 덩어리로 오염돼, 재는 대상이 검색이 아니라 질의 오염이 된다.

    측정: 45문항 키워드 50.4% · 6.1초 (팔 A 단독 57.9% · 7.0초 / 어휘 전용 40.2% · 1.6초).
    `exports/wiki_eval/_run.py:237 run_hybrid` 과 같은 것을 만든다 — 갈라지면 안 된다.
    """
    index = await get_index(bot_id)
    retrieved = await index.search(question, top_k=top_k)
    units = _select_units(retrieved, "raw_budget")
    if not units:
        return []
    return [
        {"role": "user", "content": f"# 참고 규정 원문\n{_context_block(units)}"},
        {"role": "assistant", "content": "확인했습니다. 질문해 주세요."},
    ]


def _wiki_block(retrieved: Retrieved, with_summary: bool = False) -> str:
    """위키가 정리해 둔 내용.

    `## 사실` 의 각 문장에는 이미 `> 원문 인용` 이 붙어 있다(생성 규약).
    그래서 위키 페이지만 넣어도 근거 문장이 함께 들어간다 — wiki 모드가 성립하는 이유다.
    """
    parts = []
    for page, _ in retrieved.pages:
        block = [f"## {page.title}"]
        if with_summary and page.summary:
            block.append(page.summary)
        if page.facts:
            block.append(page.facts)
        parts.append("\n".join(block))
    return "\n\n".join(parts)


def _citations(units: list[SourceUnit]) -> list[RAGCitation]:
    """주입한 원문을 인용 후보로 낸다.

    주입했다는 이유만으로 전부 "근거"라고 하면 과다 인용이다. 좁히는 일은 기존
    `fill_evidence`(답변↔원문 대조)가 이어받는다 — 여기서 어휘 매칭으로 미리 거르면
    거짓양성이 난다는 것이 실측이다(`project_citation_evidence_highlight`).
    """
    out: list[RAGCitation] = []
    for unit in units:
        out.append(
            RAGCitation(
                title=f"{unit.doc} {unit.locator}",
                content=unit.text[:MAX_UNIT_CHARS],
                approximate=False,
                uri=unit.src_id,
            )
        )
    return out


async def answer_with_wiki(
    bot_id: int,
    question: str,
    system_prompt: str = "",
    model_name: str = "gemini-3.5-flash-lite",
    temperature: float | None = None,
    max_tokens: int = 2048,
    history: list[dict[str, str]] | None = None,
    top_k: int = 3,
    context_mode: str = "raw",
) -> tuple[RAGResponse, Retrieved]:
    """위키 경로로 답변한다. 1단 결과(Retrieved)도 함께 돌려준다 — 측정에 필요하다.

    context_mode 는 **무엇을 근거로 삼느냐**를 가른다.

        raw         원문 조각을 주 근거로 주입하고 위키 정리를 곁들인다 (원문 73% : 위키 27%).
        raw_budget  같은 구조이되 원문을 RRF 유닛 순위 상위 예산분만 넣는다.
        wiki        카파시 원안 — 위키 페이지 본문으로 답한다. 원문은 따로 넣지 않는다
                    (페이지의 `## 사실` 에 이미 원문 인용이 붙어 있다).
    """
    settings = get_settings()
    if temperature is None:
        temperature = settings.RAG_TEMPERATURE

    t0 = time.perf_counter()
    index = await get_index(bot_id)
    retrieved = await index.search(question, top_k=top_k)
    search_ms = (time.perf_counter() - t0) * 1000

    units = _select_units(retrieved, context_mode)
    if not retrieved.pages or (context_mode != "wiki" and not units):
        logger.info("위키 1단 빈손 — bot_id=%s q=%.30s", bot_id, question)
        return RAGResponse(answer="", citations=[], followups=[]), retrieved

    contents: list[types.Content] = []
    for turn in history or []:
        contents.append(
            types.Content(
                role="user" if turn.get("role") == "user" else "model",
                parts=[types.Part(text=turn.get("content", ""))],
            )
        )
    contents.append(
        types.Content(
            role="user",
            parts=[
                types.Part(
                    # 규범적 지시는 여기 두지 않는다 — system_prompt 로 받는다.
                    # 팔 A(file_search)에는 없는 지시를 여기 심으면 비교가 불공정해진다.
                    text=(
                        f"# 규정 정리\n{_wiki_block(retrieved, with_summary=True)}\n\n"
                        f"# 질문\n{question}"
                        if context_mode == "wiki"
                        else f"# 규정 원문\n{_context_block(units)}\n\n"
                        f"# 참고 정리\n{_wiki_block(retrieved)}\n\n"
                        f"# 질문\n{question}"
                    )
                )
            ],
        )
    )

    client = genai.Client(api_key=settings.GEMINI_API_KEY.get_secret_value())
    t1 = time.perf_counter()
    response = await client.aio.models.generate_content(
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt or None,
            temperature=temperature,
            max_output_tokens=max_tokens,
        ),
    )
    gen_ms = (time.perf_counter() - t1) * 1000

    answer = (response.text or "").strip()
    logger.info(
        "wiki answer — mode=%s bot_id=%s pages=%s units=%d(%d자) search=%.0fms gen=%.0fms",
        context_mode,
        bot_id,
        [f"{p.slug}:{s:.4f}" for p, s in retrieved.pages],
        len(units),
        sum(len(u.text[:MAX_UNIT_CHARS]) for u in units),
        search_ms,
        gen_ms,
    )

    return (
        RAGResponse(answer=answer, citations=_citations(units), followups=[]),
        retrieved,
    )
