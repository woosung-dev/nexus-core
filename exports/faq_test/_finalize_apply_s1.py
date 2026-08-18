# 최종 S1(robust auto-per-FAQ)을 전체 241건에서 재적합 → 가·나 양쪽 반영 + 검증
import os
import sys
import json
import asyncio
from pathlib import Path
from collections import defaultdict

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

DEFAULT = 0.93
CEIL = 0.965

# 전체 241건 (r1+r2+r3)
ev = []
for run in ("run_r1", "run_r2", "run_r3"):
    ev += json.load(open(ROOT / f"exports/faq_test/{run}/evaluated.json"))

by = defaultdict(list)
for r in ev:
    by[r["top1_id"]].append(r)


def s1_threshold(rows):
    neg = [r["top1_sim"] for r in rows if not r["ground_truth"]]
    pos = [r["top1_sim"] for r in rows if r["ground_truth"]]
    t = DEFAULT
    if neg:
        ceil = max(neg)
        if ceil >= DEFAULT:
            t = min(CEIL, round(ceil + 0.003, 4))
    if pos and t > min(pos) and len([s for s in neg if s >= DEFAULT]) < 2:
        t = DEFAULT
    return t


# 캐논 35종(가 등록 기준 id) → threshold
CANON = json.load(open(ROOT / "exports/faq_test/faqs_export.json"))
S1 = {f["id"]: (s1_threshold(by[f["id"]]) if f["id"] in by else DEFAULT) for f in CANON}
Q2T = {f["question"].strip(): S1[f["id"]] for f in CANON}

bumped = {fid: t for fid, t in S1.items() if abs(t - DEFAULT) > 1e-9}
print(f"=== 최종 S1 (전체 {len(ev)}건 재적합) ===")
print(f"0.93에서 상향된 FAQ {len(bumped)}종:")
qof = {f["id"]: f["question"] for f in CANON}
for fid, t in sorted(bumped.items()):
    print(f"  id{fid} → {t}   «{qof[fid][:34]}»")
from collections import Counter
print(f"분포: {dict(Counter(round(v,4) for v in S1.values()))}\n")


async def main():
    from app.models import user, bot, chat, faq, bot_kakao_channel  # noqa: F401
    from app.core.database import async_session
    from app.crud import crud_faq

    async with async_session() as s:
        for bid in (5, 3):
            fs = await crud_faq.get_active_faqs_by_bot(s, bid)
            chg = 0
            for f in fs:
                t = Q2T.get(f.question.strip(), DEFAULT)
                if abs((f.threshold or 0) - t) > 1e-9:
                    await crud_faq.update_faq(s, f, {"threshold": t})
                    chg += 1
            await s.commit()
            fs2 = await crud_faq.get_active_faqs_by_bot(s, bid)
            dist = dict(Counter(round(f.threshold, 4) for f in fs2))
            print(f"[봇{bid}] {len(fs2)}건 — 수정 {chg}건 · threshold 분포 {dist}")


if __name__ == "__main__":
    asyncio.run(main())
