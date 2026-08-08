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
from app.services.faq_service import search_faq_override
from app.services.followup_service import generate_followups
from app.services.llm.factory import get_llm_service
from app.services.ops_facts_service import (
    apply_term_rules,
    apply_term_rules_to_citations,
    build_prompt_overlay,
    load_runtime_facts,
    term_rules,
)
from app.services.rag.factory import get_rag_service
from app.services.strict_mode import (
    STRICT_EVIDENCE_MESSAGE,
    has_direct_citation,
    is_refusal_faq,
)

logger = logging.getLogger(__name__)

# 어휘 검색(BM25 원문 주입)은 Gemini 클라이언트를 직접 만든다. 다른 프로바이더 봇에서 켜면
# 조용히 깨지므로 file_search 로 되돌린다.
_LEXICAL_PROVIDER_PREFIX = "gemini"


def _effective_retrieval_mode(bot: Bot) -> str:
    """봇 설정을 실제로 탈 수 있는 조달 방식으로 바꾼다.

    미설정(기존 봇)은 `file_search` 다 — 컬럼 server_default 와 같아서 **기존 동작과 동일**하다.
    """
    mode = getattr(bot, "retrieval_mode", None) or "file_search"
    if mode not in ("file_search", "lexical", "both"):
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
    ):
        """근거를 무엇으로 조달할지 하나만 가른다. 돌려주는 것은 세 경우 모두 `RAGResponse` 다.

        그래서 이 뒤의 처리(strict 게이트 · 용어 치환 · 메시지 저장 · 근거 형광펜 · 응답)는
        한 줄도 바뀌지 않는다. 프론트엔드도 손댈 필요가 없다.

        `file_search` 는 **기존 호출을 인자까지 그대로** 유지한다 — 기본값 봇이 지금과
        한 글자도 달라지면 안 된다(`tests/test_retrieval_mode.py` 가 인자를 통째로 비교한다).
        """
        from app.services.wiki.store import WikiCorpusUnavailable

        if retrieval_mode == "lexical":
            # 팔 B′ — file_search 를 아예 부르지 않고 BM25 원문만 준다. 1.6초.
            from app.services.wiki.service import answer_with_wiki

            try:
                rag_response, _ = await answer_with_wiki(
                    bot_id=bot.id,
                    question=message,
                    system_prompt=system_prompt,
                    model_name=bot.llm_model,
                    history=history or None,
                    context_mode="raw_budget",
                )
            except WikiCorpusUnavailable as e:
                logger.warning("어휘 검색 코퍼스 없음 bot_id=%s — file_search 로 폴백: %s", bot.id, e)
            else:
                # 어휘 검색은 동의어·구어체 질문에서 빈손이 될 수 있다(핸드오프 §5 #13).
                # 그때 answer_with_wiki 는 빈 답변을 돌려주는데, 빈 답변을 그대로 내보내면
                # 사용자에게는 그냥 고장이다. 의미 검색으로 되돌린다.
                if (rag_response.answer or "").strip():
                    # followups 는 비어 있다(file_search 경로는 공짜로 받는다). 카카오가
                    # 이것을 쓰므로 알려진 회귀다 — 지연이 이 모드의 값어치라 추가 호출로 메우지 않는다.
                    return rag_response
                logger.info("어휘 검색 결과 없음 bot_id=%s — file_search 로 폴백", bot.id)

        elif retrieval_mode == "both":
            # 팔 F — file_search 는 그대로 두고 BM25 원문을 앞선 턴으로 얹는다. 6.1초.
            from app.services.wiki.service import build_hybrid_turns

            try:
                extra = await build_hybrid_turns(bot.id, message)
            except WikiCorpusUnavailable as e:
                logger.warning("하이브리드 코퍼스 없음 bot_id=%s — file_search 로 폴백: %s", bot.id, e)
                extra = []
            merged = (extra + list(history)) if history else extra
            return await rag_service.generate_with_rag(
                bot_id=bot.id,
                prompt=message,
                system_prompt=system_prompt,
                model_name=bot.llm_model,
                history=merged or None,
            )

        return await rag_service.generate_with_rag(
            bot_id=bot.id,
            prompt=message,
            system_prompt=system_prompt,
            model_name=bot.llm_model,
            history=history or None,
        )

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

        # 1. FAQ Override 검색 (시맨틱 라우팅)
        faq_match = await search_faq_override(
            session=self.session,
            bot_id=bot.id,
            query_text=request.message,
        )

        if faq_match:
            # FAQ는 strict 봇의 명시적인 거절 안내에만 사용한다.
            faq_content = faq_match.answer
            faq_source = "faq_override"
            if bot.evidence_policy_mode == "strict" and not is_refusal_faq(faq_content):
                logger.warning("strict FAQ blocked: faq_id=%s", faq_match.faq_id)
                faq_content = STRICT_EVIDENCE_MESSAGE
                faq_source = "policy_block"

            await crud_chat.create_message(
                session=self.session,
                session_id=chat_session.id,
                role=MessageRole.ASSISTANT,
                content=faq_content,
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
        ops_facts = await load_runtime_facts(self.session, bot, request.message)
        effective_system_prompt = (bot.system_prompt or "") + build_prompt_overlay(ops_facts)
        ops_term_rules = term_rules(ops_facts)

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
                rag_response = await self._retrieve_and_generate(
                    retrieval_mode,
                    rag_service,
                    bot,
                    request.message,
                    effective_system_prompt,
                    history,
                )
                if (
                    bot.evidence_policy_mode == "strict"
                    and not has_direct_citation(rag_response.citations)
                ):
                    logger.info("strict response blocked: no direct citation bot_id=%s", bot.id)
                    rag_response.answer = STRICT_EVIDENCE_MESSAGE
                    rag_response.citations = []
                    rag_response.followups = []

                # 표기 통일 — 프롬프트로는 안 지켜지는 것이 실측돼(FINDINGS §2-4) 코드로 바꾼다.
                # 인용의 segments 도 같이 바꿔야 한다. 프론트가 본문에서 segment 를 문자열
                # 검색해 각주를 앵커하므로(citationMarkers.ts), 본문만 바꾸면 각주가 전부 빠진다.
                if ops_term_rules:
                    rag_response.answer = apply_term_rules(rag_response.answer, ops_term_rules)
                    apply_term_rules_to_citations(rag_response.citations, ops_term_rules)

                assistant_msg = await crud_chat.create_message(
                    session=self.session,
                    session_id=chat_session.id,
                    role=MessageRole.ASSISTANT,
                    content=rag_response.answer,
                    citations=[c.model_dump() for c in rag_response.citations],
                    followups=rag_response.followups,
                )
                chat_session.updated_at = datetime.now(timezone.utc)
                await self.session.commit()

                # 메인 답변 경로(persona)가 인용을 못 남기면 interactions 로 근사 인용을 비동기 백필.
                # 인용이 이미 붙었으면 근거 구절만 따로 채운다 — 어느 쪽이든 응답은 막지 않는다.
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
            await crud_chat.create_message(
                session=self.session,
                session_id=chat_session.id,
                role=MessageRole.ASSISTANT,
                content=content,
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
            content = apply_term_rules(content, ops_term_rules)

            # followups 를 먼저 생성해 메시지에 함께 영속화 (관리자 상세에서 후속질문 표시).
            followups = await generate_followups(request.message, content)

            await crud_chat.create_message(
                session=self.session,
                session_id=chat_session.id,
                role=MessageRole.ASSISTANT,
                content=content,
                followups=followups,
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
