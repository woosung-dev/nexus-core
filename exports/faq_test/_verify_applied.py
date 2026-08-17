# 확정 per-FAQ 정책 검증 — 라벨데이터 혼동행렬(플랫0.93 vs per-FAQ) + 라이브 override 스팟체크
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

ATTRACTOR_IDS = {16, 19, 26, 30}
GLOBAL_T, ATTRACTOR_T = 0.93, 0.96


def cm(records, decide):
    TP = FP = FN = TN = 0
    for r in records:
        fire = decide(r)
        if r["ground_truth"]:
            TP += fire; FN += (not fire)
        else:
            FP += fire; TN += (not fire)
    p = TP / (TP + FP) if TP + FP else 1.0
    rec = TP / (TP + FN) if TP + FN else 1.0
    return TP, FP, FN, TN, p, rec


async def main():
    ev = json.load(open(ROOT / "exports/faq_test/evaluated_all.json"))
    flat = lambda r: r["top1_sim"] >= GLOBAL_T
    perfaq = lambda r: r["top1_sim"] >= (ATTRACTOR_T if r["top1_id"] in ATTRACTOR_IDS else GLOBAL_T)

    print("=== 라벨데이터(143) 혼동행렬 비교 ===")
    for name, dec in [("플랫 0.93", flat), ("per-FAQ(0.93/0.96)", perfaq)]:
        TP, FP, FN, TN, p, r = cm(ev, dec)
        print(f"  {name:22}: 오발동FP={FP:2d}  놓침FN={FN:2d}  정밀={p:.3f}  재현={r:.3f}")

    # 라이브 스팟체크 — 실제 search_faq_override(가 id5, per-FAQ threshold 반영됨)
    from app.models import user, bot, chat, faq, bot_kakao_channel  # noqa: F401
    from app.core.database import async_session
    from app.services.faq_service import search_faq_override

    spot = [
        ("축복정리를 하게 되면 절차가 보통 어떤 식으로 흘러가나요?", "발동기대(정리절차 0.93)"),
        ("입교한 지 얼마 안 된 1세 남자입니다. 미혼 1세 축복을 받고 싶은데, 솔직히 제가 입교 전에 동거하고 관계도 가졌던 적이 있어요. 그래도 그냥 후보자 교육 받고 진행하면 되나요?", "차단기대(id19 과흡인→0.96)"),
        ("축복정리를 신청하려는데 비용이 드나요? 정리헌금 같은 게 따로 있나요?", "차단기대(비용→정리 0.93 미달)"),
    ]
    print("\n=== 라이브 search_faq_override (가 id5, 적용된 per-FAQ threshold) ===")
    async with async_session() as s:
        for q, expect in spot:
            m = await search_faq_override(s, 5, q)
            res = f"발동 id={m.faq_id} sim={m.similarity}" if m else "미발동(LLM 폴백)"
            print(f"  [{expect}]\n     Q: {q[:46]}\n     → {res}")


if __name__ == "__main__":
    asyncio.run(main())
