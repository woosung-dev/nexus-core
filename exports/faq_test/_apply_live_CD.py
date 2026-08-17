# 라이브(Neon) C(id6)·D(id7)에 FAQ 35종 + 최종 S1 threshold 등록
import os
import sys
import json
import asyncio
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
lines = (ROOT / "backend/.env").read_text().splitlines()
neon = next(s.split("=", 1)[1].strip() for s in (l.strip().lstrip("#").strip() for l in lines)
            if s.startswith("DATABASE_URL=") and "neon.tech" in s)
for l in lines:
    l = l.strip()
    if l and not l.startswith("#") and "=" in l:
        k, v = l.split("=", 1)
        os.environ[k] = v.strip().strip('"').strip("'")
os.environ["DATABASE_URL"] = neon  # ← 라이브(Neon)
sys.path.insert(0, str(ROOT / "backend"))
import logging  # noqa: E402
logging.disable(logging.INFO)

TARGETS = {6: "C", 7: "D"}  # 라이브 봇 id → 표기
DEFAULT = 0.93

# 최종 S1 맵 (전체 241건 재적합)
ev = []
for run in ("run_r1", "run_r2", "run_r3"):
    ev += json.load(open(ROOT / f"exports/faq_test/{run}/evaluated.json"))
by = defaultdict(list)
for r in ev:
    by[r["top1_id"]].append(r)


def s1(rows):
    neg = [r["top1_sim"] for r in rows if not r["ground_truth"]]
    pos = [r["top1_sim"] for r in rows if r["ground_truth"]]
    t = DEFAULT
    if neg and max(neg) >= DEFAULT:
        t = min(0.965, round(max(neg) + 0.003, 4))
    if pos and t > min(pos) and len([x for x in neg if x >= DEFAULT]) < 2:
        t = DEFAULT
    return t


CANON = json.load(open(ROOT / "exports/faq_test/faqs_export.json"))
S1 = {f["id"]: (s1(by[f["id"]]) if f["id"] in by else DEFAULT) for f in CANON}
Q2T = {f["question"].strip(): S1[f["id"]] for f in CANON}


async def main():
    from app.models import user, bot, chat, faq, bot_kakao_channel  # noqa: F401
    from app.core.database import async_session
    from app.crud import crud_bot, crud_faq
    from app.services.faq_service import create_faq_with_embedding

    async with async_session() as s:
        # 안전: 대상 봇 정체 확인
        for bid, tag in TARGETS.items():
            b = await crud_bot.get_active_bot(s, bid)
            assert b and ("(" + tag + ")" in (b.name or "") or b.name.endswith(tag)), \
                f"봇 id={bid} 정체 불일치: '{b.name if b else None}'"
            print(f"확인: 라이브 id={bid} '{b.name}' (use_rag={b.use_rag})")
        print()

        for bid, tag in TARGETS.items():
            existing = {f.question.strip() for f in await crud_faq.get_active_faqs_by_bot(s, bid)}
            reg, skip = 0, 0
            for item in CANON:
                q, a = item["question"], item["answer"]
                if q.strip() in existing:
                    skip += 1
                    continue
                await create_faq_with_embedding(session=s, bot_id=bid, question=q, answer=a, threshold=Q2T[q.strip()])
                await s.commit()
                reg += 1
                await asyncio.sleep(0.25)
            fs = await crud_faq.get_active_faqs_by_bot(s, bid)
            dist = dict(Counter(round(f.threshold, 4) for f in fs))
            vec_ok = all(f.question_vector is not None for f in fs)
            print(f"[라이브 {tag}/id{bid}] 등록 {reg}·스킵 {skip} → 활성 FAQ {len(fs)}건, 벡터 OK={vec_ok}")
            print(f"    threshold 분포: {dist}")


if __name__ == "__main__":
    asyncio.run(main())
