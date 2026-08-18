# genai 2.10 동기화 후 interactions.create 가 bot3(블레싱 나)에서 동작하는지 1회 스모크 검증
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

from app.services.llm.gemini import _get_genai_client  # noqa: E402
from app.services.rag.gemini import GeminiRAGService, _CITATION_INSTRUCTION  # noqa: E402
from app.core.database import async_session  # noqa: E402
from app.crud import crud_bot  # noqa: E402

BID = 3
Q = "축복 후 가정 공과금은 누가 부담하나요?"


async def main():
    import google.genai as g
    print("google-genai", g.__version__)
    client = _get_genai_client()
    rag = GeminiRAGService()
    store = await rag.ensure_store()
    async with async_session() as s:
        bot = await crud_bot.get_active_bot(s, BID)
    print(f"bot={bot.name} model={bot.llm_model} persona_len={len(bot.system_prompt)}")

    interaction = await client.aio.interactions.create(
        model=bot.llm_model,
        input=Q,
        system_instruction=(bot.system_prompt or "") + _CITATION_INSTRUCTION,
        tools=[{
            "type": "file_search",
            "file_search_store_names": [store],
            "metadata_filter": f"bot_id = {BID}",
            "top_k": 12,
        }],
    )
    dump = interaction.model_dump(mode="json", exclude_none=True)
    anns = []
    texts = []
    for step in dump.get("steps") or []:
        for content in step.get("content") or []:
            if content.get("text"):
                texts.append(content["text"])
            anns.extend(content.get("annotations") or [])
    print(f"SMOKE OK — text_len={sum(len(t) for t in texts)} annotations={len(anns)}")
    for a in anns[:3]:
        print("  ann:", json.dumps({k: a.get(k) for k in ("type", "file_name", "start_index", "end_index", "page_number")}, ensure_ascii=False))


asyncio.run(main())
