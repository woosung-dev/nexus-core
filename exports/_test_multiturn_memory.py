# 봇 멀티턴 기억(history_window) 기능 테스트 — 3턴 대화로 이전 질문 기억 여부 검증
import asyncio
import sys
import logging

logging.disable(logging.INFO)
sys.path.insert(0, "/Users/woosung/project/agy-project/nexus-core/backend")

BOT_ID = 3
USER_ID = 1
QUESTIONS = [
    "저는 입교한 지 얼마 안 된 1세 남성입니다. 미혼 1세 축복을 준비하려면 무엇부터 해야 하나요?",
    "제가 아까 1세라고 했죠? 그럼 축복받을 때 제 나이에 제한이 따로 있나요?",
    "앞에서 알려준 준비 단계 중 가장 첫 번째를 더 자세히 설명해줘.",
]


async def main():
    # 모든 ORM 모델을 매퍼 레지스트리에 등록 (FK 'users' 해석용)
    from app.models import user, bot, chat, faq, bot_kakao_channel  # noqa: F401
    from app.core.database import async_session
    from app.crud import crud_bot, crud_chat
    from app.models.enums import MessageRole
    from app.schemas.chat import ChatCompletionRequest
    from app.services.chat_service import ChatService

    async with async_session() as s:
        bot = await crud_bot.get_active_bot(s, BOT_ID)
        print(f"봇: id={bot.id} '{bot.name}' history_window={bot.history_window} use_rag={bot.use_rag} model={bot.llm_model}\n")
        sess = await crud_chat.create_chat_session(s, user_id=USER_ID, bot_id=BOT_ID, title="멀티턴 기억 테스트")
        await s.commit()
        await s.refresh(sess)
        svc = ChatService(s)

        answers = []
        for i, q in enumerate(QUESTIONS, 1):
            # 1) 사용자 메시지 flush (웹 엔드포인트와 동일 순서)
            await crud_chat.create_message(s, session_id=sess.id, role=MessageRole.USER, content=q)
            await s.commit()
            # 2) 이 턴에 실제 로드될 history(슬라이딩 윈도우) 미리보기 — 기능 검증 포인트
            hist = await svc._load_history(sess.id, bot, q)
            print("=" * 78)
            print(f"[턴 {i}] Q: {q}")
            print(f"  ↳ 로드된 history {len(hist)}개:")
            for h in hist:
                print(f"      - {h['role']}: {h['content'][:46]}")
            if not hist:
                print("      (없음 — 첫 턴)")
            # 3) 실제 응답 생성 (non-stream, RAG on)
            req = ChatCompletionRequest(bot_id=BOT_ID, message=q, session_id=sess.id, stream=False, use_rag=True)
            resp = await svc.process_chat_request(req, bot, sess)
            ans = resp.content or ""
            answers.append(ans)
            print(f"  A: {ans[:340]}")
            await asyncio.sleep(5)

        # 4) 기억 판정 (휴리스틱)
        print("\n" + "#" * 78)
        print("# 기억 판정")
        a2, a3 = answers[1], answers[2]
        t2_ok = any(k in a2 for k in ["연령 제한이 없", "연령 불문", "나이 제한이 없", "1세는", "1세의 경우"]) and \
            not any(k in a2 for k in ["어느 세대", "1세이신지 2세", "1세인지 2세"])
        t3_ok = any(k in a3 for k in ["첫", "첫째", "처음", "1.", "①", "먼저"]) and \
            not any(k in a3 for k in ["어떤 단계", "무엇을 준비"])
        print(f"  턴2 (1세 맥락 기억 → 연령 제한 안내): {'✅ 기억함' if t2_ok else '⚠️ 확인필요'}")
        print(f"  턴3 (앞 답변의 첫 단계 참조): {'✅ 기억함' if t3_ok else '⚠️ 확인필요'}")
        print("  ※ 판정은 휴리스틱 — 위 답변 본문으로 최종 확인 권장.")


if __name__ == "__main__":
    asyncio.run(main())
