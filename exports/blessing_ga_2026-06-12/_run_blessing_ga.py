# 블레싱 나(bot id=3)를 조화연·신은비·김소영 90문항에 운영동일 파라미터로 질의 → blessing_ga_answers.json (resume-safe)
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "/Users/woosung/project/agy-project/nexus-core/backend")

import logging
logging.disable(logging.INFO)

from sqlalchemy import text  # noqa: E402
from app.core.database import async_session  # noqa: E402
from app.services.rag.gemini import GeminiRAGService  # noqa: E402

BOT_ID = 5
DIR = Path("/Users/woosung/project/agy-project/nexus-core/exports/blessing_ga_2026-06-12")
OUT = DIR / "blessing_ga_answers.json"
USERS = ["미야자키시호", "김소영", "조화연"]


async def call(rag, sp, model, q, tries=5):
    delay = 20
    for i in range(tries):
        try:
            resp = await asyncio.wait_for(
                rag.generate_with_rag(bot_id=BOT_ID, prompt=q, system_prompt=sp,
                                      model_name=model, max_tokens=2048),
                timeout=90)
            return resp.answer, [c.title for c in resp.citations]
        except (Exception, asyncio.TimeoutError) as e:
            msg = str(e)
            if i == tries - 1:
                return f"[ERROR] {type(e).__name__}: {msg[:90]}", []
            wait = delay if ("503" in msg or "429" in msg) else 5
            await asyncio.sleep(wait)
            delay = min(int(delay * 1.5), 90)


async def main():
    # 봇 메타 로드
    async with async_session() as s:
        row = (await s.execute(text(
            "SELECT id,name,system_prompt,llm_model FROM bots WHERE id=:b"),
            {"b": BOT_ID})).mappings().first()
    sp, model, name = row["system_prompt"], row["llm_model"], row["name"]
    print(f"bot id={BOT_ID} '{name}' model={model} sp_len={len(sp)}", flush=True)

    # 질문 로드
    questions = []
    for u in USERS:
        ds = json.load(open(DIR / f"dataset_{u}.json"))
        for it in ds["items"]:
            questions.append({"qid": it["qid"], "user": u, "q": it["q"]})
    print(f"질문 {len(questions)}건 로드", flush=True)

    # resume
    done = {}
    if OUT.exists():
        prev = json.load(open(OUT))
        done = {r["qid"]: r for r in prev.get("results", []) if not r["answer"].startswith("[ERROR]")}
        print(f"이전 결과 {len(done)}건 재사용", flush=True)

    rag = GeminiRAGService()
    results = []
    for idx, item in enumerate(questions, 1):
        if item["qid"] in done:
            results.append(done[item["qid"]])
            continue
        t = time.time()
        ans, cites = await call(rag, sp, model, item["q"])
        results.append({"qid": item["qid"], "user": item["user"], "q": item["q"],
                        "answer": ans, "citations": cites})
        flag = "ERR" if ans.startswith("[ERROR]") else "ok"
        print(f"[{idx:>2}/{len(questions)}] {item['qid']} {flag} {time.time()-t:.1f}s len={len(ans)} cites={len(cites)}", flush=True)
        # 증분 저장
        OUT.write_text(json.dumps(
            {"bot": {"id": BOT_ID, "name": name, "model": model},
             "count": len(results), "results": results},
            ensure_ascii=False, indent=1), encoding="utf-8")
        await asyncio.sleep(12)  # 분당 쿼터(RPM) 보호 — 6→12s 로 완화

    errs = sum(1 for r in results if r["answer"].startswith("[ERROR]"))
    print(f"\n완료: {len(results)}건 저장 ({errs} 오류) -> {OUT}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
