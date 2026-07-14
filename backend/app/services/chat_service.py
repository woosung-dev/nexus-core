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
from app.services.rag.factory import get_rag_service

logger = logging.getLogger(__name__)

# 비동기 백필 태스크 참조 보관소 — GC 로 태스크가 취소되는 것을 방지.
_citation_backfill_tasks: set[asyncio.Task] = set()


async def _backfill_citations_async(
    bot_id: int,
    model_name: str,
    system_prompt: str,
    message_id: int,
    prompt: str,
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


def _schedule_citation_backfill(
    bot_id: int,
    model_name: str,
    system_prompt: str,
    message_id: int,
    prompt: str,
) -> None:
    """인용 백필을 백그라운드 태스크로 예약한다(응답 반환을 막지 않음)."""
    task = asyncio.create_task(
        _backfill_citations_async(bot_id, model_name, system_prompt, message_id, prompt)
    )
    _citation_backfill_tasks.add(task)
    task.add_done_callback(_citation_backfill_tasks.discard)


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

        # 1. FAQ Override 검색 (시맨틱 라우팅)
        faq_match = await search_faq_override(
            session=self.session,
            bot_id=bot.id,
            query_text=request.message,
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
                    self._generate_rag_stream(rag_service, request, bot, chat_session, history),
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
                    system_prompt=bot.system_prompt,
                    model_name=bot.llm_model,
                    history=history or None,
                )

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
                if not rag_response.citations:
                    _schedule_citation_backfill(
                        bot_id=bot.id,
                        model_name=bot.llm_model,
                        system_prompt=bot.system_prompt,
                        message_id=assistant_msg.id,
                        prompt=request.message,
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

        # 3. 일반 LLM 처리
        llm_service = get_llm_service(bot.llm_model)

        if request.stream:
            return StreamingResponse(
                self._generate_llm_stream(llm_service, request, bot, chat_session, history),
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
                system_prompt=bot.system_prompt,
                history=history or None,
            )

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

    async def _generate_rag_stream(self, rag_service, request, bot, chat_session, history=None):
        full_response_content = ""
        try:
            meta_data = json.dumps({"session_id": chat_session.id}, ensure_ascii=False)
            yield f"data: {meta_data}\n\n"

            captured_citations: list | None = None
            async for chunk in rag_service.generate_stream_with_rag(
                bot_id=bot.id,
                prompt=request.message,
                system_prompt=bot.system_prompt,
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
            if not captured_citations:
                _schedule_citation_backfill(
                    bot_id=bot.id,
                    model_name=bot.llm_model,
                    system_prompt=bot.system_prompt,
                    message_id=assistant_msg.id,
                    prompt=request.message,
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

    async def _generate_llm_stream(self, llm_service, request, bot, chat_session, history=None):
        full_response_content = ""
        try:
            # 클라이언트에게 활성화된 session_id를 가장 먼저 알려줌 (새로고침/리다이렉트 용도)
            meta_data = json.dumps({"session_id": chat_session.id}, ensure_ascii=False)
            yield f"data: {meta_data}\n\n"

            async for chunk in llm_service.generate_stream(
                prompt=request.message,
                system_prompt=bot.system_prompt,
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


