# persona vs followup-suffix 2×2로 grounding 보고 억제의 진짜 원인을 분리하는 프로브(봇5, 2질문)
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
from app.services.rag.gemini import GeminiRAGService, _FOLLOWUPS_INSTRUCTION  # noqa: E402
from app.services.llm.gemini import build_gemini_contents  # noqa: E402
from app.core.database import async_session  # noqa: E402
from app.crud import crud_bot  # noqa: E402

QS = ["축복자녀-1세 매칭확정자의 변경된 연령 기준은?", "축복을 받고 가정회비를 내는 이유가 무엇인가요?"]
BID = 5
settings = get_settings()


async def call(rag, store, model, prompt, sp, followups, tries=6):
    merged = (sp or "") + (_FOLLOWUPS_INSTRUCTION if followups else "")
    config = types.GenerateContentConfig(
        system_instruction=merged or None, temperature=settings.RAG_TEMPERATURE,
        max_output_tokens=1500 + (256 if followups else 0),
        tools=[types.Tool(file_search=types.FileSearch(
            file_search_store_names=[store], metadata_filter=f"bot_id = {BID}", top_k=settings.RAG_TOP_K))])
    delay = 15
    for i in range(tries):
        try:
            resp = await asyncio.wait_for(rag._client.aio.models.generate_content(
                model=model, contents=build_gemini_contents(prompt, None), config=config), timeout=90)
            cand = (resp.model_dump(exclude_none=True).get("candidates") or [{}])[0]
            gm = cand.get("grounding_metadata") or {}
            return len(gm.get("grounding_chunks") or []), len(gm.get("grounding_supports") or [])
        except (Exception, asyncio.TimeoutError) as e:
            if i == tries - 1:
                return f"ERR:{str(e)[:40]}", ""
            await asyncio.sleep(delay); delay = min(int(delay * 1.5), 90)


async def main():
    rag = GeminiRAGService()
    store = await rag.ensure_store()
    async with async_session() as s:
        bot = await crud_bot.get_active_bot(s, BID)
    assert bot is not None
    sp = bot.system_prompt or ""
    print(f"bot{BID} {bot.name} model={bot.llm_model}\n")
    print(f"{'q':<3} {'condition':<26} {'chunks':>6} {'supports':>8}")
    print("-" * 50)
    conds = [
        ("persona + followups (운영 비스트림)", sp, True),
        ("persona, NO followups (운영 스트림)", sp, False),
        ("persona-free + followups", "제공된 문서 근거로만 정확하게 답하라.", True),
        ("persona-free, no followups", "제공된 문서 근거로만 정확하게 답하라.", False),
    ]
    for qi, q in enumerate(QS):
        for label, s_, fu in conds:
            ch, su = await call(rag, store, bot.llm_model, q, s_, fu)
            print(f"{qi:<3} {label:<26} {str(ch):>6} {str(su):>8}", flush=True)
            await asyncio.sleep(6)
        print()


asyncio.run(main())
