"""
채팅 비즈니스 로직을 처리하는 서비스 계층.
컨트롤러(chat.py)에서 넘겨받은 요청을 기반으로 FAQ, RAG, 일반 LLM 분기 처리를 수행하고,
정상 스트리밍 및 Non-Streaming 응답을 책임집니다.
"""

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
from app.services.crisis_service import (
    BLOCKED_FALLBACK_MESSAGE,
    detect_crisis_signal,
    strip_phone_sentences,
)
from app.services.faq_service import search_faq_override
from app.services.followup_service import generate_followups
from app.services.llm.factory import get_llm_service
from app.services.rag.factory import get_rag_service

logger = logging.getLogger(__name__)

# 스트리밍 중 예기치 못한 예외를 사용자에게 노출하지 않기 위한 고정 안내 (raw str(e) 대체).
_GENERIC_STREAM_ERROR_MESSAGE = (
    "죄송합니다. 일시적인 오류로 답변을 생성하지 못했어요. 잠시 후 다시 시도해 주세요."
)


class ChatService:
    def __init__(self, session: AsyncSession):
        self.session = session

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

        # 위기 후보 신호 감지 — 자동 차단이 아니라 per-turn 지시문 주입/번호 필터의 트리거.
        crisis_keyword = detect_crisis_signal(request.message)
        if crisis_keyword:
            logger.warning(
                "crisis signal detected — session_id=%s bot_id=%s keyword=%s",
                chat_session.id,
                bot.id,
                crisis_keyword,
            )

        # 1. FAQ Override 검색 (시맨틱 라우팅)
        # 위기 신호 턴은 FAQ 캔드 답변으로 빠지지 않게 스킵 (생성형 위기 대응 보장).
        faq_match = (
            None
            if crisis_keyword
            else await search_faq_override(
                session=self.session,
                bot_id=bot.id,
                query_text=request.message,
            )
        )

        if faq_match:
            # FAQ 매칭 성공 → LLM 호출 없이 즉시 응답 (비용 절약 + 환각 방지)
            await crud_chat.create_message(
                session=self.session,
                session_id=chat_session.id,
                role=MessageRole.ASSISTANT,
                content=faq_match.answer,
            )
            chat_session.updated_at = datetime.now(timezone.utc)
            await self.session.commit()

            logger.info(
                f"FAQ Override 응답: faq_id={faq_match.faq_id}, "
                f"similarity={faq_match.similarity}"
            )

            return ChatCompletionResponse(
                session_id=chat_session.id,
                content=faq_match.answer,
                bot_id=bot.id,
                source="faq_override",
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

        # 위기 대응 지시는 봇 시스템 프롬프트 본문(위기 섹션)으로 이관됨 — 코드 주입 없음.
        # crisis_keyword 는 FAQ 스킵·번호 필터(strip)·로깅 트리거로만 쓴다.
        effective_system_prompt = bot.system_prompt

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

            if request.stream:
                return StreamingResponse(
                    self._generate_rag_stream(
                        rag_service,
                        request,
                        bot,
                        chat_session,
                        history,
                        system_prompt=effective_system_prompt,
                        crisis_keyword=crisis_keyword,
                    ),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no",
                    },
                )
            else:
                rag_response = await rag_service.generate_with_rag(
                    bot_id=bot.id,
                    prompt=request.message,
                    system_prompt=effective_system_prompt,
                    model_name=bot.llm_model,
                    history=history or None,
                )

                # 빈 응답 = 세이프티 차단(H25) → 검수 고정문으로 폴백.
                if not rag_response.answer.strip():
                    logger.warning("RAG 빈 응답(차단 추정) — session_id=%s", chat_session.id)
                    return await self._blocked_fallback_response(bot, chat_session)

                # 위기 턴은 환각 번호 방어를 위해 본문에서 전화번호 문장을 제거 후 저장/응답.
                answer = (
                    strip_phone_sentences(rag_response.answer)[0]
                    if crisis_keyword
                    else rag_response.answer
                )

                await crud_chat.create_message(
                    session=self.session,
                    session_id=chat_session.id,
                    role=MessageRole.ASSISTANT,
                    content=answer,
                    citations=[c.model_dump() for c in rag_response.citations],
                    followups=rag_response.followups,
                )
                chat_session.updated_at = datetime.now(timezone.utc)
                await self.session.commit()

                # followups 는 RAG 호출(rag_service.generate_with_rag) 1회 안에서 같이 받음.
                # 별도 LLM call(followup_service) 을 제거해 wall-time/비용 절반 + timeout 사고 차단.
                return ChatCompletionResponse(
                    session_id=chat_session.id,
                    content=answer,
                    bot_id=bot.id,
                    citations=rag_response.citations,
                    source="rag",
                    followups=rag_response.followups,
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
                    crisis_keyword=crisis_keyword,
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

            # 빈 응답 = 세이프티 차단 → 검수 고정문으로 폴백.
            if not content.strip():
                logger.warning("LLM 빈 응답(차단 추정) — session_id=%s", chat_session.id)
                return await self._blocked_fallback_response(bot, chat_session)

            # 위기 턴은 환각 번호 방어를 위해 본문에서 전화번호 문장을 제거 후 저장/응답.
            if crisis_keyword:
                content = strip_phone_sentences(content)[0]

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

    async def _generate_rag_stream(
        self,
        rag_service,
        request,
        bot,
        chat_session,
        history=None,
        system_prompt: str | None = None,
        crisis_keyword: str | None = None,
    ):
        # system_prompt 미지정(레거시 호출) 시 봇 기본값 — 기존 테스트 호환.
        effective_system_prompt = system_prompt if system_prompt is not None else bot.system_prompt
        full_response_content = ""
        sent_content = ""  # 와이어로 이미 내보낸 텍스트 (차단 시 DB 이어붙임 기준)
        try:
            meta_data = json.dumps({"session_id": chat_session.id}, ensure_ascii=False)
            yield f"data: {meta_data}\n\n"

            captured_citations: list | None = None
            async for chunk in rag_service.generate_stream_with_rag(
                bot_id=bot.id,
                prompt=request.message,
                system_prompt=effective_system_prompt,
                model_name=bot.llm_model,
                history=history or None,
            ):
                # 본문은 str, 스트림 종료 시 인용 메타데이터는 dict 로 1회 전달된다.
                if isinstance(chunk, dict):
                    captured_citations = chunk.get("citations")
                    continue
                full_response_content += chunk
                # 위기 턴은 번호 필터를 위해 버퍼링만 하고, 일반 턴은 청크 즉시 방출.
                if not crisis_keyword:
                    sent_content += chunk
                    data = json.dumps({"content": chunk}, ensure_ascii=False)
                    yield f"data: {data}\n\n"

            # 빈 스트림 = 세이프티 차단 → 검수 고정문으로 폴백.
            if not full_response_content.strip():
                logger.warning("RAG 스트림 빈 응답(차단 추정) — session_id=%s", chat_session.id)
                async for sse in self._yield_blocked_fallback(chat_session, sent_content):
                    yield sse
                return

            # 위기 턴: 누적 본문에서 전화번호 문장 제거 후 content 이벤트 1회로 방출.
            if crisis_keyword:
                full_response_content = strip_phone_sentences(full_response_content)[0]
                sent_content = full_response_content
                data = json.dumps({"content": full_response_content}, ensure_ascii=False)
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

            # 인용(citations)을 SSE 와이어에도 실어 보낸다 — 비스트리밍 응답과 동일한 출처 노출.
            if captured_citations:
                payload = json.dumps(
                    {"type": "citations", "message_id": assistant_msg.id, "items": captured_citations},
                    ensure_ascii=False,
                )
                yield f"data: {payload}\n\n"

            if followups:
                payload = json.dumps(
                    {"type": "followups", "message_id": assistant_msg.id, "items": followups},
                    ensure_ascii=False,
                )
                yield f"data: {payload}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error("RAG 스트리밍 오류: %s", e, exc_info=True)
            error_data = json.dumps({"error": _GENERIC_STREAM_ERROR_MESSAGE}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    async def _generate_llm_stream(
        self,
        llm_service,
        request,
        bot,
        chat_session,
        history=None,
        system_prompt: str | None = None,
        crisis_keyword: str | None = None,
    ):
        effective_system_prompt = system_prompt if system_prompt is not None else bot.system_prompt
        full_response_content = ""
        sent_content = ""
        try:
            # 클라이언트에게 활성화된 session_id를 가장 먼저 알려줌 (새로고침/리다이렉트 용도)
            meta_data = json.dumps({"session_id": chat_session.id}, ensure_ascii=False)
            yield f"data: {meta_data}\n\n"

            async for chunk in llm_service.generate_stream(
                prompt=request.message,
                system_prompt=effective_system_prompt,
                history=history or None,
            ):
                full_response_content += chunk
                if not crisis_keyword:
                    sent_content += chunk
                    data = json.dumps({"content": chunk}, ensure_ascii=False)
                    yield f"data: {data}\n\n"

            # 빈 스트림 = 세이프티 차단 → 검수 고정문으로 폴백.
            if not full_response_content.strip():
                logger.warning("LLM 스트림 빈 응답(차단 추정) — session_id=%s", chat_session.id)
                async for sse in self._yield_blocked_fallback(chat_session, sent_content):
                    yield sse
                return

            # 위기 턴: 누적 본문에서 전화번호 문장 제거 후 content 이벤트 1회로 방출.
            if crisis_keyword:
                full_response_content = strip_phone_sentences(full_response_content)[0]
                sent_content = full_response_content
                data = json.dumps({"content": full_response_content}, ensure_ascii=False)
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
            logger.error("스트리밍 오류: %s", e, exc_info=True)
            error_data = json.dumps({"error": _GENERIC_STREAM_ERROR_MESSAGE}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
            # 주의: 오류 발생 시 불완전한 메시지는 저장하지 않음 (롤백 처리됨)

    async def _blocked_fallback_response(
        self, bot: Bot, chat_session: ChatSession
    ) -> ChatCompletionResponse:
        """세이프티 차단 시 검수 고정문을 assistant 메시지로 저장·commit 후 반환 (비스트리밍)."""
        await crud_chat.create_message(
            session=self.session,
            session_id=chat_session.id,
            role=MessageRole.ASSISTANT,
            content=BLOCKED_FALLBACK_MESSAGE,
        )
        chat_session.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        return ChatCompletionResponse(
            session_id=chat_session.id,
            content=BLOCKED_FALLBACK_MESSAGE,
            bot_id=bot.id,
            source="blocked_fallback",
        )

    async def _yield_blocked_fallback(self, chat_session: ChatSession, already_sent: str):
        """세이프티 차단 시 고정문을 저장·commit 후 content 이벤트 + [DONE] 방출 (스트리밍).

        already_sent: 차단 전 이미 와이어로 내보낸 본문 — DB 에는 이어붙여 저장하되
        와이어로는 고정문만 추가 전송한다(중복 방지).
        """
        db_content = (
            already_sent + "\n\n" + BLOCKED_FALLBACK_MESSAGE if already_sent else BLOCKED_FALLBACK_MESSAGE
        )
        await crud_chat.create_message(
            session=self.session,
            session_id=chat_session.id,
            role=MessageRole.ASSISTANT,
            content=db_content,
        )
        chat_session.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        data = json.dumps({"content": BLOCKED_FALLBACK_MESSAGE}, ensure_ascii=False)
        yield f"data: {data}\n\n"
        yield "data: [DONE]\n\n"


