# 베이스(B_정밀정보) + 보강레이어 병합 프롬프트로 15문항 재측정 — 보강 효과 정량 확인
# 사용: cd backend && set -a; source .env; set +a; uv run python -u ../exports/_probe_boost.py
import asyncio
import json
import re
import sys
from datetime import date
from pathlib import Path

EXPORTS = "/Users/woosung/project/agy-project/nexus-core/exports"
sys.path.insert(0, "/Users/woosung/project/agy-project/nexus-core/backend")
sys.path.insert(0, EXPORTS)

import _probe_run as P  # QUESTIONS, call, MODEL, STAGING_BOT 재사용
from app.services.rag.gemini import GeminiRAGService  # noqa: E402

R3 = Path(EXPORTS) / "round3_rag"
EXP = Path("/Users/woosung/project/agy-project/nexus-core/syste-prompt-ver/_experiment")
OUT = Path(EXPORTS) / "probe_answers_boost.json"
BASE_NAME = sys.argv[1] if len(sys.argv) > 1 else "B_정밀정보"


def merged_prompt():
    base = (EXP / f"{BASE_NAME}.md").read_text(encoding="utf-8")
    layer = (R3 / "system_prompt_보강레이어.md").read_text(encoding="utf-8")
    layer = re.sub(r"^<!--.*?-->\n", "", layer, flags=re.DOTALL)
    return base.rstrip() + "\n\n---\n\n# [3주차 보강 — 신규 공문·6대오류·표기 규칙]\n\n" + layer.strip() + "\n"


async def main():
    rag = GeminiRAGService()
    sp = merged_prompt()
    cand = f"{BASE_NAME}+보강"
    print(f"재측정 후보: {cand} (prompt {len(sp)} chars)", flush=True)
    results = []
    for q in P.QUESTIONS:
        ans, cites = await P.call(rag, sp, q["q"])
        results.append({"candidate": cand, "qid": q["id"], "area": q["area"],
                        "q": q["q"], "golden": q["golden"], "answer": ans, "citations": cites})
        print(f"  Q{q['id']:>2} {q['area'][:18]:<18} len={len(ans)}", flush=True)
        await asyncio.sleep(6)
    OUT.write_text(json.dumps(
        {"meta": {"base": BASE_NAME, "layer": "보강레이어", "model": P.MODEL, "generated": str(date.today())},
         "questions": P.QUESTIONS, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {OUT} ({len(results)}건)", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
