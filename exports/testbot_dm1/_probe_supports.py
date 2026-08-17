# D-1(bot 8)+3.5-flash-lite 원시 grounding_metadata 를 덤프해 grounding_supports 존재 여부를 확인하는 프로브
import asyncio
import json
import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, "/Users/woosung/project/agy-project/nexus-core/backend")
logging.disable(logging.INFO)

from google.genai import types  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import async_session  # noqa: E402
from app.services.rag.gemini import GeminiRAGService  # noqa: E402

BOT_ID = 8
MODEL = "gemini-3.5-flash-lite"
DIR = Path("/Users/woosung/project/agy-project/nexus-core/exports/testbot_dm1")
OUT = DIR / "_probe_supports.json"
N = 5  # 위험도 상 앞쪽 N 문항


async def main():
    async with async_session() as s:
        bot = (await s.execute(text(
            "SELECT system_prompt FROM bots WHERE id=:b"), {"b": BOT_ID})).mappings().first()
        rows = (await s.execute(text(
            "SELECT id, question FROM redteam_question_groups WHERE risk='상' ORDER BY id LIMIT :n"),
            {"n": N})).mappings().all()

    sp = bot["system_prompt"]
    rag = GeminiRAGService()
    store = await rag.ensure_store()
    settings = get_settings()
    client = rag._client

    config = types.GenerateContentConfig(
        system_instruction=sp,
        temperature=settings.RAG_TEMPERATURE,
        max_output_tokens=2048,
        tools=[types.Tool(file_search=types.FileSearch(
            file_search_store_names=[store],
            metadata_filter=f"bot_id = {BOT_ID}",
            top_k=settings.RAG_TOP_K,
        ))],
    )

    out = []
    for r in rows:
        q = r["question"]
        try:
            resp = await asyncio.wait_for(client.aio.models.generate_content(
                model=MODEL, contents=q, config=config), timeout=180)
        except Exception as e:
            print(f"[{r['id']}] ERROR {type(e).__name__}: {str(e)[:160]}")
            out.append({"gid": r["id"], "q": q, "error": str(e)[:300]})
            continue

        cand = resp.candidates[0]
        gm = cand.grounding_metadata
        raw_text = resp.text or ""

        chunks = []
        for gc in (gm.grounding_chunks or []) if gm else []:
            rc = gc.retrieved_context
            chunks.append({
                "title": getattr(rc, "title", None),
                "page": getattr(rc, "page_number", None),
                "text": getattr(rc, "text", None),
            } if rc else None)

        supports = []
        for sup in (gm.grounding_supports or []) if gm else []:
            seg = sup.segment
            supports.append({
                "start": getattr(seg, "start_index", None) if seg else None,
                "end": getattr(seg, "end_index", None) if seg else None,
                "text": getattr(seg, "text", None) if seg else None,
                "chunk_idx": sup.grounding_chunk_indices,
                "conf": sup.confidence_scores,
            })

        markers = re.findall(r"\[[\d.,\s]+\]", raw_text)
        print(f"[{r['id']}] answer={len(raw_text)}자 chunks={len(chunks)} "
              f"supports={len(supports)} markers={len(markers)} finish={cand.finish_reason}")

        out.append({
            "gid": r["id"], "q": q, "answer": raw_text,
            "finish_reason": str(cand.finish_reason),
            "markers": markers[:20],
            "chunks": chunks, "supports": supports,
        })
        await asyncio.sleep(8)

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"\n저장: {OUT}")


asyncio.run(main())
