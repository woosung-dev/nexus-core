# HOLD FAQ 15종 비활성화(소프트삭제). argv: dev|live. KEEP=20(기존19+id22) 유지
import os
import sys
import json
import asyncio
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
TARGET = sys.argv[1]  # dev | live
lines = (ROOT / "backend/.env").read_text().splitlines()
if TARGET == "live":
    url = next(s.split("=", 1)[1].strip() for s in (l.strip().lstrip("#").strip() for l in lines)
               if s.startswith("DATABASE_URL=") and "neon.tech" in s)
    BOTS = {6: "C", 7: "D"}
else:
    url = next(s.split("=", 1)[1].strip() for s in (l.strip() for l in lines)
               if s.startswith("DATABASE_URL=") and "localhost" in s)
    BOTS = {3: "나", 5: "가"}
for l in lines:
    l = l.strip()
    if l and not l.startswith("#") and "=" in l:
        k, v = l.split("=", 1)
        os.environ[k] = v.strip().strip('"').strip("'")
os.environ["DATABASE_URL"] = url
sys.path.insert(0, str(ROOT / "backend"))
import logging  # noqa: E402
logging.disable(logging.INFO)

REMOVE_IDS = {5, 11, 12, 13, 14, 15, 16, 17, 25, 26, 27, 28, 29, 30, 32}  # HOLD - id22
CANON = json.load(open(ROOT / "exports/faq_test/faqs_export.json"))
REMOVE_Q = {f["question"].strip() for f in CANON if f["id"] in REMOVE_IDS}
assert len(REMOVE_Q) == 15, f"제거 질문 수 이상: {len(REMOVE_Q)}"


async def main():
    from app.models import user, bot, chat, faq, bot_kakao_channel  # noqa: F401
    from app.core.database import async_session
    from app.crud import crud_bot, crud_faq

    print(f"대상: {TARGET}  봇 {BOTS}  · 제거 {len(REMOVE_Q)}종 / 유지 20종")
    async with async_session() as s:
        for bid, tag in BOTS.items():
            b = await crud_bot.get_active_bot(s, bid)
            assert b, f"봇 {bid} 없음"
            fs = await crud_faq.get_active_faqs_by_bot(s, bid)
            removed = 0
            for f in fs:
                if f.question.strip() in REMOVE_Q:
                    await crud_faq.soft_delete_faq(s, f)
                    removed += 1
            await s.commit()
            left = await crud_faq.get_active_faqs_by_bot(s, bid)
            print(f"  [{tag}/id{bid}] '{b.name}' — 비활성 {removed}종 → 활성 FAQ {len(left)}종 남음")


if __name__ == "__main__":
    asyncio.run(main())
