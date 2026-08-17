# 관대S1(base0.90) per-FAQ threshold를 dev(가/나) 또는 live(C/D)에 반영. argv: dev|live
import os
import sys
import json
import asyncio
from pathlib import Path
from collections import Counter

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
TARGET = sys.argv[1]  # "dev" or "live"
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

# 관대S1 맵 (canonical id → threshold)
L = {int(k): v for k, v in json.load(open(ROOT / "exports/faq_test/lenient_s1_map.json")).items()}
CANON = json.load(open(ROOT / "exports/faq_test/faqs_export.json"))
Q2T = {f["question"].strip(): L.get(f["id"], 0.90) for f in CANON}


async def main():
    from app.models import user, bot, chat, faq, bot_kakao_channel  # noqa: F401
    from app.core.database import async_session
    from app.crud import crud_bot, crud_faq

    print(f"대상: {TARGET}  봇 {BOTS}")
    async with async_session() as s:
        for bid, tag in BOTS.items():
            b = await crud_bot.get_active_bot(s, bid)
            assert b, f"봇 {bid} 없음"
            fs = await crud_faq.get_active_faqs_by_bot(s, bid)
            chg = 0
            for f in fs:
                t = Q2T.get(f.question.strip(), 0.90)
                if abs((f.threshold or 0) - t) > 1e-9:
                    await crud_faq.update_faq(s, f, {"threshold": t})
                    chg += 1
            await s.commit()
            fs2 = await crud_faq.get_active_faqs_by_bot(s, bid)
            dist = dict(sorted(Counter(round(f.threshold, 3) for f in fs2).items()))
            print(f"  [{tag}/id{bid}] '{b.name}' {len(fs2)}건 수정 {chg} · 분포 {dist}")


if __name__ == "__main__":
    asyncio.run(main())
