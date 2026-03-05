"""
채팅 비즈니스 로직을 처리하는 서비스 계층.
컨트롤러(chat.py)에서 넘겨받은 요청을 기반으로 FAQ, RAG, 일반 LLM 분기 처리를 수행하고,
정상 스트리밍 및 Non-Streaming 응답을 책임집니다.
"""

import json
import logging
from datetime import datetime

from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import crud_chat
from app.models.bot import Bot
from app.models.chat import ChatSession
from app.models.enums import MessageRole
from app.schemas.chat import ChatCompletionRequest, ChatCompletionResponse
from app.services.faq_service import search_faq_override
from app.services.llm.gemini import GeminiService
from app.services.llm.openai import OpenAIService
from app.services.rag.factory import get_rag_service

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _get_llm_service(self, model_name: str):
        """봇의 llm_model 설정에 따라 적절한 LLM 서비스 반환"""
        if model_name.startswith("gpt"):
            return OpenAIService(model_name=model_name)
        # 기본값: Gemini
        return GeminiService(model_name=model_name)

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
            chat_session.updated_at = datetime.now()
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

        # 2. (분기) RAG 처리
        if request.use_rag:
            rag_service = get_rag_service(provider=bot.llm_model)

            if request.stream:
                return StreamingResponse(
                    self._generate_rag_stream(rag_service, request, bot, chat_session),
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
                )

                await crud_chat.create_message(
                    session=self.session,
                    session_id=chat_session.id,
                    role=MessageRole.ASSISTANT,
                    content=rag_response.answer,
                )
                chat_session.updated_at = datetime.now()
                await self.session.commit()

                return ChatCompletionResponse(
                    session_id=chat_session.id,
                    content=rag_response.answer,
                    bot_id=bot.id,
                    citations=rag_response.citations,
                    source="rag",
                )

        # 3. 일반 LLM 처리
        llm_service = self._get_llm_service(bot.llm_model)

        if request.stream:
            return StreamingResponse(
                self._generate_llm_stream(llm_service, request, bot, chat_session),
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
            )

            await crud_chat.create_message(
                session=self.session,
                session_id=chat_session.id,
                role=MessageRole.ASSISTANT,
                content=content,
            )
            chat_session.updated_at = datetime.now()
            await self.session.commit()

            return ChatCompletionResponse(
                session_id=chat_session.id,
                content=content,
                bot_id=bot.id,
                source="llm",
            )

    async def _generate_rag_stream(self, rag_service, request, bot, chat_session):
        full_response_content = ""
        try:
            meta_data = json.dumps({"session_id": chat_session.id}, ensure_ascii=False)
            yield f"data: {meta_data}\n\n"

            async for chunk in rag_service.generate_stream_with_rag(
                bot_id=bot.id,
                prompt=request.message,
                system_prompt=bot.system_prompt,
                model_name=bot.llm_model,
            ):
                full_response_content += chunk
                data = json.dumps({"content": chunk}, ensure_ascii=False)
                yield f"data: {data}\n\n"

            yield "data: [DONE]\n\n"

            # 스트리밍 완료 후 1회 commit
            await crud_chat.create_message(
                session=self.session,
                session_id=chat_session.id,
                role=MessageRole.ASSISTANT,
                content=full_response_content,
            )
            chat_session.updated_at = datetime.now()
            await self.session.commit()

        except Exception as e:
            logger.error(f"RAG 스트리밍 오류: {e}")
            error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    async def _generate_llm_stream(self, llm_service, request, bot, chat_session):
        full_response_content = ""
        try:
            # 클라이언트에게 활성화된 session_id를 가장 먼저 알려줌 (새로고침/리다이렉트 용도)
            meta_data = json.dumps({"session_id": chat_session.id}, ensure_ascii=False)
            yield f"data: {meta_data}\n\n"

            async for chunk in llm_service.generate_stream(
                prompt=request.message,
                system_prompt=bot.system_prompt,
            ):
                full_response_content += chunk
                data = json.dumps({"content": chunk}, ensure_ascii=False)
                yield f"data: {data}\n\n"

            yield "data: [DONE]\n\n"

            # 스트리밍 정상 종료 후 1회 DB 기록 & updated_at 갱신
            await crud_chat.create_message(
                session=self.session,
                session_id=chat_session.id,
                role=MessageRole.ASSISTANT,
                content=full_response_content,
            )
            chat_session.updated_at = datetime.now()
            await self.session.commit()

        except Exception as e:
            logger.error(f"스트리밍 오류: {e}")
            error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
            # 주의: 오류 발생 시 불완전한 메시지는 저장하지 않음 (롤백 처리됨)


