"""
채팅 관련 API 엔드포인트.
세션 관리, 메시지 기록, SSE(Server-Sent Events) 스트리밍 지원.
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.crud import crud_chat, crud_bot
from app.core.exceptions import BotNotFoundError, NotFoundError, NexusException, ValidationError
from app.models.enums import MessageRole
from app.models.user import User
from app.schemas.chat import (
    ChatCompletionRequest,
    ChatSessionListResponse,
    ChatSessionResponse,
    MessageResponse,
    MessageFeedbackUpdate,
)
from app.schemas.clarification import (
    ChatClarificationActionRequest,
    ChatClarificationActionResponse,
    ChatClarificationFacet,
    ChatClarificationStateResponse,
)
from app.services.chat_service import ChatService
from app.services.adaptive_clarification_service import MAX_QUESTIONS, start_companion, view_for_state
from app.services import clarification_service as policy_service
from app.services.rag.factory import get_rag_service
from app.services.strict_mode import STRICT_EVIDENCE_MESSAGE, has_direct_citation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chats", tags=["채팅"])


# Removed _get_llm_service (moved to ChatService)


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
    rows, total = await crud_chat.get_user_chat_sessions(
        session, current_user.id, limit, offset
    )

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

    Idempotent: 동일 user+bot 으로 메시지 0 개인 최근 빈 세션이 이미 있으면
    새로 만들지 않고 그 세션을 그대로 반환한다. 봇 선택 후 첫 메시지를 안 보내고 떠난 경우
    사이드바에 "새 대화" 가 누적되는 것을 막기 위함.
    """
    bot_obj = None
    if bot_id:
        bot_obj = await crud_bot.get_active_bot(session, bot_id)
        if not bot_obj:
            raise BotNotFoundError()

    existing = await crud_chat.find_recent_empty_session(session, current_user.id, bot_id)
    if existing is not None:
        sess_dict = existing.model_dump()
        if bot_obj:
            sess_dict["bot"] = bot_obj.model_dump()
        return ChatSessionResponse.model_validate(sess_dict)

    chat_session = await crud_chat.create_chat_session(
        session=session, user_id=current_user.id, bot_id=bot_id, title=title
    )
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
    chat_session = await crud_chat.get_chat_session_by_id(session, session_id)

    if not chat_session:
        raise NotFoundError("채팅 세션을 찾을 수 없습니다.")
    if chat_session.user_id != current_user.id:
        raise NexusException(
            error_code="FORBIDDEN", 
            message="접근 권한이 없습니다.", 
            status_code=status.HTTP_403_FORBIDDEN
        )

    messages = await crud_chat.get_session_messages(session, session_id)

    return [MessageResponse.model_validate(m) for m in messages]


async def _owned_chat_session(
    session: AsyncSession, session_id: int, current_user: User
):
    chat_session = await crud_chat.get_chat_session_by_id(session, session_id)
    if not chat_session:
        raise NotFoundError("세션을 찾을 수 없습니다.")
    if chat_session.user_id != current_user.id:
        raise NexusException(
            error_code="FORBIDDEN", message="접근 권한이 없습니다.", status_code=status.HTTP_403_FORBIDDEN
        )
    return chat_session


@router.get("/{session_id}/clarification", response_model=ChatClarificationStateResponse)
async def get_chat_clarification(
    session_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatClarificationStateResponse:
    """새로고침 뒤 현재 pending 동행 카드만 복원한다."""
    chat_session = await _owned_chat_session(session, session_id, current_user)
    view = view_for_state(chat_session.clarification_state)
    return ChatClarificationStateResponse(active=view is not None, clarification=view)


@router.post("/{session_id}/clarification", response_model=ChatClarificationActionResponse)
async def act_on_chat_clarification(
    session_id: int,
    request: ChatClarificationActionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatClarificationActionResponse:
    """CTA 시작/현재 facet 제출. 상태·정책·선택지는 모두 서버에서 재검증한다."""
    chat_session = await _owned_chat_session(session, session_id, current_user)
    state = chat_session.clarification_state
    view = view_for_state(state)
    if not isinstance(state, dict) or view is None:
        raise ValidationError("진행 중인 추가 확인이 없습니다.")
    if state.get("version") != request.version:
        raise ValidationError("화면이 최신 상태가 아닙니다. 새로고침 후 다시 시도해 주세요.")

    if request.action == "start_companion":
        updated = start_companion(state, request.version)
        if updated is None:
            raise ValidationError("이 요청은 함께 확인하기로 시작할 수 없습니다.")
        chat_session.clarification_state = updated
        next_view = view_for_state(updated)
        content = "좋습니다. 정확한 안내를 위해 한 가지만 확인할게요.\n\n" + (
            next_view.facet.question if next_view and next_view.facet else ""
        )
        await crud_chat.create_message(
            session=session, session_id=session_id, role=MessageRole.ASSISTANT, content=content
        )
        chat_session.updated_at = datetime.now(timezone.utc)
        session.add(chat_session)
        await session.commit()
        return ChatClarificationActionResponse(
            session_id=session_id, content=content, clarification=next_view
        )

    if view.mode != "blocking" or view.facet is None:
        raise ValidationError("현재 확인 항목을 제출할 수 없습니다.")
    if request.facet_id != view.facet.id:
        raise ValidationError("현재 확인 항목과 일치하지 않습니다.")
    values = [value.strip() for value in request.values if isinstance(value, str) and value.strip()]
    if not values or (view.facet.selection_mode == "single" and len(values) != 1):
        raise ValidationError("현재 질문에 맞는 값을 입력해 주세요.")
    if any(len(value) > 500 for value in values):
        raise ValidationError("입력값이 너무 깁니다.")

    slots = dict(state.get("canonical_slots") or {})
    question_count = int(state.get("question_count") or 0) + 1
    next_facet: ChatClarificationFacet | None = None
    if view.facet.policy:
        bot = await crud_bot.get_active_bot(session, chat_session.bot_id)
        if not bot:
            raise BotNotFoundError()
        policy = policy_service._active_policy(bot, None)
        submitted = policy_service._submitted_policy_rule(
            policy,
            None,
            [
                policy_service.ClarificationAnswer(
                    question_id=view.facet.id, question=view.facet.question, values=values
                )
            ],
        )
        if submitted is None:
            raise ValidationError("현재 정책 항목을 다시 확인해 주세요.")
        normalised = policy_service._normalise_slot_values(
            next(slot for slot in submitted.required_slots if slot.id == view.facet.id), values
        )
        if not normalised:
            raise ValidationError("허용된 선택지 또는 직접 입력 규칙에 맞지 않습니다.")
        slots[view.facet.id] = normalised
        _, missing = policy_service._policy_answers_from_values(submitted, slots)
        if missing:
            slot = missing[0]
            next_facet = ChatClarificationFacet(
                id=slot.id,
                question=slot.question,
                selection_mode=slot.selection_mode,
                options=[option.label for option in slot.options],
                allow_custom=slot.allow_custom,
                policy=True,
            )
    else:
        slots[view.facet.id] = values

    if next_facet is not None:
        if question_count >= MAX_QUESTIONS:
            content = "두 번의 확인으로도 안전하게 판단할 수 없어 담당자에게 확인해 주세요."
            chat_session.clarification_state = None
            await crud_chat.create_message(
                session=session, session_id=session_id, role=MessageRole.ASSISTANT, content=content
            )
            chat_session.updated_at = datetime.now(timezone.utc)
            await session.commit()
            return ChatClarificationActionResponse(session_id=session_id, content=content)
        updated = {
            "mode": "blocking",
            "route": "blocking_ask",
            "canonical_slots": slots,
            "pending_facet": next_facet.model_dump(),
            "pinned_evidence_ids": state.get("pinned_evidence_ids", []),
            "question_count": question_count,
            "version": request.version + 1,
        }
        chat_session.clarification_state = updated
        next_view = view_for_state(updated)
        content = "한 가지만 더 확인할게요.\n\n" + next_facet.question
        await crud_chat.create_message(
            session=session, session_id=session_id, role=MessageRole.ASSISTANT, content=content
        )
        chat_session.updated_at = datetime.now(timezone.utc)
        await session.commit()
        return ChatClarificationActionResponse(
            session_id=session_id, content=content, clarification=next_view
        )

    # 카드 제출 후에는 서버가 보관한 최초 요청과 canonical slot만으로 최종 RAG를 호출한다.
    # 일반 composer 입력/클라이언트가 준 정책 context는 다시 사용하지 않는다.
    bot = await crud_bot.get_active_bot(session, chat_session.bot_id)
    if not bot:
        raise BotNotFoundError()
    messages = await crud_chat.get_session_messages(session, session_id)
    original = next((message.content for message in reversed(messages) if message.role == MessageRole.USER), None)
    if not original:
        raise ValidationError("최초 요청을 찾을 수 없습니다.")
    slot_text = "\n".join(f"- {key}: {', '.join(value)}" for key, value in slots.items())
    rag_response = await get_rag_service(provider=bot.llm_model).generate_with_rag(
        bot_id=bot.id,
        prompt=f"{original}\n\n[서버 검증 확인값]\n{slot_text}",
        system_prompt=bot.system_prompt,
        model_name=bot.llm_model,
    )
    if bot.evidence_policy_mode == "strict" and not has_direct_citation(rag_response.citations):
        rag_response.answer = STRICT_EVIDENCE_MESSAGE
        rag_response.citations = []
        rag_response.followups = []
    await crud_chat.create_message(
        session=session,
        session_id=session_id,
        role=MessageRole.ASSISTANT,
        content=rag_response.answer,
        citations=[citation.model_dump() for citation in rag_response.citations],
        followups=rag_response.followups,
    )
    chat_session.clarification_state = None
    chat_session.updated_at = datetime.now(timezone.utc)
    await session.commit()
    return ChatClarificationActionResponse(
        session_id=session_id,
        content=rag_response.answer,
        citations=rag_response.citations,
        followups=rag_response.followups,
    )


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
    bot = await crud_bot.get_active_bot(session, request.bot_id)

    if not bot:
        raise BotNotFoundError()
    if not bot.is_active:
        raise ValidationError("비활성화된 봇입니다.")

    # 2. 세션 검증 또는 신규 생성
    chat_session = None

    if request.session_id:
        chat_session = await crud_chat.get_chat_session_by_id(session, request.session_id)
        if not chat_session:
            raise NotFoundError("세션을 찾을 수 없습니다.")
        if chat_session.user_id != current_user.id:
            raise NexusException(
                error_code="FORBIDDEN",
                message="세션 접근 권한이 없습니다.",
                status_code=status.HTTP_403_FORBIDDEN
            )
        pending_view = view_for_state(chat_session.clarification_state)
        if pending_view is not None and pending_view.mode == "blocking":
            raise ValidationError("추가 확인 카드에 먼저 답해 주세요.")
        # optional CTA를 시작하지 않고 새 요청을 보낸 경우 이전 동행 제안은 만료시킨다.
        if pending_view is not None:
            chat_session.clarification_state = None
        # 사이드바 가독성: 빈 세션의 기본 제목("새 대화") 을 첫 메시지로 자동 갱신.
        # 이후 메시지에서는 이미 다른 제목이 들어있으므로 건드리지 않는다.
        # 멀티라인 메시지 대비: 첫 줄만 사용 + strip (사이드바 layout 깨짐 방지).
        if chat_session.title == "새 대화":
            first_line = request.message.split("\n", 1)[0].strip() or request.message[:20]
            chat_session.title = (
                first_line[:20] + "..." if len(first_line) > 20 else first_line
            )
            session.add(chat_session)
            await session.flush()
    else:
        # 새 세션 생성
        title = request.message[:20] + "..." if len(request.message) > 20 else request.message
        chat_session = await crud_chat.create_chat_session(
            session=session, user_id=current_user.id, bot_id=request.bot_id, title=title
        )

    # 3. 사용자 메시지 DB에 저장 (commit 없이 flush만)
    await crud_chat.create_message(
        session=session, session_id=chat_session.id, role=MessageRole.USER, content=request.message
    )

    # 4. 서비스 레이어 위임 (ChatService)
    chat_service = ChatService(session=session)
    return await chat_service.process_chat_request(
        request=request, bot=bot, chat_session=chat_session
    )


@router.patch("/messages/{message_id}", response_model=MessageResponse)
async def update_message_feedback(
    message_id: int,
    request: MessageFeedbackUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """
    메시지에 대한 피드백(좋아요/싫어요)을 업데이트합니다.
    """
    # 메시지 및 세션 소유권 확인 (비동기 쿼리)
    row = await crud_chat.get_message_with_session(session, message_id)

    if not row:
        raise NotFoundError("메시지를 찾을 수 없습니다.")

    msg_obj, sess_obj = row

    if sess_obj.user_id != current_user.id:
        raise NexusException(
            error_code="FORBIDDEN",
            message="피드백 수정 권한이 없습니다.",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # 업데이트 — feedback 이 null 이면 reasons/comment 도 자동 클리어
    msg_obj.feedback = request.feedback
    if request.feedback is None:
        msg_obj.feedback_reasons = None
        msg_obj.feedback_comment = None
    else:
        msg_obj.feedback_reasons = (
            json.dumps(request.feedback_reasons, ensure_ascii=False)
            if request.feedback_reasons
            else None
        )
        msg_obj.feedback_comment = (request.feedback_comment or None)

    session.add(msg_obj)
    await session.commit()
    await session.refresh(msg_obj)

    return MessageResponse.model_validate(msg_obj)
