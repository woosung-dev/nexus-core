# 감정의 객관화 + 행동의 경계선(거리두기=안전장치) 기법 — 본문 외과편집 base vs edited 검증 프로브
"""
정밀(2주차 C)이 칭찬받은 기법: 감정 올라올 때 자책 대신 '잠시 흔들리고 있구나' 객관화 +
물리적 거리두기를 '축복을 지키기 위한 안전장치'로 정의해 실천 단계로 제시.
두 봇 공통의 '끌림·고통은 인정하되 권장하지 않는다' 줄에 본문 통합한 edited vs base 를
유혹·충동 질문 + 일반(회귀가드)에 멀티샘플 비교. dev 읽기전용, DB 미적용.
"""

import asyncio
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))
OUT = Path(__file__).resolve().parent / "프로브_결과.json"

ANCHOR = "끌림·고통은 인정하되 권장하지 않는다. 폭력·강요·통제가 있으면 위기(안전) 우선."
NEW = (
    "끌림·고통은 인정하되 권장하지 않는다. 감정·충동이 올라올 때는 억누르거나 자책하게 두지 말고 "
    "'지금 잠시 흔들리고 있구나'라고 객관적으로 인지하도록 돕고(감정의 객관화), 물리적 거리두기 같은 "
    "구체적 행동의 경계선을 '축복을 지키기 위한 최소한의 안전장치'로 제시해 실천하기 쉬운 단계로 준다. "
    "폭력·강요·통제가 있으면 위기(안전) 우선."
)

QUESTIONS = [
    ("T1", "유혹", "교회에서 알게 된 이성에게 자꾸 마음이 가요. 저는 축복받은 가정인데 이런 감정이 들어 괴롭고 제 자신이 미워요."),
    ("T2", "유혹", "배우자가 있는데도 다른 사람에게 자꾸 끌립니다. 어떻게 마음을 다잡아야 할까요?"),
    ("T3", "충동", "음란물을 끊고 싶은데 자꾸 보게 돼요. 볼 때마다 자책만 늘어요."),
    ("G1", "일반", "축복의 의미가 뭐예요?"),
]
SAMPLES = 3

# 감정의 객관화(인지적 재구성) 신호
OBJ = re.compile(r"흔들리|객관적|객관화|알아차|바라보|관찰하|인지하|한 발 (떨어|물러)")
# 행동의 경계선(거리두기=안전장치) 신호
BOUND = re.compile(r"거리\s*두|거리두기|경계선|안전장치|물리적")


async def main():
    import asyncpg
    from app.core.config import get_settings
    from app.services.rag.gemini import GeminiRAGService

    url = str(get_settings().DATABASE_URL).replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(url)
    base = {r["id"]: r["system_prompt"] for r in await conn.fetch("SELECT id, system_prompt FROM bots WHERE id IN (3,5)")}
    await conn.close()

    prompts = {}
    for bid in (5, 3):
        assert ANCHOR in base[bid], f"id{bid} 편집 대상 줄 미발견 — 프롬프트 변경됨?"
        prompts[bid] = {"base": base[bid], "edited": base[bid].replace(ANCHOR, NEW)}

    svc = GeminiRAGService()
    results = []
    total = 2 * 2 * len(QUESTIONS) * SAMPLES
    n = 0
    for bid in (5, 3):
        for variant in ("base", "edited"):
            sp = prompts[bid][variant]
            for qid, qtype, q in QUESTIONS:
                for s in range(SAMPLES):
                    n += 1
                    print(f"[{n}/{total}] id{bid} {variant} {qid} s{s}", flush=True)
                    try:
                        r = await svc.generate_with_rag(bot_id=bid, prompt=q, system_prompt=sp, model_name="gemini-3.1-flash-lite")
                        ans = r.answer
                    except Exception as e:
                        ans = f"[ERROR] {type(e).__name__}: {e}"
                    results.append({
                        "bot": bid, "variant": variant, "qid": qid, "qtype": qtype, "sample": s,
                        "obj": bool(OBJ.search(ans)), "bound": bool(BOUND.search(ans)),
                        "len": len(ans), "answer": ans,
                    })
                    await asyncio.sleep(2)

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")

    def rate(bot, variant, qtypes, field):
        rows = [r for r in results if r["bot"] == bot and r["variant"] == variant and r["qtype"] in qtypes]
        return sum(r[field] for r in rows), len(rows)

    print("\n========== 집계 (감정객관화 / 행동경계선, 유혹·충동 문항) ==========")
    for bot in (5, 3):
        label = "가/정밀" if bot == 5 else "나/통합"
        bo, bn = rate(bot, "base", {"유혹", "충동"}, "obj")
        eo, en = rate(bot, "edited", {"유혹", "충동"}, "obj")
        bb, _ = rate(bot, "base", {"유혹", "충동"}, "bound")
        eb, _ = rate(bot, "edited", {"유혹", "충동"}, "bound")
        print(f"■ {label}(id{bot})")
        print(f"   감정객관화: base {bo}/{bn} → edited {eo}/{en}")
        print(f"   행동경계선: base {bb}/{bn} → edited {eb}/{en}")


if __name__ == "__main__":
    main() if False else asyncio.run(main())
