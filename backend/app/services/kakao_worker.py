# 카카오 콜백 백그라운드 처리: 새 DB 세션에서 LLM 응답 생성 후 콜백 URL로 1회 전송
import asyncio
import logging

from app.core.config import get_settings
from app.core.database import async_session
from app.crud import crud_bot, crud_bot_kakao_channel, crud_chat, crud_user
from app.models.enums import MessageRole
from app.schemas.chat import ChatCompletionRequest
from app.services import kakao_service
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

WORKER_DEADLINE_SECONDS = 50.0


async def process_kakao_callback(
    kakao_bot_id: str, bot_user_key: str, utterance: str, callback_url: str
) -> None:
    """5초 즉시응답 이후 백그라운드에서 호출됨.
    deadline 은 '응답 생성'만 감싼다(생성 실패 시 payload=None → fallback).
    콜백 전송은 deadline 밖에서 정확히 1회만 — 중복 전송 원천 차단.
    """
    settings = get_settings()
    payload: dict | None = None
    try:
        payload = await asyncio.wait_for(
            _build_answer(kakao_bot_id, bot_user_key, utterance),
            timeout=WORKER_DEADLINE_SECONDS,
        )
    except Exception as e:
        logger.error("카카오 워커 응답 생성 실패(fallback 전송 예정): %s", e)

    # SSRF 가드: 허용되지 않은 host 면 전송 중단(성공/실패 무관).
    if not kakao_service.is_allowed_callback_host(
        callback_url, settings.kakao_callback_allowed_hosts_list
    ):
        logger.error("허용되지 않은 callbackUrl host, 전송 중단: %s", callback_url)
        return

    # 콜백 URL 은 1회용 → 여기서 정확히 한 번만 전송.
    await kakao_service.send_callback(
        callback_url, payload or kakao_service.fallback_payload()
    )


async def _build_answer(kakao_bot_id: str, bot_user_key: str, utterance: str) -> dict:
    """새 DB 세션에서 LLM 응답을 생성해 카카오 콜백 payload(dict)를 반환. 실패 시 예외."""
    async with async_session() as session:
        channel = await crud_bot_kakao_channel.get_by_kakao_bot_id(session, kakao_bot_id)
        if channel is None or not channel.is_active:
            raise ValueError(f"미등록/비활성 카카오 봇: {kakao_bot_id}")

        bot = await crud_bot.get_active_bot(session, channel.bot_id)
        if bot is None:
            raise ValueError(f"비활성 봇: {channel.bot_id}")

        user = await crud_user.get_or_create_kakao_user(session, kakao_bot_id, bot_user_key)
        chat_session = await crud_chat.get_or_create_kakao_session(session, user.id, bot.id)

        # 사용자 메시지 직접 저장(ChatService 는 assistant 만 저장). ChatService 내부 commit 으로 함께 영속화.
        await crud_chat.create_message(
            session=session, session_id=chat_session.id, role=MessageRole.USER, content=utterance
        )

        chat_request = ChatCompletionRequest(
            bot_id=bot.id, message=utterance, session_id=chat_session.id, stream=False, use_rag=True
        )
        response = await ChatService(session=session).process_chat_request(
            request=chat_request, bot=bot, chat_session=chat_session
        )
        return kakao_service.build_callback_payload(response.content, response.followups)
