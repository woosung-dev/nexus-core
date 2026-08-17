# persona vs persona-free 호출의 grounding 보고 차이를 봇3·5 × 2질문으로 즉시 비교하는 파일럿
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

PERSONA_FREE = "제공된 문서 근거로만 정확하게 답하라."
QS = [
    "축복자녀-1세 매칭확정자의 변경된 연령 기준은?",
    "축복헌금 환불 규정은 어떻게 되나요?",
]
BOTS = [5, 3]
settings = get_settings()


async def call(rag, store, bot_id, model, prompt, system_instruction, followups):
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
    resp = await rag._client.aio.models.generate_content(
        model=model, contents=build_gemini_contents(prompt, None), config=config)
    dump = resp.model_dump(mode="json", exclude_none=True)
    cand = (dump.get("candidates") or [{}])[0]
    gm = cand.get("grounding_metadata") or {}
    cm = cand.get("citation_metadata") or {}
    text = resp.text or ""
    return {
        "answer_len": len(text),
        "markers": len(_CITATION_MARKER_RE.findall(text)),
        "chunks": len(gm.get("grounding_chunks") or []),
        "supports": len(gm.get("grounding_supports") or []),
        "retr_queries": gm.get("retrieval_queries"),
        "citation_meta": len(cm.get("citations") or []),
        "head": text[:90],
    }


async def main():
    rag = GeminiRAGService()
    store = await rag.ensure_store()
    print(f"store: {store}\n")
    print(f"{'bot':>3} {'mode':<12} {'q':<3} {'ans':>4} {'chunk':>5} {'supp':>4} {'mark':>4} {'citM':>4}  head")
    print("-" * 100)
    for bid in BOTS:
        async with async_session() as s:
            bot = await crud_bot.get_active_bot(s, bid)
        assert bot is not None, f"bot {bid} 없음"
        for qi, q in enumerate(QS):
            for mode, sp, fu in [("persona", bot.system_prompt, True),
                                  ("persona_free", PERSONA_FREE, False)]:
                try:
                    r = await call(rag, store, bid, bot.llm_model, q, sp, fu)
                    print(f"{bid:>3} {mode:<12} {qi:<3} {r['answer_len']:>4} {r['chunks']:>5} "
                          f"{r['supports']:>4} {r['markers']:>4} {r['citation_meta']:>4}  {r['head']}")
                except Exception as e:
                    print(f"{bid:>3} {mode:<12} {qi:<3} ERROR {type(e).__name__}: {str(e)[:60]}")
                await asyncio.sleep(4)


asyncio.run(main())
