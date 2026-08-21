"""
채팅 비즈니스 로직을 처리하는 서비스 계층.
컨트롤러(chat.py)에서 넘겨받은 요청을 기반으로 FAQ, RAG, 일반 LLM 분기 처리를 수행하고,
정상 스트리밍 및 Non-Streaming 응답을 책임집니다.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.crud import crud_chat
from app.models.bot import Bot
from app.models.chat import ChatSession
from app.models.enums import MessageRole
from app.schemas.chat import ChatCompletionRequest, ChatCompletionResponse
from app.schemas.rag import RAGCitation, RAGResponse
from app.services.faq_service import search_faq_override
from app.services.followup_service import generate_followups
from app.services.llm.factory import get_llm_service
from app.services.ops_facts_service import (
    apply_term_rules,
    apply_term_rules_to_citations,
    build_crisis_suffix,
    build_prompt_overlay,
    load_runtime_facts,
    term_rules,
)
from app.services.rag.factory import get_rag_service
from app.services.strict_mode import (
    STRICT_EVIDENCE_MESSAGE,
    cited_ids,
    evidence_ok,
    fabricated_citations,
    fabricated_vs_grounding,
    grounding_locators,
    has_direct_citation,
    is_refusal_faq,
    strip_source_markers,
    strip_source_markers_from_citations,
)
from app.services.turn_trace import (
    CRISIS,
    FAQ,
    OPS_FACTS,
    RECORD,
    RETRIEVAL,
    STRICT,
    STRIP,
    TERM,
    UNANSWERED,
    TurnTrace,
    prompt_sha8,
    unit_refs,
)
from app.services.unanswered import (
    UNANSWERED_MESSAGE,
    Reason,
    RetrievalTrace,
    is_self_refusal,
    normalize_question,
)

logger = logging.getLogger(__name__)

# 어휘 검색(BM25 원문 주입)은 Gemini 클라이언트를 직접 만든다. 다른 프로바이더 봇에서 켜면
# 조용히 깨지므로 file_search 로 되돌린다.
_LEXICAL_PROVIDER_PREFIX = "gemini"


def _strict_blocks(
    retrieval_mode: str,
    trace: RetrievalTrace,
    response: RAGResponse,
    crisis_active: bool = False,
) -> bool:
    """strict 봇의 답변을 고정 문구로 바꿀 것인가.

    경로마다 「인용」의 뜻이 달라서 자를 나눈다.

        file_search·both   Gemini 가 준 grounding 을 본다 — 기존 `has_direct_citation`
        lexical            **주입 목록과 두 방향으로 대조한다** — `evidence_ok`
                           ① 주입한 근거를 짚었나  ② 주입 안 한 근거를 대지 않았나

    어휘 경로에 기존 자를 대면 아무것도 안 걸린다. `wiki.service._citations()` 가 주입
    유닛마다 `approximate=False` 인용을 만들어 언제나 참이기 때문이다. 그래서 화면이
    「직접 인용을 남기지 못하면 차단합니다」라고 쓰는데 실제 보호는 0이었다.

    **봇이 스스로 못 답한다고 말한 답변은 그대로 둔다.** 그건 근거 없이 지어낸 답이
    아니라 프롬프트가 시킨 올바른 거절이고, 고정 문구로 바꾸면 「가정행복국 02-3271-0502」
    같은 안내가 사라져 오히려 나빠진다. 봇 29 측정에서 차단 대상 31셀 중 30셀이 이것이었다.

    폴백했을 때는 어휘 경로가 아니다 — 답변을 만든 것은 file_search 라 기존 자로 돌아간다.

    ② 를 2026-08-14 에 더했다. ① 만 보면 「맞는 근거 하나에 가짜 셋을 얹은 답변」이 통과한다 —
    110셀 실측에서 가짜 근거 26건 중 18건이 그렇게 새어 나갔다. 근거와 수치는 `evidence_ok`.

    ⚠ **대조 목록은 `trace.evidence_units` 다 — `trace.units` 가 아니다.** 프롬프트에는
    `# 규정 원문`(units) 뒤에 `# 참고 정리`(위키 페이지)도 들어가고, 그 `## 사실` 에는
    `> 원문 인용` 이 붙어 있어 units 에 없는 조문 원문이 모델에게 간다. units 하고만
    대조하던 동안 **정당한 인용이 「지어냄」으로 차단됐다** — replay 600건 재판정에서
    57건 중 56건이 그 오경보였고, 내용이 틀린 답변은 0건이었다
    (`exports/replay_2026-08/_rejudge_pages.py`).

    **위기 턴은 이 자를 대지 않는다.** 위기 안내에는 규정집 인용이 붙지 않아
    `evidence_ok` 도 `has_direct_citation` 도 통과할 수 없다. 실측으로 C07「죽고 싶어요」가
    4/4 차단됐고(`exports/regression/_gate_s1_*.json`), 그러면 자살 신호에
    「확인 가능한 직접 인용 근거가 없어…」만 나간다. 이 게이트는 **문서에 없는 것을
    지어냈나**를 막는 자인데, 위기 블록은 운영자가 승인한 고정 문안이라 지어낼 여지가 없다.
    근거가 없는 게 아니라 **근거의 종류가 다르다** — `ops_facts` 승인이 그 근거다.
    """
    if crisis_active:
        return False
    if _uses_grounding_ruler(retrieval_mode, trace):
        if not has_direct_citation(response.citations):
            return True
        # ② 지어냄 검사 (2026-08-22 추가) — grounding 청크를 대조 목록으로 쓴다.
        # ①(본문 표기 요구)은 넣지 않는다: 이 경로의 ①은 grounding 존재이고, 표기를
        # 새로 요구하면 지금까지 통과하던 무표기 답변이 통째로 죽는다.
        answer = response.answer or ""
        fake = fabricated_vs_grounding(answer, response.citations, trace.evidence_units)
        return bool(fake) and not is_self_refusal(answer)
    answer = response.answer or ""
    return not evidence_ok(answer, trace.evidence_units) and not is_self_refusal(answer)


def _uses_grounding_ruler(retrieval_mode: str, trace: RetrievalTrace) -> bool:
    """이 턴을 grounding 청크로 재는가(참), 주입 목록으로 재는가(거짓).

    답변을 **무엇이 만들었나**로 갈린다. 어휘 1단이 빈손이라 file_search 로 폴백했으면
    주입 목록은 답변과 무관하다 — 그때도 참이다.

    **판정(`_strict_blocks`)과 기록(`turn.stage(STRICT, ...)`)이 같은 자를 써야 한다.**
    어긋나 있던 동안 관리자 화면의 `fabricated_loc` 이 게이트가 안 본 목록으로 찍혔다.
    """
    fell_back = bool({Reason.LEXICAL_EMPTY, Reason.CORPUS_UNAVAILABLE} & set(trace.reasons))
    return retrieval_mode != "lexical" or fell_back


def _attach_crisis(answer: str, block: str) -> tuple[str, str]:
    """위기 안내 블록을 답변에 붙인다. `(새 답변, 판정)` 을 돌려준다.

    **거절문 뒤에 안전 안내를 붙이지 않는다.** 「규정집 이외의 내용에는 답할 수 없습니다」
    다음에 안전 안내가 오면 사용자가 먼저 읽는 것은 거절이다. 판정 기준 ①「안전 우선」이
    바로 그 순서를 보는 것이라, 이 경우에는 **덧붙이지 말고 통째로 바꾼다.**

    바꾸는 대상은 셋이다 — 빈 답변 · 봇이 스스로 못 답한다고 한 답변 · 게이트가 이미
    갈아 끼운 고정 문구. 그 밖에는 모델이 쓴 위로 문장을 살리고 뒤에 붙인다.
    """
    text = (answer or "").strip()
    if (
        not text
        or text in (STRICT_EVIDENCE_MESSAGE, UNANSWERED_MESSAGE)
        or is_self_refusal(text)
    ):
        return block, "replaced"
    return f"{text}\n\n{block}", "appended"


# `fs_fusion` 2단에 붙이는 작성 지시. 스케일 150 실측에서 codex 위험신호를 5→1 로
# 낮춘 것이 이 두 줄이다(`docs/architecture/handoff-launch-week-2026-08-22.md` §2-b).
# ⚠ **표기율은 이 지시로 안 오른다** — (근거:) 표기 55% 로 현행 56% 와 같았다. 지시가
# 사는 곳은 「근거 없는 단정을 안 한다」와 「유형을 안 물어보고 단정하지 않는다」 쪽이다.
FUSION_WRITE_INSTRUCTION = (
    "# 작성 지시\n"
    "- 본문에서 근거로 삼은 대목마다 (근거: 문서·조항) 표기를 붙여라. 위 자료에 있는 내용만 근거로 써라.\n"
    "- 규정이 축복 유형(미혼 1세 편성·기성축복·축복자녀 간 등)에 따라 다르면 어느 유형 기준인지 명시하라. "
    "사용자의 유형을 모르면 단정하지 말고 유형을 확인하라.\n"
)


def _fusion_prompt(question: str, citations: list[RAGCitation], wiki_block: str) -> str:
    """1단이 물어 온 청크를 원문으로 깔고 다시 쓰게 하는 2단 프롬프트.

    측정 러너 `exports/replay_2026-08/_run_scale.py:_gen_b2v2` 와 **같은 순서·같은 문구**다.
    바꾸면 실측치(답변률 46.7% · 위험신호 1)와 프로덕션이 갈라진다.

    청크 본문은 표시용 800자 절단본(`content`)이 아니라 `full_content` 를 쓴다 — 모델에게
    자르지 않은 원문을 줘야 조문 중간이 잘려 나가지 않는다.
    """
    chunks = "\n\n".join(
        f"[{c.title}]\n{c.full_content or c.content}" for c in citations
    )
    return (
        f"# 규정 원문(검색 결과)\n{chunks}\n\n"
        + (f"# 참고 정리\n{wiki_block}\n\n" if wiki_block else "")
        + f"{FUSION_WRITE_INSTRUCTION}\n"
        + f"# 질문\n{question}"
    )


def _effective_retrieval_mode(bot: Bot) -> str:
    """봇 설정을 실제로 탈 수 있는 조달 방식으로 바꾼다.

    미설정(기존 봇)은 `file_search` 다 — 컬럼 server_default 와 같아서 **기존 동작과 동일**하다.
    """
    mode = getattr(bot, "retrieval_mode", None) or "file_search"
    if mode not in ("file_search", "lexical", "both", "fs_fusion"):
        logger.warning("알 수 없는 retrieval_mode=%r bot_id=%s — file_search 로 처리", mode, bot.id)
        return "file_search"
    if mode != "file_search" and not (bot.llm_model or "").startswith(_LEXICAL_PROVIDER_PREFIX):
        logger.warning(
            "retrieval_mode=%s 는 Gemini 전용이다 — bot_id=%s model=%s 는 file_search 로 폴백",
            mode, bot.id, bot.llm_model,
        )
        return "file_search"
    return mode


# 비동기 백필 태스크 참조 보관소 — GC 로 태스크가 취소되는 것을 방지.
_citation_backfill_tasks: set[asyncio.Task] = set()


async def _backfill_citations_async(
    bot_id: int,
    model_name: str,
    system_prompt: str,
    message_id: int,
    prompt: str,
    answer: str = "",
) -> None:
    """응답 트랜잭션과 분리된 새 세션에서 interactions 인용을 캡처해 메시지에 백필한다.

    메인 답변(generate_content+persona)은 grounding 보고를 억제해 인용을 거의 못 남기므로,
    응답을 막지 않도록 별도 비동기 태스크에서 채운다. 실패는 조용히 경고만 남긴다.
    이 인용은 표시된 답변이 아니라 이 호출이 새로 생성한 답변 기준이라 approximate=True 로 나간다.
    """
    try:
        rag_service = get_rag_service(provider=model_name)
        search_fn = getattr(rag_service, "search_citations", None)
        if search_fn is None:
            return
        citations = await search_fn(
            bot_id=bot_id,
            prompt=prompt,
            system_prompt=system_prompt,
            model_name=model_name,
        )
        if not citations:
            return

        # 근거 구절까지 같이 채워 DB 쓰기를 1회로 끝낸다.
        await _fill_evidence(rag_service, citations, answer, model_name)

        # 응답 트랜잭션과 분리된 새 세션으로 백필 (요청 커밋 이후 실행되므로 안전).
        from app.core.database import async_session

        async with async_session() as session:
            updated = await crud_chat.update_message_citations(
                session, message_id, [c.model_dump() for c in citations]
            )
            if updated:
                await session.commit()
                logger.info(
                    "인용 백필 완료 message_id=%s citations=%d", message_id, len(citations)
                )
    except Exception as e:
        logger.warning("인용 백필 실패 message_id=%s: %s", message_id, e)


async def _fill_evidence(rag_service, citations, answer: str, model_name: str) -> int:
    """인용 청크에서 실제 근거 구절을 뽑아 채운다. 지원하지 않는 provider 면 조용히 통과."""
    fill_fn = getattr(rag_service, "fill_evidence", None)
    if fill_fn is None or not citations:
        return 0
    return await fill_fn(citations=citations, answer=answer, model_name=model_name)


async def _fill_evidence_async(
    model_name: str, message_id: int, citations: list, answer: str
) -> None:
    """정확 인용이 이미 붙은 메시지에 근거 구절만 뒤늦게 채운다.

    청크당 LLM 1회라 답변 경로에 넣으면 체감 지연이 그대로 늘어난다. 인용 백필과 같은 이유로
    응답을 보낸 뒤 별도 태스크에서 돌리고, 실패는 경고만 남긴다(인용 표시 자체는 이미 살아 있다).
    """
    try:
        from app.schemas.rag import RAGCitation

        parsed = [RAGCitation(**c) if isinstance(c, dict) else c for c in citations]
        rag_service = get_rag_service(provider=model_name)
        filled = await _fill_evidence(rag_service, parsed, answer, model_name)
        if not filled:
            return

        from app.core.database import async_session

        async with async_session() as session:
            updated = await crud_chat.update_message_citations(
                session, message_id, [c.model_dump() for c in parsed]
            )
            if updated:
                await session.commit()
                logger.info(
                    "근거 구절 채움 message_id=%s cards=%d/%d",
                    message_id,
                    filled,
                    len(parsed),
                )
    except Exception as e:
        logger.warning("근거 구절 채우기 실패 message_id=%s: %s", message_id, e)


def _schedule_evidence_fill(
    model_name: str, message_id: int, citations: list, answer: str
) -> None:
    """근거 구절 채우기를 백그라운드 태스크로 예약한다(응답 반환을 막지 않음)."""
    task = asyncio.create_task(
        _fill_evidence_async(model_name, message_id, citations, answer)
    )
    _citation_backfill_tasks.add(task)
    task.add_done_callback(_citation_backfill_tasks.discard)


def _schedule_citation_backfill(
    bot_id: int,
    model_name: str,
    system_prompt: str,
    message_id: int,
    prompt: str,
    answer: str = "",
) -> None:
    """인용 백필을 백그라운드 태스크로 예약한다(응답 반환을 막지 않음)."""
    task = asyncio.create_task(
        _backfill_citations_async(
            bot_id, model_name, system_prompt, message_id, prompt, answer
        )
    )
    _citation_backfill_tasks.add(task)
    task.add_done_callback(_citation_backfill_tasks.discard)


# ─── 「답변 못 함」 기록 ──────────────────────────────────────────
#
# 관찰된 사실만 남긴다. 검색 점수로 「답할 수 있나」를 추정하지 않는다 —
# 45문항 실측에서 네 갈래 신호가 전부 실패했고, 같은 종류의 시도가 과거에도 두 번 기각됐다.
# 자세한 이유는 `app/services/unanswered.py` 모듈 docstring.


async def _record_unanswered(
    session: AsyncSession,
    *,
    bot: Bot,
    chat_session: ChatSession,
    message_id: int | None,
    question: str,
    reasons: list[str],
    detail: dict | None = None,
) -> None:
    """관찰된 신호를 `unanswered_questions` 에 남긴다. 커밋은 호출자가 한다.

    **이 레이어가 답변을 막아서는 안 된다.**

    ⚠ `try/except` 만으로는 그게 안 된다. DB 오류가 나면 파이썬 예외는 잡히지만
    **트랜잭션이 오염된 채로 남아** 호출자의 `commit()` 이 `PendingRollbackError` 로 죽는다.
    그러면 어시스턴트 메시지까지 통째로 날아가고 사용자는 500 을 받는다 — 기록하려다
    답변을 잃는 것이라 정반대 결과다. 실측으로 확인했다.

    그래서 SAVEPOINT 안에서 쓴다. 실패하면 여기까지만 되감기고 바깥 트랜잭션은 멀쩡하다.
    """
    if not reasons:
        return
    try:
        from app.crud import crud_unanswered

        norm = normalize_question(question)
        async with session.begin_nested():
            for reason in reasons:
                await crud_unanswered.record(
                    session,
                    bot_id=bot.id,
                    session_id=chat_session.id,
                    message_id=message_id,
                    question_text=question,
                    question_norm=norm,
                    reason=reason,
                    detail=detail or {},
                )
    except Exception:
        logger.exception(
            "못 답한 질문 기록 실패 — 응답은 그대로 진행 bot_id=%s", getattr(bot, "id", None)
        )


class ChatService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _retrieve_and_generate(
        self,
        retrieval_mode: str,
        rag_service,
        bot: Bot,
        message: str,
        system_prompt: str,
        history: list[dict[str, str]] | None,
    ) -> tuple[RAGResponse, RetrievalTrace]:
        """근거를 무엇으로 조달할지 하나만 가른다. 첫 번째 반환값은 세 경우 모두 `RAGResponse` 다.

        그래서 이 뒤의 처리(strict 게이트 · 용어 치환 · 메시지 저장 · 근거 형광펜 · 응답)는
        한 줄도 바뀌지 않는다. 프론트엔드도 손댈 필요가 없다.

        두 번째 반환값 `RetrievalTrace` 는 **조달 과정에서 관찰된 것**이다. `answer_with_wiki`
        가 `tuple[RAGResponse, Retrieved]` 를 돌려주는데 여기서 두 번째를 버리고 있었다 —
        폴백이 일어났다는 사실이 로그 한 줄로만 남고 데이터로는 사라졌다. 그걸 살린다.
        **점수는 안 쓴다.** 쓰는 것은 주입된 원문(2층이 읽을 것)과 관찰된 사실뿐이다.

        `file_search` 는 **기존 호출을 인자까지 그대로** 유지한다 — 기본값 봇이 지금과
        한 글자도 달라지면 안 된다(`tests/test_retrieval_mode.py` 가 인자를 통째로 비교한다).
        """
        from app.services.wiki.store import WikiCorpusUnavailable

        trace = RetrievalTrace()

        if retrieval_mode == "lexical":
            # 팔 B′ — file_search 를 아예 부르지 않고 BM25 원문만 준다. 1.6초.
            from app.services.wiki.service import _select_units, answer_with_wiki

            try:
                rag_response, retrieved = await answer_with_wiki(
                    bot_id=bot.id,
                    question=message,
                    system_prompt=system_prompt,
                    model_name=bot.llm_model,
                    history=history or None,
                    context_mode="raw_budget",
                )
            except WikiCorpusUnavailable as e:
                logger.warning("어휘 검색 코퍼스 없음 bot_id=%s — file_search 로 폴백: %s", bot.id, e)
                trace.mark(Reason.CORPUS_UNAVAILABLE)
            else:
                # 답변 생성이 실제로 본 목록과 **같은 목록이어야** 2층 판정이 성립한다.
                # `_select_units` 는 순수 함수라 다시 불러도 같은 결과다
                # (측정 하네스도 같은 방식으로 바깥에서 부른다).
                if retrieved is not None:
                    trace.units = _select_units(retrieved, "raw_budget")
                    # 프롬프트에는 `# 참고 정리` 로 위키 페이지도 함께 들어간다. 그 페이지가
                    # 실어 온 조문은 units 에 없어도 모델이 본 근거다 — 안 남기면 정확한
                    # 인용이 「지어냄」으로 집계된다(RetrievalTrace docstring).
                    trace.pages = [page.slug for page, _ in retrieved.pages]
                    trace.page_src_ids = sorted(
                        {src for page, _ in retrieved.pages for src in page.sources}
                    )
                    # `retrieved.units` 가 바로 「상위 페이지들의 sources 합집합」이다
                    # (`store.WikiIndex.search`). 인덱스를 다시 안 타도 된다.
                    trace.page_units = list(retrieved.units)
                # 어휘 검색은 동의어·구어체 질문에서 빈손이 될 수 있다(핸드오프 §5 #13).
                # 그때 answer_with_wiki 는 빈 답변을 돌려주는데, 빈 답변을 그대로 내보내면
                # 사용자에게는 그냥 고장이다. 의미 검색으로 되돌린다.
                if (rag_response.answer or "").strip():
                    # followups 는 비어 있다(file_search 경로는 공짜로 받는다). 카카오가
                    # 이것을 쓰므로 알려진 회귀다 — 지연이 이 모드의 값어치라 추가 호출로 메우지 않는다.
                    return rag_response, trace
                # **폴백은 없애지 않는다 — 사용자 보호 장치다.** 폴백했다는 사실만 남긴다.
                logger.info("어휘 검색 결과 없음 bot_id=%s — file_search 로 폴백", bot.id)
                trace.mark(Reason.LEXICAL_EMPTY)

        elif retrieval_mode == "both":
            # 팔 F — file_search 는 그대로 두고 BM25 원문을 앞선 턴으로 얹는다. 6.1초.
            from app.services.wiki.service import build_hybrid_turns

            try:
                extra = await build_hybrid_turns(bot.id, message)
            except WikiCorpusUnavailable as e:
                logger.warning("하이브리드 코퍼스 없음 bot_id=%s — file_search 로 폴백: %s", bot.id, e)
                trace.mark(Reason.CORPUS_UNAVAILABLE)
                extra = []
            merged = (extra + list(history)) if history else extra
            response = await rag_service.generate_with_rag(
                bot_id=bot.id,
                prompt=message,
                system_prompt=system_prompt,
                model_name=bot.llm_model,
                history=merged or None,
            )
            return response, trace

        response = await rag_service.generate_with_rag(
            bot_id=bot.id,
            prompt=message,
            system_prompt=system_prompt,
            model_name=bot.llm_model,
            history=history or None,
        )

        if retrieval_mode == "fs_fusion":
            return await self._fuse(rag_service, bot, message, system_prompt, response, trace)
        return response, trace

    async def _fuse(
        self,
        rag_service,
        bot: Bot,
        message: str,
        system_prompt: str,
        draft: RAGResponse,
        trace: RetrievalTrace,
    ) -> tuple[RAGResponse, RetrievalTrace]:
        """팔 B2v2 — file_search 를 **검색기로만** 쓰고, 물어 온 청크로 답을 다시 쓴다.

        1단은 위의 `generate_with_rag` 그대로다(인자 한 글자도 안 바꾼다). 2단은 도구 없이
        청크 + 위키 페이지 + 작성 지시를 넣고 본문만 받는다. 인용·followups 는 1단 것을
        물려준다 — 2단은 검색을 안 하므로 새 인용이 나올 수 없고, followups 를 다시 받으면
        호출이 하나 더 는다.

        replay 150 실측(2026-08-21): 답 받음 38.0%(현행) → 46.7%, 자체 거절 39.3% → 10.0%.
        **답변률은 A(file_search 단독)와 같다** — 2호출의 값어치는 안전축이다
        (codex 위험신호 5 → 1). 지연은 2배(9초 → 15초 안팎).

        ⚠ **빈손이면 융합하지 않는다.** 청크가 없으면 넣을 원문이 없고, 그 상태로 2단을
        돌리면 모델이 기억으로 답을 쓴다 — 게이트가 막을 수 있는 지어냄이 아니라
        **막을 수 없는** 지어냄이 된다.
        """
        if not draft.citations:
            return draft, trace

        wiki_block = await self._fusion_wiki(bot.id, message, trace)
        answer = await rag_service.generate_plain(
            prompt=_fusion_prompt(message, draft.citations, wiki_block),
            system_prompt=system_prompt,
            model_name=bot.llm_model,
        )
        return (
            RAGResponse(
                answer=answer or draft.answer,
                citations=draft.citations,
                followups=draft.followups,
            ),
            trace,
        )

    async def _fusion_wiki(self, bot_id: int, message: str, trace: RetrievalTrace) -> str:
        """2단 프롬프트에 얹을 `# 참고 정리` 블록. 없으면 빈 문자열이다.

        **페이지가 실어 온 원문을 trace 에 남기는 것이 핵심이다.** 게이트가
        grounding 청크하고만 대조하면, 위키 페이지의 `> 원문 인용` 을 정확히 옮긴 답변이
        「지어냄」으로 차단된다(`strict_mode.grounding_locators` 의 `extra_units`).

        코퍼스가 없어도 융합은 그대로 간다 — 위키는 보조 채널이지 근거 조달 경로가 아니다.
        `Reason.CORPUS_UNAVAILABLE` 을 찍지 않는 이유가 이것이다. 그 이유코드는
        「폴백했다」는 뜻이라 결손 집계에서 어휘 경로의 폴백과 섞인다.
        """
        from app.services.wiki.service import _wiki_block
        from app.services.wiki.store import WikiCorpusUnavailable, get_index

        try:
            index = await get_index(bot_id)
            retrieved = await index.search(message, top_k=3)
        except WikiCorpusUnavailable as e:
            logger.info("융합 위키 채널 없음 bot_id=%s — 청크만으로 진행: %s", bot_id, e)
            return ""
        if not retrieved.pages:
            return ""
        trace.pages = [page.slug for page, _ in retrieved.pages]
        trace.page_src_ids = sorted({src for page, _ in retrieved.pages for src in page.sources})
        trace.page_units = list(retrieved.units)
        return _wiki_block(retrieved)

    async def _load_history(
        self, session_id: int, bot: Bot, current_message: str
    ) -> list[dict[str, str]]:
        """멀티턴 대화 기억용 슬라이딩 윈도우 히스토리 로드.

        bot.history_window(0=비활성)만큼 최근 메시지를 [{"role","content"}] 로 직렬화한다.
        call site(웹 엔드포인트/카카오 워커)가 현재 사용자 메시지를 먼저 flush하므로
        같은 트랜잭션 조회에 포함됨 → 마지막 row가 현재 메시지와 일치할 때만 드랍.
        """
        window = bot.history_window or 0
        if window <= 0:
            return []

        rows = await crud_chat.get_recent_messages(
            self.session, session_id=session_id, limit=window + 1
        )
        if rows and rows[-1].role == MessageRole.USER and rows[-1].content == current_message:
            rows = rows[:-1]
        rows = rows[-window:]

        cut = get_settings().CHAT_HISTORY_MAX_CHARS_PER_MESSAGE
        history: list[dict[str, str]] = []
        for m in rows:
            content = m.content
            if cut > 0 and len(content) > cut:
                content = content[:cut] + " …(이하 생략)"
            history.append(
                {
                    "role": "user" if m.role == MessageRole.USER else "assistant",
                    "content": content,
                }
            )
        return history

    async def process_chat_request(
        self,
        request: ChatCompletionRequest,
        bot: Bot,
        chat_session: ChatSession,
    ):
        """
        FAQ Override 검색 결과, RAG 사용 여부, 스트리밍 여부에 따라 적절한 응답 형식을 반환합니다.
        스트리밍 시 DB 저장은 제너레이터(SSE)가 끝날 때 내부적으로 호출됩니다.
        """
        # 진단용 분기 식별 로그: 어느 경로(FAQ/RAG/일반 LLM, OpenAI/Gemini)로 빠지는지 운영에서 한 줄로 확인.
        logger.info(
            "chat req — bot_id=%s model=%s stream=%s req_use_rag=%s bot_use_rag=%s "
            "history_window=%d msg_len=%d session_id=%s",
            bot.id,
            bot.llm_model,
            request.stream,
            request.use_rag,
            bot.use_rag,
            bot.history_window or 0,
            len(request.message),
            chat_session.id,
        )

        # 한 턴이 여덟 단계를 어떻게 지났는지 남긴다(관리자 전용). 값을 만들지 않고
        # **이미 결정된 것을 받아 적기만** 한다 — 추가 LLM 호출도 추가 DB 왕복도 없다.
        turn = TurnTrace()
        turn.snapshot(bot, bot.system_prompt or "", request)

        # 1. FAQ Override 검색 (시맨틱 라우팅)
        faq_obs: dict = {}
        faq_match = await search_faq_override(
            session=self.session,
            bot_id=bot.id,
            query_text=request.message,
            observe=faq_obs,
        )

        if faq_match:
            # FAQ는 strict 봇의 명시적인 거절 안내에만 사용한다.
            faq_content = faq_match.answer
            faq_source = "faq_override"
            if bot.evidence_policy_mode == "strict" and not is_refusal_faq(faq_content):
                logger.warning("strict FAQ blocked: faq_id=%s", faq_match.faq_id)
                faq_content = STRICT_EVIDENCE_MESSAGE
                faq_source = "policy_block"

            # FAQ 가 가로챈 턴은 여기서 끝난다 — 검색도 생성도 타지 않는다.
            turn.stage(
                FAQ, faq_source, faq_id=faq_match.faq_id,
                similarity=faq_match.similarity, **faq_obs,
            )
            await crud_chat.create_message(
                session=self.session,
                session_id=chat_session.id,
                role=MessageRole.ASSISTANT,
                content=faq_content,
                trace=turn.to_json(),
            )
            chat_session.updated_at = datetime.now(timezone.utc)
            await self.session.commit()

            logger.info(
                f"FAQ Override 응답: faq_id={faq_match.faq_id}, "
                f"similarity={faq_match.similarity}"
            )

            return ChatCompletionResponse(
                session_id=chat_session.id,
                content=faq_content,
                bot_id=bot.id,
                source=faq_source,
            )

        # 멀티턴 대화 기억 — FAQ 분기 통과 후 1회만 로드 (FAQ hit 시 불필요한 쿼리 방지).
        # history_window=0(기본)이면 빈 리스트 → 기존 stateless 동작과 완전 동일.
        history = await self._load_history(chat_session.id, bot, request.message)
        if history:
            logger.info(
                "chat history loaded — session_id=%s history_len=%d",
                chat_session.id,
                len(history),
            )

        # 운영 확정 사실 — 규정집이 "폐지됐다"고 말해주지 않는 것들을 프롬프트에 얹는다.
        # 승인된 행이 없으면 overlay 는 빈 문자열이라 기존 동작과 완전히 동일하다.
        # term(표기 통일)은 여기 들어가지 않고 응답 후처리로 치환한다 — 프롬프트 지시로는
        # 안 지켜지는 것이 실측됐다(FINDINGS §2-4).
        turn.stage(FAQ, "pass", **faq_obs)

        ops_facts = await load_runtime_facts(self.session, bot, request.message)
        effective_system_prompt = (bot.system_prompt or "") + build_prompt_overlay(ops_facts)
        ops_term_rules = term_rules(ops_facts)
        # 위기 안내. 트리거가 걸린 턴에만 값이 있고, 그때부터 이 턴의 처리가 달라진다 —
        # strict 게이트를 안 태우고(`_strict_blocks`), 답변 끝에 고정 블록을 붙이고,
        # 배경 인용 백필과 「답변 못 함」 적재를 건너뛴다.
        crisis_block = build_crisis_suffix(ops_facts)
        # `config.prompt_sha8` 은 봇 **저장값**이고, 여기 `prompt_sha8` 이 실제로 모델에
        # 간 **실효 프롬프트**다. 둘이 다르면 overlay 가 붙었다는 뜻이다.
        turn.stage(
            OPS_FACTS,
            "overlay" if ops_facts else "none",
            n=len(ops_facts),
            kinds=sorted({f.kind for f in ops_facts}) or None,
            term_rules=len(ops_term_rules) or None,
            prompt_sha8=prompt_sha8(effective_system_prompt),
            prompt_len=len(effective_system_prompt),
        )

        # 2. (분기) RAG 처리
        # bot.use_rag 로 봇 단위 토글 제공 — file_search store가 비어있는 봇은 admin에서 False로
        # 설정해 매 요청 7-12s의 빈 retrieval 호출을 차단한다. request.use_rag와 AND 평가.
        effective_use_rag = request.use_rag and bot.use_rag
        if effective_use_rag:
            rag_service = get_rag_service(provider=bot.llm_model)
            # 인스턴스 캐시 검증: store_cached=False면 매 요청 ensure_store가 외부 API를 호출 중.
            logger.info(
                "rag instance id=%s provider=%s store_cached=%s",
                id(rag_service),
                bot.llm_model,
                bool(getattr(rag_service, "_store_resource_name", None)),
            )

            # 근거 조달 방식. lexical/both 는 **비스트리밍 전용**이다 — answer_with_wiki 에
            # 스트리밍 경로가 없고, 팔 F 도 앞선 턴을 조립한 뒤 한 번에 생성한다.
            # 그래서 두 스트림 분기를 file_search 일 때로 한정하고, 나머지는 아래 else 로 떨어진다.
            retrieval_mode = _effective_retrieval_mode(bot)
            stream_ok = request.stream and retrieval_mode == "file_search"

            if stream_ok and bot.evidence_policy_mode == "strict":
                return StreamingResponse(
                    self._generate_strict_rag_stream(
                        rag_service,
                        request,
                        bot,
                        chat_session,
                        history,
                        system_prompt=effective_system_prompt,
                    ),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no",
                    },
                )
            if stream_ok:
                return StreamingResponse(
                    self._generate_rag_stream(
                        rag_service,
                        request,
                        bot,
                        chat_session,
                        history,
                        system_prompt=effective_system_prompt,
                    ),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no",
                    },
                )
            else:
                rag_response, trace = await self._retrieve_and_generate(
                    retrieval_mode,
                    rag_service,
                    bot,
                    request.message,
                    effective_system_prompt,
                    history,
                )
                # 무엇을 근거로 들고 생성까지 갔나. **원문은 넣지 않는다** — 참조만(규칙 1).
                turn.stage(
                    RETRIEVAL,
                    "fallback" if trace.reasons else retrieval_mode,
                    mode=retrieval_mode,
                    units=len(trace.units) or None,
                    unit_refs=unit_refs(trace.units) or None,
                    # 위키 채널. `unit_refs` 만 남기면 「모델이 본 근거」를 절반만 적는 것이라
                    # 정확한 인용이 지어냄으로 집계된다.
                    pages=list(trace.pages) or None,
                    page_srcs=list(trace.page_src_ids) or None,
                    reasons=list(trace.reasons) or None,
                    answer_len=len((rag_response.answer or "").strip()),
                    citations=len(rag_response.citations),
                    # file_search·both 의 strict 게이트는 `has_direct_citation` 을 본다.
                    # 그 판정을 **나중에 오프라인으로 재현**하려면 근사 백필이 아닌 인용이
                    # 있었는지가 남아야 한다. 개수만으로는 못 푼다.
                    direct_citation=has_direct_citation(rag_response.citations),
                    history_turns=len(history) or None,
                )

                strict_on = bot.evidence_policy_mode == "strict"
                # 차단되면 답변이 고정 문구로 갈리므로 **판정 전에** 표기를 떠 둔다.
                # `fabricated` 도 여기서 떠야 한다 — 뒤에서 계산하면 고정 문구를 재게 된다.
                cited = sorted(cited_ids(rag_response.answer))
                # 게이트와 **같은 목록**으로 재야 기록과 판정이 어긋나지 않는다.
                evidence = trace.evidence_units
                # ⚠ **「지어냄 0」과 「안 쟀음」은 다르다.** 두 자 모두 대조 목록이 비면
                # 빈 값을 돌려준다 — 그걸 0으로 읽어서 「이 경로는 안전하다」고 집계한 적이
                # 있다. 무보호가 아니라 무측정이라는 것을 `fabricated_checked` 로 남긴다.
                if _uses_grounding_ruler(retrieval_mode, trace):
                    # file_search·both·fs_fusion·폴백 — grounding 청크(+ 융합이 얹은 위키
                    # 원문)가 대조 목록이다. id 표기는 이 경로에 주입 라벨이 없어 안 잰다.
                    fake_ids = set()
                    fake_loc = fabricated_vs_grounding(
                        rag_response.answer, rag_response.citations, evidence
                    )
                    fabricated_checked = bool(
                        grounding_locators(rag_response.citations, evidence)
                    )
                else:
                    fake_ids, fake_loc = fabricated_citations(rag_response.answer, evidence)
                    fabricated_checked = bool(evidence)
                strict_blocked = strict_on and _strict_blocks(
                    retrieval_mode, trace, rag_response, crisis_active=bool(crisis_block)
                )
                if strict_blocked:
                    logger.info("strict response blocked: no direct citation bot_id=%s", bot.id)
                    rag_response.answer = STRICT_EVIDENCE_MESSAGE
                    rag_response.citations = []
                    rag_response.followups = []
                # 게이트가 무엇을 보고 막았나. `cited` 는 답변이 **표기한** 근거고
                # `unit_refs`(위 단계)가 **주입한** 근거다 — 이 둘의 대조가 판정 그 자체다.
                # 무엇을 지어냈는지 남긴다. 「막혔다」만 남기면 관리자가 원인을 못 푼다.
                # legacy 봇에서도 기록한다 — 게이트를 켜기 전에 얼마나 새는지 보려면 필요하다.
                turn.stage(
                    STRICT,
                    "blocked" if strict_blocked else ("pass" if strict_on else "off"),
                    cited=cited or None,
                    fabricated=sorted(fake_ids) or None,
                    fabricated_loc=[f"{k}{n}" for k, n in sorted(fake_loc)] or None,
                    # False 면 위 둘이 「없음」이 아니라 「안 쟀음」이다. 집계에서 갈라라.
                    fabricated_checked=fabricated_checked,
                )

                # 기계 id 표기를 벗긴다. **strict 게이트보다 뒤여야 한다** — 게이트가 그
                # 표기를 주입 목록과 대조하므로(`has_grounded_citation`) 먼저 지우면
                # strict 봇이 전부 차단된다. `create_message` 보다는 앞이어야 한다 —
                # DB 에 남으면 새로고침 때 다시 보인다.
                before_strip = len(rag_response.answer or "")
                rag_response.answer = strip_source_markers(rag_response.answer)
                strip_source_markers_from_citations(rag_response.citations)
                turn.stage(
                    STRIP,
                    "stripped" if len(rag_response.answer or "") != before_strip else "none",
                    removed_chars=before_strip - len(rag_response.answer or "") or None,
                )

                # ── 1층. 결정론 게이트 ──
                # 사용자에게 문구가 나가는 조건은 **이것 하나뿐**이다. 지금은 빈 말풍선이
                # 그대로 나가므로 치환해도 과잉 거절 위험이 0이다.
                # 인용 0건은 쓰지 않는다 — 인용 0 ≠ RAG 미작동이고, 어휘 경로에서는
                # `_citations()` 가 주입 유닛마다 인용을 만들어 애초에 안 걸린다.
                if not (rag_response.answer or "").strip():
                    logger.info("빈 답변 — 고정 문구로 치환 bot_id=%s", bot.id)
                    rag_response.answer = UNANSWERED_MESSAGE
                    rag_response.citations = []
                    rag_response.followups = []
                    trace.mark(Reason.EMPTY_ANSWER)
                elif is_self_refusal(rag_response.answer):
                    # 봇이 스스로 못 답한다고 말했다. **답변은 안 건드린다** — 프롬프트가
                    # 시킨 그 문구가 맞다. 관찰만 남겨 관리자 화면을 채운다.
                    trace.mark(Reason.SELF_REFUSAL)
                # 사용자에게 나가는 문구가 여기서 갈린다. 「유보율」의 분자가 이 단계다.
                turn.stage(
                    UNANSWERED,
                    "replaced" if Reason.EMPTY_ANSWER in trace.reasons
                    else ("self_refusal" if Reason.SELF_REFUSAL in trace.reasons else "none"),
                )

                # 표기 통일 — 프롬프트로는 안 지켜지는 것이 실측돼(FINDINGS §2-4) 코드로 바꾼다.
                # 인용의 segments 도 같이 바꿔야 한다. 프론트가 본문에서 segment 를 문자열
                # 검색해 각주를 앵커하므로(citationMarkers.ts), 본문만 바꾸면 각주가 전부 빠진다.
                before_term = rag_response.answer
                if ops_term_rules:
                    rag_response.answer = apply_term_rules(rag_response.answer, ops_term_rules)
                    apply_term_rules_to_citations(rag_response.citations, ops_term_rules)
                turn.stage(
                    TERM,
                    "applied" if rag_response.answer != before_term else "none",
                    rules=len(ops_term_rules) or None,
                )

                # 위기 안내 — **표기 치환 뒤**여야 한다. 운영자가 승인한 문안이 한 글자도
                # 안 바뀌고 나가야 하는데, 앞에 두면 term 규칙이 번호나 기관명을 건드린다.
                if crisis_block:
                    rag_response.answer, crisis_decision = _attach_crisis(
                        rag_response.answer, crisis_block
                    )
                    # 후속질문은 위기 턴에서 **언제나** 뗀다. 「더 궁금한 것」을 되묻는
                    # 자리가 아니다. 인용은 교체했을 때만 뗀다 — 덧붙인 경우에는 모델이
                    # 쓴 앞부분에 여전히 붙어 있어야 각주가 맞는다.
                    rag_response.followups = []
                    if crisis_decision == "replaced":
                        rag_response.citations = []
                    # 블록 **본문은 남기지 않는다** — trace 규칙 1(원문 금지).
                    turn.stage(CRISIS, crisis_decision, block_len=len(crisis_block))

                # 기록은 아래 `_record_unanswered` 가 하지만, 무엇을 남길지는 여기서 이미
                # 정해져 있다. 메시지 INSERT 한 번에 trace 를 얹으려고 미리 닫는다.
                turn.stage(
                    RECORD,
                    "recorded" if trace.reasons else "none",
                    reasons=list(trace.reasons) or None,
                )

                assistant_msg = await crud_chat.create_message(
                    session=self.session,
                    session_id=chat_session.id,
                    role=MessageRole.ASSISTANT,
                    content=rag_response.answer,
                    citations=[c.model_dump() for c in rag_response.citations],
                    followups=rag_response.followups,
                    trace=turn.to_json(),
                )
                chat_session.updated_at = datetime.now(timezone.utc)

                # ── 3층. 관찰된 것을 남긴다 (어시스턴트 메시지와 같은 트랜잭션) ──
                # **위기 턴은 안 남긴다.** 검색이 빈손이라 `reasons` 에 `lexical_empty` 가
                # 붙지만 그건 「자료가 없어서 못 답했다」가 아니다 — 위기 안내는 규정집으로
                # 메울 수 있는 결손이 아니고, 우리는 제대로 답했다. 남기면 (a) 유보 집계에
                # 섞이고 (b) STEP 3 의 자료 보강 목록에 「죽고 싶어요」가 doc_gap 후보로 올라온다.
                if not crisis_block:
                    await _record_unanswered(
                        self.session,
                        bot=bot,
                        chat_session=chat_session,
                        message_id=assistant_msg.id,
                        question=request.message,
                        reasons=trace.reasons,
                        detail={
                            "retrieval_mode": retrieval_mode,
                            "src_ids": [u.src_id for u in trace.units],
                        },
                    )
                await self.session.commit()

                # 메인 답변 경로(persona)가 인용을 못 남기면 interactions 로 근사 인용을 비동기 백필.
                # 인용이 이미 붙었으면 근거 구절만 따로 채운다 — 어느 쪽이든 응답은 막지 않는다.
                #
                # **위기 턴은 둘 다 안 돈다.** 자살 신호 답변에 근거 인용을 지어내 붙이려는
                # 호출이라 뜻이 없고, 배경 LLM 호출이 하나 더 나가 요청률이 2배가 된다.
                if not crisis_block:
                    if not rag_response.citations and bot.evidence_policy_mode != "strict":
                        _schedule_citation_backfill(
                            bot_id=bot.id,
                            model_name=bot.llm_model,
                            system_prompt=effective_system_prompt,
                            message_id=assistant_msg.id,
                            prompt=request.message,
                            answer=rag_response.answer,
                        )
                    else:
                        _schedule_evidence_fill(
                            model_name=bot.llm_model,
                            message_id=assistant_msg.id,
                            citations=[c.model_dump() for c in rag_response.citations],
                            answer=rag_response.answer,
                        )

                # followups 는 RAG 호출(rag_service.generate_with_rag) 1회 안에서 같이 받음.
                # 별도 LLM call(followup_service) 을 제거해 wall-time/비용 절반 + timeout 사고 차단.
                return ChatCompletionResponse(
                    session_id=chat_session.id,
                    content=rag_response.answer,
                    bot_id=bot.id,
                    citations=rag_response.citations,
                    source="rag",
                    followups=rag_response.followups,
                )

        if bot.evidence_policy_mode == "strict":
            # strict 봇은 RAG가 비활성화된 요청으로 사실 답변을 만들지 않는다.
            content = STRICT_EVIDENCE_MESSAGE
            turn.stage(STRICT, "blocked", reason="rag_disabled")
            # 위기 턴이면 고정 문구 대신 안전 안내를 낸다. RAG 를 껐다는 이유로
            # 자살 신호에 「답변해 드릴 수 없습니다」를 내보내면 안 된다.
            if crisis_block:
                content, crisis_decision = _attach_crisis(content, crisis_block)
                turn.stage(CRISIS, crisis_decision, block_len=len(crisis_block))
            await crud_chat.create_message(
                session=self.session,
                session_id=chat_session.id,
                role=MessageRole.ASSISTANT,
                content=content,
                trace=turn.to_json(),
            )
            chat_session.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            return ChatCompletionResponse(
                session_id=chat_session.id,
                content=content,
                bot_id=bot.id,
                source="policy_block",
            )

        # 3. 일반 LLM 처리
        llm_service = get_llm_service(bot.llm_model)

        if request.stream:
            return StreamingResponse(
                self._generate_llm_stream(
                    llm_service,
                    request,
                    bot,
                    chat_session,
                    history,
                    system_prompt=effective_system_prompt,
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            content = await llm_service.generate(
                prompt=request.message,
                system_prompt=effective_system_prompt,
                history=history or None,
            )
            before_term = content
            content = apply_term_rules(content, ops_term_rules)
            # RAG 를 안 탄 경로다 — 근거 없이 생성만 했다는 사실 자체가 기록돼야 한다.
            turn.stage(RETRIEVAL, "skipped", reason="use_rag=false")
            turn.stage(
                TERM,
                "applied" if content != before_term else "none",
                rules=len(ops_term_rules) or None,
            )

            # 위기 안내 — RAG 경로와 같은 규약(표기 치환 뒤, 저장 앞).
            if crisis_block:
                content, crisis_decision = _attach_crisis(content, crisis_block)
                turn.stage(CRISIS, crisis_decision, block_len=len(crisis_block))

            # followups 를 먼저 생성해 메시지에 함께 영속화 (관리자 상세에서 후속질문 표시).
            # 위기 턴에서는 만들지 않는다 — 「더 궁금한 것」을 되묻는 자리가 아니다.
            followups = [] if crisis_block else await generate_followups(request.message, content)

            await crud_chat.create_message(
                session=self.session,
                session_id=chat_session.id,
                role=MessageRole.ASSISTANT,
                content=content,
                followups=followups,
                trace=turn.to_json(),
            )
            chat_session.updated_at = datetime.now(timezone.utc)
            await self.session.commit()

            return ChatCompletionResponse(
                session_id=chat_session.id,
                content=content,
                bot_id=bot.id,
                source="llm",
                followups=followups,
            )

    async def _generate_strict_rag_stream(
        self, rag_service, request, bot, chat_session, history=None, system_prompt=None
    ):
        """strict 봇의 SSE 경로.

        Gemini가 grounding을 응답 마지막에만 주므로, 본문을 먼저 흘리면 근거 정책을
        되돌릴 수 없다. 이 경로는 검증 뒤 하나의 청크로 전송한다.
        """
        sp = system_prompt if system_prompt is not None else (bot.system_prompt or "")
        try:
            meta_data = json.dumps({"session_id": chat_session.id}, ensure_ascii=False)
            yield f"data: {meta_data}\n\n"

            response = await rag_service.generate_with_rag(
                bot_id=bot.id,
                prompt=request.message,
                system_prompt=sp,
                model_name=bot.llm_model,
                history=history or None,
            )
            if has_direct_citation(response.citations):
                content = response.answer
                citations = [c.model_dump() for c in response.citations]
                followups = response.followups
            else:
                logger.info("strict stream blocked: no direct citation bot_id=%s", bot.id)
                content = STRICT_EVIDENCE_MESSAGE
                citations = []
                followups = []

            assistant_msg = await crud_chat.create_message(
                session=self.session,
                session_id=chat_session.id,
                role=MessageRole.ASSISTANT,
                content=content,
                citations=citations,
                followups=followups or None,
            )
            chat_session.updated_at = datetime.now(timezone.utc)
            await self.session.commit()

            yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
            if followups:
                payload = json.dumps(
                    {"type": "followups", "message_id": assistant_msg.id, "items": followups},
                    ensure_ascii=False,
                )
                yield f"data: {payload}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error("strict RAG 스트리밍 오류: %s", e)
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    async def _generate_rag_stream(
        self, rag_service, request, bot, chat_session, history=None, system_prompt=None
    ):
        sp = system_prompt if system_prompt is not None else (bot.system_prompt or "")
        full_response_content = ""
        try:
            meta_data = json.dumps({"session_id": chat_session.id}, ensure_ascii=False)
            yield f"data: {meta_data}\n\n"

            captured_citations: list | None = None
            async for chunk in rag_service.generate_stream_with_rag(
                bot_id=bot.id,
                prompt=request.message,
                system_prompt=sp,
                model_name=bot.llm_model,
                history=history or None,
            ):
                # 본문은 str, 스트림 종료 시 인용 메타데이터는 dict 로 1회 전달된다.
                # 인용은 DB 저장만 하고 클라이언트 SSE 와이어 포맷은 기존 그대로 유지한다.
                if isinstance(chunk, dict):
                    captured_citations = chunk.get("citations")
                    continue
                full_response_content += chunk
                data = json.dumps({"content": chunk}, ensure_ascii=False)
                yield f"data: {data}\n\n"

            # 후속 질문 생성 (silent on failure) — 메시지에 함께 영속화하기 위해 commit 전에 생성
            followups = await generate_followups(request.message, full_response_content)

            # 스트리밍 완료 후 1회 commit → message_id 확보 (인용/후속 함께 저장)
            assistant_msg = await crud_chat.create_message(
                session=self.session,
                session_id=chat_session.id,
                role=MessageRole.ASSISTANT,
                content=full_response_content,
                citations=captured_citations,
                followups=followups or None,
            )
            chat_session.updated_at = datetime.now(timezone.utc)
            await self.session.commit()

            # 스트림 grounding 이 인용을 못 남기면 interactions 로 근사 인용을 비동기 백필.
            # 인용이 이미 붙었으면 근거 구절만 따로 채운다 — 어느 쪽이든 스트림은 막지 않는다.
            if not captured_citations:
                _schedule_citation_backfill(
                    bot_id=bot.id,
                    model_name=bot.llm_model,
                    system_prompt=sp,
                    message_id=assistant_msg.id,
                    prompt=request.message,
                    answer=full_response_content,
                )
            else:
                _schedule_evidence_fill(
                    model_name=bot.llm_model,
                    message_id=assistant_msg.id,
                    citations=captured_citations,
                    answer=full_response_content,
                )

            if followups:
                payload = json.dumps(
                    {"type": "followups", "message_id": assistant_msg.id, "items": followups},
                    ensure_ascii=False,
                )
                yield f"data: {payload}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"RAG 스트리밍 오류: {e}")
            error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    async def _generate_llm_stream(
        self, llm_service, request, bot, chat_session, history=None, system_prompt=None
    ):
        sp = system_prompt if system_prompt is not None else (bot.system_prompt or "")
        full_response_content = ""
        try:
            # 클라이언트에게 활성화된 session_id를 가장 먼저 알려줌 (새로고침/리다이렉트 용도)
            meta_data = json.dumps({"session_id": chat_session.id}, ensure_ascii=False)
            yield f"data: {meta_data}\n\n"

            async for chunk in llm_service.generate_stream(
                prompt=request.message,
                system_prompt=sp,
                history=history or None,
            ):
                full_response_content += chunk
                data = json.dumps({"content": chunk}, ensure_ascii=False)
                yield f"data: {data}\n\n"

            # 스트리밍 정상 종료 후 1회 DB 기록 & updated_at 갱신 → message_id 확보
            assistant_msg = await crud_chat.create_message(
                session=self.session,
                session_id=chat_session.id,
                role=MessageRole.ASSISTANT,
                content=full_response_content,
            )
            chat_session.updated_at = datetime.now(timezone.utc)
            await self.session.commit()

            # 후속 질문 생성 (silent on failure)
            followups = await generate_followups(request.message, full_response_content)
            if followups:
                payload = json.dumps(
                    {"type": "followups", "message_id": assistant_msg.id, "items": followups},
                    ensure_ascii=False,
                )
                yield f"data: {payload}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"스트리밍 오류: {e}")
            error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
            # 주의: 오류 발생 시 불완전한 메시지는 저장하지 않음 (롤백 처리됨)
