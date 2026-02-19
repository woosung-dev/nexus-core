"""
채팅 완성 API 엔드포인트.
SSE(Server-Sent Events) 스트리밍 지원.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.models.bot import Bot
from app.schemas.chat import ChatCompletionRequest, ChatCompletionResponse
from app.services.llm.gemini import GeminiService
from app.services.llm.openai import OpenAIService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["채팅"])


def _get_llm_service(model_name: str):
    """봇의 llm_model 설정에 따라 적절한 LLM 서비스 반환"""
    if model_name.startswith("gpt"):
        return OpenAIService(model_name=model_name)
    # 기본값: Gemini
    return GeminiService(model_name=model_name)


@router.post("/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    채팅 완성 엔드포인트.
    stream=True (기본값) → SSE 스트리밍 응답
    stream=False → JSON 응답
    """
    # 봇 조회
    result = await session.execute(select(Bot).where(Bot.id == request.bot_id))
    bot = result.scalar_one_or_none()

    if not bot:
        raise HTTPException(status_code=404, detail="봇을 찾을 수 없습니다.")

    if not bot.is_active:
        raise HTTPException(status_code=400, detail="비활성화된 봇입니다.")

    # LLM 서비스 선택 (봇 설정 기반)
    llm_service = _get_llm_service(bot.llm_model)

    if request.stream:
        # SSE 스트리밍 응답
        async def event_generator():
            try:
                async for chunk in llm_service.generate_stream(
                    prompt=request.message,
                    system_prompt=bot.system_prompt,
                ):
                    # SSE 형식으로 전송
                    data = json.dumps({"content": chunk}, ensure_ascii=False)
                    yield f"data: {data}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"스트리밍 오류: {e}")
                error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
                yield f"data: {error_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        # Non-Streaming 응답
        content = await llm_service.generate(
            prompt=request.message,
            system_prompt=bot.system_prompt,
        )

        return ChatCompletionResponse(
            session_id=request.session_id or 0,
            content=content,
            bot_id=request.bot_id,
        )
