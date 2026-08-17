# 블레싱 나 v3(id3)·가 v3(id5)를 각자 사용자셋 90문항에 운영동일 질의 → answers_*_v3.json (순차·resume-safe)
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

DIR = Path("/Users/woosung/project/agy-project/nexus-core/exports/blessing_v3_2026-06-12")
RECS = json.load(open("/Users/woosung/project/agy-project/nexus-core/exports/_redteam_v2_data.json"))["records"]

JOBS = [
    {"name": "나", "bot_id": 3, "users": ["조화연", "신은비", "김소영"], "out": DIR / "answers_나_v3.json"},
    {"name": "가", "bot_id": 5, "users": ["미야자키시호", "김소영", "조화연"], "out": DIR / "answers_가_v3.json"},
]


def questions_for(users):
    qs = []
    for u in users:
        rs = [r for r in RECS if r["user"] == u]
        for i, r in enumerate(rs, 1):
            qs.append({"qid": f"{u}-{i:02d}", "user": u, "q": (r["q"] or "").strip()})
    return qs


async def call(rag, bot_id, sp, model, q, tries=5):
    delay = 20
    for i in range(tries):
        try:
            resp = await asyncio.wait_for(
                rag.generate_with_rag(bot_id=bot_id, prompt=q, system_prompt=sp,
                                      model_name=model, max_tokens=2048),
                timeout=90)
            return resp.answer, [c.title for c in resp.citations]
        except (Exception, asyncio.TimeoutError) as e:
            msg = str(e)
            if i == tries - 1:
                return f"[ERROR] {type(e).__name__}: {msg[:90]}", []
            await asyncio.sleep(delay if ("503" in msg or "429" in msg) else 5)
            delay = min(int(delay * 1.5), 90)


async def run_job(rag, job):
    async with async_session() as s:
        row = (await s.execute(text("SELECT name,system_prompt,llm_model FROM bots WHERE id=:b"),
                               {"b": job["bot_id"]})).first()
    name, sp, model = row[0], row[1], row[2]
    print(f"\n##### {job['name']} v3 = bot {job['bot_id']} '{name}' sp_len={len(sp)} #####", flush=True)
    qs = questions_for(job["users"])
    done = {}
    if job["out"].exists():
        done = {r["qid"]: r for r in json.load(open(job["out"])).get("results", [])
                if not r["answer"].startswith("[ERROR]")}
        print(f"  이전 {len(done)}건 재사용", flush=True)
    results = []
    for idx, item in enumerate(qs, 1):
        if item["qid"] in done:
            results.append(done[item["qid"]]); continue
        t = time.time()
        ans, cites = await call(rag, job["bot_id"], sp, model, item["q"])
        results.append({"qid": item["qid"], "user": item["user"], "q": item["q"],
                        "answer": ans, "citations": cites})
        flag = "ERR" if ans.startswith("[ERROR]") else "ok"
        print(f"  [{idx:>2}/{len(qs)}] {item['qid']} {flag} {time.time()-t:.1f}s", flush=True)
        job["out"].write_text(json.dumps({"bot": {"id": job["bot_id"], "name": name},
                                          "results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
        await asyncio.sleep(12)
    errs = sum(1 for r in results if r["answer"].startswith("[ERROR]"))
    print(f"  완료: {len(results)}건 ({errs} 오류) -> {job['out'].name}", flush=True)


async def main():
    rag = GeminiRAGService()
    for job in JOBS:
        await run_job(rag, job)
    print("\n모든 v3 질의 완료.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
