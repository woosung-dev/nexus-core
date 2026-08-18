# 봇3·5 × 40질문에 persona/persona-free 2회 호출, raw grounding 신호를 _raw_captures.json으로 캡처(재개가능)
import os
import sys
import json
import time
import asyncio
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
for _l in (ROOT / "backend/.env").read_text().splitlines():
    _l = _l.strip()
    if _l and not _l.startswith("#") and "=" in _l:
        k, v = _l.split("=", 1)
        os.environ.setdefault(k, v.strip().strip('"').strip("'"))
os.environ["DATABASE_URL"] = os.environ["DATABASE_URL"].replace("@db:", "@localhost:")
sys.path.insert(0, str(ROOT / "backend"))
import logging  # noqa: E402
logging.disable(logging.INFO)

from google.genai import types  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.services.rag.gemini import (  # noqa: E402
    GeminiRAGService, _FOLLOWUPS_INSTRUCTION, _CITATION_MARKER_RE,
)
from app.services.llm.gemini import build_gemini_contents  # noqa: E402
from app.core.database import async_session  # noqa: E402
from app.crud import crud_bot  # noqa: E402

BOTS = [5, 3]
PERSONA_FREE = "제공된 문서 근거로만 정확하게 답하라."
QUESTIONS = json.load(open(ROOT / "exports/rag_citation_audit/_questions.json", encoding="utf-8"))
OUT = ROOT / "exports/rag_citation_audit/_raw_captures.json"
settings = get_settings()


async def call_dump(rag, store, bot_id, model, prompt, system_instruction, followups, tries=5):
    """generate_content 1회 + full dump. 운영 요청 상수를 그대로 재구성(운영 코드 무수정)."""
    merged = (system_instruction or "") + (_FOLLOWUPS_INSTRUCTION if followups else "")
    config = types.GenerateContentConfig(
        system_instruction=merged or None,
        temperature=settings.RAG_TEMPERATURE,
        max_output_tokens=1500 + (256 if followups else 0),
        tools=[types.Tool(file_search=types.FileSearch(
            file_search_store_names=[store],
            metadata_filter=f"bot_id = {bot_id}",
            top_k=settings.RAG_TOP_K))],
    )
    delay = 20
    for i in range(tries):
        try:
            resp = await asyncio.wait_for(rag._client.aio.models.generate_content(
                model=model, contents=build_gemini_contents(prompt, None), config=config), timeout=90)
            dump = resp.model_dump(mode="json", exclude_none=True)
            cand = (dump.get("candidates") or [{}])[0]
            text = resp.text or ""
            return {
                "ok": True,
                "raw_text": text,
                "markers": _CITATION_MARKER_RE.findall(text),
                "grounding_metadata": cand.get("grounding_metadata") or {},
                "citation_metadata": cand.get("citation_metadata") or {},
                "finish_reason": cand.get("finish_reason"),
            }
        except (Exception, asyncio.TimeoutError) as e:
            msg = str(e)
            if i == tries - 1:
                return {"ok": False, "error": f"{type(e).__name__}: {msg[:120]}"}
            await asyncio.sleep(delay if ("503" in msg or "429" in msg) else 5)
            delay = min(int(delay * 1.5), 90)


async def main():
    rag = GeminiRAGService()
    store = await rag.ensure_store()
    async with async_session() as s:
        bots = {}
        for bid in BOTS:
            b = await crud_bot.get_active_bot(s, bid)
            assert b is not None, f"bot {bid} 없음"
            bots[bid] = {"name": b.name, "llm_model": b.llm_model,
                         "system_prompt": b.system_prompt or ""}
    print(f"store={store} · bots={ {b: bots[b]['llm_model'] for b in BOTS} }", flush=True)

    captures = json.load(open(OUT, encoding="utf-8")) if OUT.exists() else []
    done = {(c["qid"], c["bot_id"]) for c in captures}
    total = len(BOTS) * len(QUESTIONS)
    print(f"질문 {len(QUESTIONS)} × 봇 {len(BOTS)} = {total}쌍, 완료 {len(done)}", flush=True)

    for bid in BOTS:
        bot = bots[bid]
        for q in QUESTIONS:
            if (q["qid"], bid) in done:
                continue
            t0 = time.perf_counter()
            persona = await call_dump(rag, store, bid, bot["llm_model"], q["question"],
                                      bot["system_prompt"], True)
            await asyncio.sleep(4)
            pfree = await call_dump(rag, store, bid, bot["llm_model"], q["question"],
                                    PERSONA_FREE, False)
            rec = {
                "qid": q["qid"], "bot_id": bid, "model": bot["llm_model"],
                "question": q["question"], "anchors": q["anchors"],
                "expected_retrieval": q["expected_retrieval"], "source": q["source"],
                "golden": q.get("golden", ""),
                "sp_len": len(bot["system_prompt"]),
                "persona": persona, "persona_free": pfree,
                "elapsed_s": round(time.perf_counter() - t0, 1),
            }
            captures.append(rec)
            OUT.write_text(json.dumps(captures, ensure_ascii=False, indent=1), encoding="utf-8")

            def _sig(r):
                gm = r.get("grounding_metadata") or {}
                return (len(gm.get("grounding_chunks") or []), len(gm.get("grounding_supports") or []),
                        len(r.get("markers") or [])) if r.get("ok") else "ERR"
            print(f"  {bid} {q['qid']:<10} persona={_sig(persona)} pfree={_sig(pfree)}", flush=True)
            await asyncio.sleep(4)

    print(f"\n캡처 완료 {len(captures)}쌍 → {OUT}", flush=True)


asyncio.run(main())
