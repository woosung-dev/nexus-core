# 확정 감도 적용 — 가(id5) threshold 일괄수정 + 나(id3) 신규등록 (전역 0.93, 과흡인 4종 0.96)
import os
import sys
import json
import asyncio
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
for _l in (ROOT / "backend/.env").read_text().splitlines():
    _l = _l.strip()
    if _l and not _l.startswith("#") and "=" in _l:
        k, v = _l.split("=", 1)
        os.environ.setdefault(k, v.strip().strip('"').strip("'"))
if "DATABASE_URL" in os.environ:
    os.environ["DATABASE_URL"] = os.environ["DATABASE_URL"].replace("@db:", "@localhost:")
sys.path.insert(0, str(ROOT / "backend"))
import logging  # noqa: E402
logging.disable(logging.INFO)

GLOBAL_T = 0.93
ATTRACTOR_T = 0.96
ATTRACTOR_IDS = {16, 19, 26, 30}  # faqs_export(=가 등록) 기준 id: 양육·1세축복·금식실수·수련회호감

CANON = json.load(open(ROOT / "exports/faq_test/faqs_export.json"))
ATTRACTOR_Q = {f["question"].strip() for f in CANON if f["id"] in ATTRACTOR_IDS}


def thr(question):
    return ATTRACTOR_T if question.strip() in ATTRACTOR_Q else GLOBAL_T


async def main():
    from app.models import user, bot, chat, faq, bot_kakao_channel  # noqa: F401
    from app.core.database import async_session
    from app.crud import crud_bot, crud_faq
    from app.services.faq_service import create_faq_with_embedding

    print(f"정책: 전역 {GLOBAL_T} / 과흡인 4종 {ATTRACTOR_T}")
    print(f"과흡인 질문:\n  - " + "\n  - ".join(q[:40] for q in ATTRACTOR_Q) + "\n")

    async with async_session() as s:
        # ── 가(id5): 기존 35건 threshold 일괄 수정 ──
        b5 = await crud_bot.get_active_bot(s, 5)
        faqs5 = await crud_faq.get_active_faqs_by_bot(s, 5)
        chg = 0
        for f in faqs5:
            t = thr(f.question)
            if abs((f.threshold or 0) - t) > 1e-9:
                await crud_faq.update_faq(s, f, {"threshold": t})
                chg += 1
        await s.commit()
        cnt96 = sum(1 for f in faqs5 if thr(f.question) == ATTRACTOR_T)
        print(f"[가 id5] {len(faqs5)}건 — threshold 수정 {chg}건 (0.96 {cnt96}건 / 0.93 {len(faqs5)-cnt96}건)")

        # ── 나(id3): 신규 등록(중복 skip) ──
        b3 = await crud_bot.get_active_bot(s, 3)
        existing3 = {f.question.strip() for f in await crud_faq.get_active_faqs_by_bot(s, 3)}
        reg, skip = 0, 0
        for item in CANON:
            q, a = item["question"], item["answer"]
            if q.strip() in existing3:
                skip += 1
                continue
            await create_faq_with_embedding(session=s, bot_id=3, question=q, answer=a, threshold=thr(q))
            await s.commit()
            reg += 1
            await asyncio.sleep(0.25)
        faqs3 = await crud_faq.get_active_faqs_by_bot(s, 3)
        cnt96_3 = sum(1 for f in faqs3 if thr(f.question) == ATTRACTOR_T)
        print(f"[나 id3] 신규등록 {reg} · 스킵 {skip} → 활성 FAQ {len(faqs3)}건 (0.96 {cnt96_3}건 / 0.93 {len(faqs3)-cnt96_3}건)")

        # ── 검증: 양쪽 threshold 분포 ──
        from collections import Counter
        print("\n검증 — threshold 분포")
        for bid in (5, 3):
            fs = await crud_faq.get_active_faqs_by_bot(s, bid)
            print(f"  봇{bid}: {dict(Counter(round(f.threshold, 2) for f in fs))}")


if __name__ == "__main__":
    asyncio.run(main())
