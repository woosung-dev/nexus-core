# A/B 캡처: OLD(generate_content) vs NEW(interactions) 답변·인용·followups·지연을 40Q×봇3·5로 수집(재개가능)
import os
import sys
import json
import time
import asyncio
import re
from pathlib import Path

WB = "/Users/woosung/project/agy-project/nexus-core/.claude/worktrees/agent-interactions-answer/backend"
MAIN = "/Users/woosung/project/agy-project/nexus-core"
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

from google.genai import types  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.services.rag.gemini import (  # noqa: E402
    GeminiRAGService, _FOLLOWUPS_INSTRUCTION, _split_answer_and_followups,
)
from app.services.llm.gemini import build_gemini_contents, is_blocked, safe_response_text  # noqa: E402
from app.core.database import async_session  # noqa: E402
from app.crud import crud_bot  # noqa: E402

BOTS = [5, 3]
QUESTIONS = json.load(open(f"{MAIN}/exports/rag_citation_audit/_questions.json", encoding="utf-8"))
OUT = f"{SC}/_ab_captures.json"
settings = get_settings()
_FU_BLOCK = re.compile(r"<\s*follow[\s_-]?ups\s*>", re.IGNORECASE)


async def old_path(rag, bot_id, prompt, persona, model, tries=5):
    """OLD: generate_content + persona + _FOLLOWUPS_INSTRUCTION + grounding_chunks 파싱(M2 이전 동작 재구성)."""
    store = await rag.ensure_store()
    cfg = types.GenerateContentConfig(
        system_instruction=(persona or "") + _FOLLOWUPS_INSTRUCTION,
        temperature=settings.RAG_TEMPERATURE, max_output_tokens=1500 + 256,
        tools=[types.Tool(file_search=types.FileSearch(
            file_search_store_names=[store], metadata_filter=f"bot_id = {bot_id}", top_k=settings.RAG_TOP_K))])
    delay = 20
    for i in range(tries):
        try:
            t = time.perf_counter()
            resp = await asyncio.wait_for(rag._client.aio.models.generate_content(
                model=model, contents=build_gemini_contents(prompt, None), config=cfg), timeout=90)
            ms = (time.perf_counter() - t) * 1000
            if is_blocked(resp):
                return {"answer": "[BLOCKED]", "citations": [], "followups": [], "latency_ms": ms, "blocked": True}
            cits = []
            try:
                g = resp.candidates[0].grounding_metadata
                if g and g.grounding_chunks:
                    for c in g.grounding_chunks:
                        if c.retrieved_context:
                            cits.append(c.retrieved_context.title)
            except (AttributeError, IndexError):
                pass
            ans, fups = _split_answer_and_followups(safe_response_text(resp))
            return {"answer": ans, "citations": cits, "followups": fups, "latency_ms": ms, "blocked": False}
        except (Exception, asyncio.TimeoutError) as e:
            if i == tries - 1:
                return {"answer": f"[ERROR] {str(e)[:80]}", "citations": [], "followups": [], "latency_ms": 0, "blocked": True}
            await asyncio.sleep(delay if ("503" in str(e) or "429" in str(e)) else 5)
            delay = min(int(delay * 1.5), 90)


async def new_path(rag, bot_id, prompt, persona, model, tries=5):
    """NEW: 마이그레이션된 interactions 기반 generate_with_rag(답변+정확인용+followups 단일 호출)."""
    delay = 20
    for i in range(tries):
        try:
            t = time.perf_counter()
            r = await asyncio.wait_for(rag.generate_with_rag(
                bot_id=bot_id, prompt=prompt, system_prompt=persona, model_name=model), timeout=90)
            ms = (time.perf_counter() - t) * 1000
            blocked = r.answer.startswith("죄송") and not r.citations and not r.followups
            return {"answer": r.answer, "citations": [c.title for c in r.citations],
                    "citations_full": [c.model_dump() for c in r.citations],
                    "followups": r.followups, "latency_ms": ms,
                    "blocked": blocked, "fu_leak": bool(_FU_BLOCK.search(r.answer))}
        except (Exception, asyncio.TimeoutError) as e:
            if i == tries - 1:
                return {"answer": f"[ERROR] {str(e)[:80]}", "citations": [], "citations_full": [],
                        "followups": [], "latency_ms": 0, "blocked": True, "fu_leak": False}
            await asyncio.sleep(delay if ("503" in str(e) or "429" in str(e)) else 5)
            delay = min(int(delay * 1.5), 90)


async def main():
    rag = GeminiRAGService()
    async with async_session() as s:
        bots = {b: await crud_bot.get_active_bot(s, b) for b in BOTS}
    caps = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else []
    done = {(c["qid"], c["bot_id"]) for c in caps}
    print(f"질문 {len(QUESTIONS)} × 봇 {len(BOTS)} = {len(QUESTIONS)*len(BOTS)}, 완료 {len(done)}", flush=True)
    for bid in BOTS:
        bot = bots[bid]
        persona, model = bot.system_prompt or "", bot.llm_model
        for q in QUESTIONS:
            if (q["qid"], bid) in done:
                continue
            old = await old_path(rag, bid, q["question"], persona, model)
            await asyncio.sleep(3)
            new = await new_path(rag, bid, q["question"], persona, model)
            rec = {"qid": q["qid"], "bot_id": bid, "question": q["question"],
                   "golden": q.get("golden", ""), "anchors": q.get("anchors", []),
                   "source": q.get("source"), "expected_retrieval": q.get("expected_retrieval"),
                   "OLD": old, "NEW": new}
            caps.append(rec)
            json.dump(caps, open(OUT, "w"), ensure_ascii=False, indent=1)
            print(f"  {bid} {q['qid']:<10} OLD(cit={len(old['citations'])},{old['latency_ms']:.0f}ms) "
                  f"NEW(cit={len(new['citations'])},leak={new['fu_leak']},{new['latency_ms']:.0f}ms)", flush=True)
            await asyncio.sleep(3)
    print(f"\n캡처 완료 {len(caps)} → {OUT}", flush=True)


asyncio.run(main())
