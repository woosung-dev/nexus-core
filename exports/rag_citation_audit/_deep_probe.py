# 심층검증: (A) 사이드패스가 실제 출처문서를 집어내는가 (B) persona를 system_instruction 밖(대화턴)으로 빼면 grounding 복구되는가
import os
import sys
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
from app.services.rag.gemini import GeminiRAGService  # noqa: E402
from app.services.llm.gemini import build_gemini_contents  # noqa: E402
from app.core.database import async_session  # noqa: E402
from app.crud import crud_bot  # noqa: E402

BID = 5
settings = get_settings()


async def grounding_for(rag, store, model, prompt, system_instruction, history):
    config = types.GenerateContentConfig(
        system_instruction=system_instruction or None,
        temperature=0.0, max_output_tokens=800,
        tools=[types.Tool(file_search=types.FileSearch(
            file_search_store_names=[store], metadata_filter=f"bot_id = {BID}", top_k=settings.RAG_TOP_K))])
    resp = await rag._client.aio.models.generate_content(
        model=model, contents=build_gemini_contents(prompt, history), config=config)
    cand = (resp.model_dump(exclude_none=True).get("candidates") or [{}])[0]
    gm = cand.get("grounding_metadata") or {}
    chunks = gm.get("grounding_chunks") or []
    texts = " ".join((c.get("retrieved_context") or {}).get("text", "") for c in chunks)
    return len(chunks), texts, (resp.text or "")


async def main():
    rag = GeminiRAGService()
    store = await rag.ensure_store()
    async with async_session() as s:
        bot = await crud_bot.get_active_bot(s, BID)
    sp, model = bot.system_prompt or "", bot.llm_model

    print("=== (A) 사이드패스가 실제 출처문서(깨끗앵커 포함 청크)를 집어내는가 ===")
    A = [("축복을 받고 가정회비를 내는 이유가 무엇인가요?", ["15,000", "3,000"]),
         ("축복식 드레스와 턱시도는 어디서 구매하나요?", ["크리스티나", "Kristina"])]
    for q, anchors in A:
        cits = await rag.search_citations(bot_id=BID, prompt=q, model_name=model)
        joined = " ".join((c.content or "") + " " + (c.title or "") for c in cits)
        hit = [a for a in anchors if a in joined]
        print(f"  q='{q[:22]}' 사이드패스인용={len(cits)} 청크내 앵커={hit} "
              f"{'✓ 실제 출처 포함' if hit else '✗ 앵커 미포함'}")
        for c in cits[:3]:
            print(f"      - {c.title}")
        await asyncio.sleep(4)

    print("\n=== (B) persona 위치별 grounding (system_instruction vs 대화턴 vs 없음) ===")
    qs = ["축복을 받고 가정회비를 내는 이유가 무엇인가요?", "축복식 드레스와 턱시도는 어디서 구매하나요?"]
    for q in qs:
        n_sys, _, _ = await grounding_for(rag, store, model, q, sp, None)
        await asyncio.sleep(4)
        hist = [{"role": "user", "content": sp}, {"role": "model", "content": "네, 지침을 숙지했습니다."}]
        n_hist, _, _ = await grounding_for(rag, store, model, q, None, hist)
        await asyncio.sleep(4)
        n_none, _, _ = await grounding_for(rag, store, model, q, None, None)
        await asyncio.sleep(4)
        print(f"  q='{q[:22]}' | system_instruction={n_sys}  대화턴persona={n_hist}  persona없음={n_none}")


asyncio.run(main())
