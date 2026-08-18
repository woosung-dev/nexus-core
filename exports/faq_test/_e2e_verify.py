# FAQ override end-to-end 검증 — 실제 채팅 경로(process_chat_request)에서 source=faq_override 확인
import asyncio
import sys
import logging

logging.disable(logging.INFO)
sys.path.insert(0, "/Users/woosung/project/agy-project/nexus-core/backend")

BOT_ID = 5
USER_ID = 1
PROBE = "축복정리 하는 방법하고 갖춰야 할 요건 알려줘"  # 통과기대(타깃 id=3 매칭)


async def main():
    from app.models import user, bot, chat, faq, bot_kakao_channel  # noqa: F401
    from app.core.database import async_session
    from app.crud import crud_bot, crud_chat
    from app.models.enums import MessageRole
    from app.schemas.chat import ChatCompletionRequest
    from app.services.chat_service import ChatService

    async with async_session() as s:
        b = await crud_bot.get_active_bot(s, BOT_ID)
        sess = await crud_chat.create_chat_session(s, user_id=USER_ID, bot_id=BOT_ID, title="FAQ override 검증")
        await s.commit()
        await s.refresh(sess)
        await crud_chat.create_message(s, session_id=sess.id, role=MessageRole.USER, content=PROBE)
        await s.commit()

        svc = ChatService(s)
        req = ChatCompletionRequest(bot_id=BOT_ID, message=PROBE, session_id=sess.id, stream=False, use_rag=True)
        resp = await svc.process_chat_request(req, b, sess)

        print(f"프로브: {PROBE}")
        print(f"source: {getattr(resp, 'source', None)}")
        print(f"content[:200]: {(resp.content or '')[:200]}")

        # 정리: 검증 세션 삭제 (FAQ는 보존)
        from sqlalchemy import delete, select
        from app.models.chat import ChatSession, Message
        await s.execute(delete(Message).where(Message.session_id.in_(
            select(ChatSession.id).where(ChatSession.title == "FAQ override 검증"))))
        await s.execute(delete(ChatSession).where(ChatSession.title == "FAQ override 검증"))
        await s.commit()
        print("검증 세션 삭제 완료 (FAQ 35건은 보존)")


if __name__ == "__main__":
    asyncio.run(main())
