# 교란변수 분리: NEW2 = interactions(persona + followups, 인용강제 지시 없음). OLD 는 기존 캡처 재사용 → _ab2_captures.json
import os
import sys
import json
import time
import asyncio
import re
from pathlib import Path

WB = "/Users/woosung/project/agy-project/nexus-core/.claude/worktrees/agent-interactions-answer/backend"
SC = "/private/tmp/claude-501/-Users-woosung-project-agy-project-nexus-core/cf88eb6c-aabb-40e6-84d0-e477d46c9272/scratchpad"
sys.path.insert(0, WB)
for _l in (Path(WB) / ".env").read_text().splitlines():
    _l = _l.strip()
    if _l and not _l.startswith("#") and "=" in _l:
        k, v = _l.split("=", 1)
        os.environ.setdefault(k, v.strip().strip('"').strip("'"))
os.environ["DATABASE_URL"] = os.environ["DATABASE_URL"].replace("@db:", "@localhost:")
import logging  # noqa: E402
logging.disable(logging.INFO)

from app.core.config import get_settings  # noqa: E402
from app.services.rag.gemini import (  # noqa: E402
    GeminiRAGService, _FOLLOWUPS_INSTRUCTION, _split_answer_and_followups,
    _citations_from_steps, _build_interaction_input,
)
from app.core.database import async_session  # noqa: E402
from app.crud import crud_bot  # noqa: E402

OLD_CAPS = {(c["qid"], c["bot_id"]): c["OLD"] for c in json.load(open(f"{SC}/_ab_captures.json", encoding="utf-8"))}
QUESTIONS = {(q["qid"]): q for q in json.load(open(
    "/Users/woosung/project/agy-project/nexus-core/exports/rag_citation_audit/_questions.json", encoding="utf-8"))}
OUT = f"{SC}/_ab2_captures.json"
BOTS = [5, 3]
settings = get_settings()
_FU = re.compile(r"<\s*follow[\s_-]?ups\s*>", re.IGNORECASE)


async def new2(rag, bot_id, prompt, persona, model, tries=5):
    """interactions, system_instruction = persona + followups (인용강제 지시 제외)."""
    store = await rag.ensure_store()
    sysi = (persona or "") + _FOLLOWUPS_INSTRUCTION
    tool = {"type": "file_search", "file_search_store_names": [store],
            "metadata_filter": f"bot_id = {bot_id}", "top_k": settings.RAG_TOP_K}
    delay = 20
    for i in range(tries):
        try:
            t = time.perf_counter()
            it = await asyncio.wait_for(rag._client.aio.interactions.create(
                model=model, input=_build_interaction_input(prompt, None), system_instruction=sysi,
                tools=[tool], generation_config={"temperature": settings.RAG_TEMPERATURE, "max_output_tokens": 2304}), timeout=90)
            ms = (time.perf_counter() - t) * 1000
            status = getattr(it, "status", None)
            raw = it.output_text or ""
            if status in ("failed", "cancelled") or not raw.strip():
                return {"answer": "[BLOCKED]", "citations": [], "citations_full": [], "followups": [], "latency_ms": ms, "blocked": True, "fu_leak": False}
            dump = it.model_dump(mode="json", exclude_none=True)
            cits = _citations_from_steps(dump.get("steps") or [])
            ans, fups = _split_answer_and_followups(raw)
            return {"answer": ans, "citations": [c.title for c in cits],
                    "citations_full": [c.model_dump() for c in cits], "followups": fups,
                    "latency_ms": ms, "blocked": False, "fu_leak": bool(_FU.search(ans))}
        except (Exception, asyncio.TimeoutError) as e:
            if i == tries - 1:
                return {"answer": f"[ERROR] {str(e)[:80]}", "citations": [], "citations_full": [], "followups": [], "latency_ms": 0, "blocked": True, "fu_leak": False}
            await asyncio.sleep(delay if ("503" in str(e) or "429" in str(e)) else 5)
            delay = min(int(delay * 1.5), 90)


async def main():
    rag = GeminiRAGService()
    async with async_session() as s:
        bots = {b: await crud_bot.get_active_bot(s, b) for b in BOTS}
    caps = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else []
    done = {(c["qid"], c["bot_id"]) for c in caps}
    keys = [k for k in OLD_CAPS if k not in done]
    print(f"NEW2 캡처 대상 {len(keys)} (완료 {len(done)})", flush=True)
    for qid, bid in keys:
        bot = bots[bid]
        q = QUESTIONS[qid]
        n2 = await new2(rag, bid, q["question"], bot.system_prompt or "", bot.llm_model)
        caps.append({"qid": qid, "bot_id": bid, "question": q["question"],
                     "golden": q.get("golden", ""), "anchors": q.get("anchors", []),
                     "source": q.get("source"), "expected_retrieval": q.get("expected_retrieval"),
                     "OLD": OLD_CAPS[(qid, bid)], "NEW": n2})
        json.dump(caps, open(OUT, "w"), ensure_ascii=False, indent=1)
        print(f"  {bid} {qid:<10} NEW2(cit={len(n2['citations'])},leak={n2['fu_leak']},{n2['latency_ms']:.0f}ms)", flush=True)
        await asyncio.sleep(4)
    print(f"\nNEW2 캡처 완료 {len(caps)} → {OUT}", flush=True)


asyncio.run(main())
