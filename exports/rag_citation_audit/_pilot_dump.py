# 단일 페르소나 호출의 raw 응답을 dump해 실제 SDK grounding 필드 경로를 확인하는 파일럿
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

Q = "축복자녀-1세 매칭확정자의 변경된 연령 기준은?"  # 문서에만 있는 사실(답에 "25") = 검색 오라클
BOT = 5
OUT = ROOT / "exports/rag_citation_audit/_pilot_dump.json"


async def main():
    settings = get_settings()
    rag = GeminiRAGService()
    store = await rag.ensure_store()
    async with async_session() as s:
        bot = await crud_bot.get_active_bot(s, BOT)

    merged = (bot.system_prompt or "") + _FOLLOWUPS_INSTRUCTION
    config = types.GenerateContentConfig(
        system_instruction=merged or None,
        temperature=settings.RAG_TEMPERATURE,
        max_output_tokens=1500 + 256,
        tools=[types.Tool(file_search=types.FileSearch(
            file_search_store_names=[store],
            metadata_filter=f"bot_id = {BOT}",
            top_k=settings.RAG_TOP_K))],
    )
    resp = await rag._client.aio.models.generate_content(
        model=bot.llm_model, contents=build_gemini_contents(Q, None), config=config)
    dump = resp.model_dump(mode="json", exclude_none=True)
    OUT.write_text(json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8")

    text = resp.text or ""
    cand = (dump.get("candidates") or [{}])[0]
    gm = cand.get("grounding_metadata") or {}
    cm = cand.get("citation_metadata") or {}
    print("=" * 70)
    print("model        :", bot.llm_model)
    print("answer_len   :", len(text), "| has '25':", "25" in text)
    print("inline mkrs  :", _CITATION_MARKER_RE.findall(text)[:12])
    print("dump top keys:", list(dump.keys()))
    print("candidate keys:", list(cand.keys()))
    print("grnd_meta keys:", list(gm.keys()))
    print("  grounding_chunks  :", len(gm.get("grounding_chunks") or []))
    print("  grounding_supports:", len(gm.get("grounding_supports") or []))
    print("  retrieval_queries :", gm.get("retrieval_queries"))
    print("  retrieval_metadata:", gm.get("retrieval_metadata"))
    print("citation_metadata cits:", len(cm.get("citations") or []))
    gc = gm.get("grounding_chunks") or []
    if gc:
        print("chunk[0]   :", json.dumps(gc[0], ensure_ascii=False)[:600])
    gs = gm.get("grounding_supports") or []
    if gs:
        print("support[0] :", json.dumps(gs[0], ensure_ascii=False)[:600])
    if cm.get("citations"):
        print("citation[0]:", json.dumps(cm["citations"][0], ensure_ascii=False)[:600])
    print("=" * 70)
    print("answer head:", text[:400])


asyncio.run(main())
