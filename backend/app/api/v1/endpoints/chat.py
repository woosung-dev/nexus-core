"""
채팅 관련 API 엔드포인트.
세션 관리, 메시지 기록, SSE(Server-Sent Events) 스트리밍 지원.
"""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, desc

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.bot import Bot
from app.models.chat import ChatSession, Message
from app.models.enums import MessageRole
from app.models.user import User
from app.schemas.chat import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
    MessageResponse,
)
from app.services.rag.factory import get_rag_service
from app.services.llm.gemini import GeminiService
from app.services.llm.openai import OpenAIService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chats", tags=["채팅"])


def _get_llm_service(model_name: str):
    """봇의 llm_model 설정에 따라 적절한 LLM 서비스 반환"""
    if model_name.startswith("gpt"):
        return OpenAIService(model_name=model_name)
    # 기본값: Gemini
    return GeminiService(model_name=model_name)


@router.get("", response_model=ChatSessionListResponse)
async def list_chat_sessions(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatSessionListResponse:
    """
    현재 로그인한 사용자의 채팅 세션 목록을 조회합니다.
    최근 업데이트된 순서(updated_at DESC)로 정렬됩니다.
    """
    statement = (
        select(ChatSession, Bot)
        .outerjoin(Bot, ChatSession.bot_id == Bot.id)
        .where(ChatSession.user_id == current_user.id)
        .order_by(desc(ChatSession.updated_at))
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(statement)
    rows = result.all()

    # 전체 개수 조회
    count_statement = select(ChatSession.id).where(ChatSession.user_id == current_user.id)
    count_result = await session.execute(count_statement)
    total = len(count_result.scalars().all())

    session_responses = []
    for chat_sess, bot_obj in rows:
        sess_dict = chat_sess.model_dump()
        if bot_obj:
            sess_dict["bot"] = bot_obj.model_dump()
        session_responses.append(ChatSessionResponse.model_validate(sess_dict))

    return ChatSessionListResponse(sessions=session_responses, total=total)


@router.post("", response_model=ChatSessionResponse)
async def create_chat_session(
    bot_id: int | None = None,
    title: str = "새 대화",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatSessionResponse:
    """
    새로운 채팅 세션을 생성합니다.
    """
    bot_obj = None
    if bot_id:
        result = await session.execute(select(Bot).where(Bot.id == bot_id))
        bot_obj = result.scalar_one_or_none()
        if not bot_obj:
            raise HTTPException(status_code=404, detail="지정된 봇을 찾을 수 없습니다.")

    chat_session = ChatSession(
        user_id=current_user.id,
        bot_id=bot_id,
        title=title,
    )
    session.add(chat_session)
    await session.commit()
    await session.refresh(chat_session)

    sess_dict = chat_session.model_dump()
    if bot_obj:
        sess_dict["bot"] = bot_obj.model_dump()

    return ChatSessionResponse.model_validate(sess_dict)


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[MessageResponse]:
    """
    특정 채팅 세션의 메시지 기록을 조회합니다.
    """
    # 세션 소유권 검증
    result = await session.execute(select(ChatSession).where(ChatSession.id == session_id))
    chat_session = result.scalar_one_or_none()

    if not chat_session:
        raise HTTPException(status_code=404, detail="채팅 세션을 찾을 수 없습니다.")
    if chat_session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    statement = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    msg_result = await session.execute(statement)
    messages = msg_result.scalars().all()

    return [MessageResponse.model_validate(m) for m in messages]


@router.post("/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    채팅 완성 엔드포인트.
    사용자 메시지를 DB에 저장하고, AI 응답 스트리밍 완료 후 응답 메시지를 DB에 저장합니다.
    session_id가 없으면 자동으로 새 채팅 세션을 생성합니다.
    """
    # 1. 봇 검증
    result = await session.execute(select(Bot).where(Bot.id == request.bot_id))
    bot = result.scalar_one_or_none()

    if not bot:
        raise HTTPException(status_code=404, detail="봇을 찾을 수 없습니다.")
    if not bot.is_active:
        raise HTTPException(status_code=400, detail="비활성화된 봇입니다.")

    # 2. 세션 검증 또는 신규 생성
    chat_session = None

    if request.session_id:
        sess_result = await session.execute(
            select(ChatSession).where(ChatSession.id == request.session_id)
        )
        chat_session = sess_result.scalar_one_or_none()
        if not chat_session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        if chat_session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="세션 접근 권한이 없습니다.")
    else:
        # 새 세션 생성
        title = request.message[:20] + "..." if len(request.message) > 20 else request.message
        chat_session = ChatSession(
            user_id=current_user.id,
            bot_id=request.bot_id,
            title=title
        )
        session.add(chat_session)
        await session.flush()  # ID 확보

    # 3. 사용자 메시지 DB에 즉시 저장
    user_msg = Message(
        session_id=chat_session.id,
        role=MessageRole.USER,
        content=request.message,
    )
    session.add(user_msg)
    await session.commit()

    # 4. (분기) RAG 처리 (Non-Streaming)
    if request.use_rag:
        rag_service = get_rag_service(provider=bot.llm_model)
        rag_response = await rag_service.generate_with_rag(
            bot_id=request.bot_id,
            prompt=request.message,
            system_prompt=bot.system_prompt,
            model_name=bot.llm_model,
        )

        # AI 응답 DB 저장
        ai_msg = Message(
            session_id=chat_session.id,
            role=MessageRole.ASSISTANT,
            content=rag_response.answer,
        )
        session.add(ai_msg)
        chat_session.updated_at = datetime.now()
        await session.commit()

        return ChatCompletionResponse(
            session_id=chat_session.id,
            content=rag_response.answer,
            bot_id=request.bot_id,
            citations=rag_response.citations,
        )

    # 5. 일반 LLM 처리
    llm_service = _get_llm_service(bot.llm_model)

    if request.stream:
        # SSE 스트리밍 응답
        async def event_generator():
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

                # 스트리밍이 완전히 정상 종료된 후 1회 DB 기록 & updated_at 갱신
                ai_msg = Message(
                    session_id=chat_session.id,
                    role=MessageRole.ASSISTANT,
                    content=full_response_content,
                )
                session.add(ai_msg)
                chat_session.updated_at = datetime.now()
                await session.commit()

            except Exception as e:
                logger.error(f"스트리밍 오류: {e}")
                error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
                yield f"data: {error_data}\n\n"
                # 주의: 오류 발생 시 불완전한 메시지는 저장하지 않음 (롤백 처리됨)

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

        ai_msg = Message(
            session_id=chat_session.id,
            role=MessageRole.ASSISTANT,
            content=content,
        )
        session.add(ai_msg)
        chat_session.updated_at = datetime.now()
        await session.commit()

        return ChatCompletionResponse(
            session_id=chat_session.id,
            content=content,
            bot_id=request.bot_id,
        )
