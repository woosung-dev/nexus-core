# D-1 답변의 인용을 interactions API(persona-free 백필)로 복구해 _evals.json 에 bf_citations 추가 (resume-safe)
# generate_with_rag 의 grounding 보고가 자주 비므로(페르소나 억제), 별도 검색으로 "참고한 자료(근사)"를 되살린다.
import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, "/Users/woosung/project/agy-project/nexus-core/backend")
logging.disable(logging.WARNING)

from sqlalchemy import text  # noqa: E402

from app.core.database import async_session  # noqa: E402
from app.services.rag.gemini import GeminiRAGService  # noqa: E402

BOT_ID = 8
DIR = Path("/Users/woosung/project/agy-project/nexus-core/exports/testbot_dm1")
RETRIES = 3      # 인용 방출이 비결정적이라 빈손이면 재시도
THROTTLE = 4


async def backfill_one(rag, sp, model, q):
    for _ in range(RETRIES):
        try:
            cites = await asyncio.wait_for(
                rag.search_citations(bot_id=BOT_ID, prompt=q, system_prompt=sp, model_name=model),
                timeout=120)
        except Exception:
            cites = []
        out, seen = [], set()
        for c in cites:
            t = (c.title or "").strip()
            if not t:
                continue
            key = (t, c.page_number)
            if key in seen:
                continue
            seen.add(key)
            out.append(t + (f" p.{c.page_number}" if c.page_number else ""))
        if out:
            return out
        await asyncio.sleep(THROTTLE)
    return []


async def main(tag):
    evals = DIR / (f"_evals_{tag}.json" if tag else "_evals.json")
    data = json.load(open(evals))
    results = data["results"]
    async with async_session() as s:
        row = (await s.execute(text(
            "SELECT system_prompt, llm_model FROM bots WHERE id=:b"), {"b": BOT_ID})).mappings().first()
    sp, model = row["system_prompt"], row["llm_model"]

    # 인용이 실제로 붙은 행만 완료로 보고, 빈손(bf_citations=[])은 재시도 대상에 포함
    todo = [r for r in results if not r.get("bf_citations")]
    print(f"백필 대상 {len(todo)}/{len(results)}건 (인용 보유 {len(results)-len(todo)})", flush=True)
    rag = GeminiRAGService()
    for i, r in enumerate(todo, 1):
        bf = await backfill_one(rag, sp, model, r["q"])
        r["bf_citations"] = bf
        r["bf_n"] = len(bf)
        print(f"[{i:>2}/{len(todo)}] #{r['gid']} → 백필 {len(bf)}건 {bf if bf else '(빈손)'}", flush=True)
        evals.write_text(json.dumps({"count": len(results), "results": results},
                                    ensure_ascii=False, indent=1), encoding="utf-8")
        await asyncio.sleep(THROTTLE)

    got = sum(1 for r in results if r.get("bf_n"))
    print(f"\n완료: {len(results)}건 중 인용 복구 {got}건 ({round(100*got/len(results))}%) → {evals.name}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="", help="_evals_<tag>.json 백필")
    ap.add_argument("--bot-id", type=int, default=BOT_ID, help="테스트 봇 bots.id (기본 8)")
    args = ap.parse_args()
    BOT_ID = args.bot_id  # 모듈 전역 재설정
    asyncio.run(main(args.tag))
