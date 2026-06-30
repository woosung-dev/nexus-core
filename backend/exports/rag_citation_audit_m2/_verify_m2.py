# 봇5·3 에 search_citations(persona+인용지침)를 여러 질문 호출해 인용 보고율·정확성을 라이브 검증
import asyncio

from app.crud import crud_bot
from app.services.rag.factory import get_rag_service

QUESTIONS = [
    "축복식 드레스와 턱시도는 어디서 구매하나요?",
    "축복을 받고 가정회비를 내는 이유가 무엇인가요?",
    "금식 중에 실수하면 어떻게 해야 해?",
    "2세가정 편성은 꼭 해야 하나요?",
]


async def run_bot(bot_id: int):
    from app.core.database import async_session

    async with async_session() as session:
        bot = await crud_bot.get_active_bot(session, bot_id)
    if bot is None:
        print(f"[봇{bot_id}] 활성 봇 없음 — skip")
        return
    svc = get_rag_service(provider=bot.llm_model)
    print(f"\n=== 봇{bot_id} ({bot.llm_model}, persona {len(bot.system_prompt)}자) ===")
    hits = 0
    for q in QUESTIONS:
        cites = await svc.search_citations(
            bot_id=bot_id, prompt=q, system_prompt=bot.system_prompt, model_name=bot.llm_model
        )
        if cites:
            hits += 1
        approx = {c.approximate for c in cites}
        files = sorted({c.title for c in cites if c.title})[:4]
        print(f"  q={q[:22]!r:<26} citations={len(cites):>2} approximate={approx or '-'}")
        for f in files:
            print(f"      · {f}")
    print(f"  >>> 인용 보고율(≥1) = {hits}/{len(QUESTIONS)}")


async def main():
    for bot_id in (5, 3):
        await run_bot(bot_id)


if __name__ == "__main__":
    asyncio.run(main())
