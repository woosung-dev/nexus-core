# 블레싱 FAQ(질문·지정답변)를 봇에 일괄 등록 — create_faq_with_embedding 루프
import asyncio
import sys
import logging

logging.disable(logging.INFO)
sys.path.insert(0, "/Users/woosung/project/agy-project/nexus-core/backend")

XLSX = "/Users/woosung/Downloads/블레싱네비게이션_FAQ_지정답변_작성완료.xlsx"
SHEET = "FAQ 전체 목록"
BOT_ID = 5  # 블레싱 가
Q_COL, A_COL = 2, 7  # 질문, 지정답변 (0-base)
DATA_START_ROW = 2   # 행0 제목, 행1 헤더


def load_pairs():
    import openpyxl
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    ws = wb[SHEET]
    pairs = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i < DATA_START_ROW:
            continue
        q = row[Q_COL] if len(row) > Q_COL else None
        a = row[A_COL] if len(row) > A_COL else None
        q = (str(q).strip() if q is not None else "")
        a = (str(a).strip() if a is not None else "")
        if not q or not a:
            continue
        pairs.append((q, a))
    return pairs


async def main():
    from app.models import user, bot, chat, faq, bot_kakao_channel  # noqa: F401
    from app.core.database import async_session
    from app.crud import crud_bot, crud_faq
    from app.services.faq_service import create_faq_with_embedding

    pairs = load_pairs()
    print(f"xlsx '{SHEET}'에서 (질문,지정답변) {len(pairs)}건 로드\n")

    async with async_session() as s:
        b = await crud_bot.get_active_bot(s, BOT_ID)
        print(f"대상 봇: id={b.id} '{b.name}'")
        existing = await crud_faq.get_active_faqs_by_bot(s, BOT_ID)
        existing_q = {f.question.strip() for f in existing}
        print(f"기존 활성 FAQ: {len(existing)}건\n")

        registered, skipped, failed = 0, 0, 0
        for idx, (q, a) in enumerate(pairs, 1):
            if q in existing_q:
                skipped += 1
                print(f"  [{idx:2}] SKIP(중복): {q[:42]}")
                continue
            try:
                f = await create_faq_with_embedding(
                    session=s, bot_id=BOT_ID, question=q, answer=a, threshold=0.85
                )
                await s.commit()
                registered += 1
                print(f"  [{idx:2}] OK id={f.id}: {q[:42]}")
                existing_q.add(q)
            except Exception as e:
                await s.rollback()
                failed += 1
                print(f"  [{idx:2}] FAIL: {q[:42]}  ({type(e).__name__}: {e})")
            await asyncio.sleep(0.3)

        print(f"\n등록 {registered} · 스킵 {skipped} · 실패 {failed}")
        after = await crud_faq.get_active_faqs_by_bot(s, BOT_ID)
        sample = after[0] if after else None
        has_vec = sample is not None and sample.question_vector is not None
        print(f"봇 {BOT_ID} 활성 FAQ 총 {len(after)}건. 샘플 question_vector NOT NULL: {has_vec}")


if __name__ == "__main__":
    asyncio.run(main())
