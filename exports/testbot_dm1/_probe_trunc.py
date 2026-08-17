# 3.5-flash 잘림 원인 규명 — finish_reason·thinking 토큰 사용량을 직접 확인하는 일회성 프로브
import asyncio
import sys

sys.path.insert(0, "/Users/woosung/project/agy-project/nexus-core/backend")
import logging

logging.disable(logging.INFO)

from google.genai import types  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.database import async_session  # noqa: E402
from app.services.rag.gemini import GeminiRAGService, _FOLLOWUPS_INSTRUCTION  # noqa: E402
from app.core.config import get_settings  # noqa: E402

BOT_ID = 8
GID = 106
MODEL = "gemini-3.5-flash"


async def probe(rag, sp, store, q, max_out, label):
    s = get_settings()
    cfg = types.GenerateContentConfig(
        system_instruction=(sp or "") + _FOLLOWUPS_INSTRUCTION,
        temperature=s.RAG_TEMPERATURE,
        max_output_tokens=max_out,
        tools=[types.Tool(file_search=types.FileSearch(
            file_search_store_names=[store],
            metadata_filter=f"bot_id = {BOT_ID}",
            top_k=s.RAG_TOP_K))],
    )
    r = await rag._client.aio.models.generate_content(
        model=MODEL, contents=q, config=cfg)
    cand = r.candidates[0] if r.candidates else None
    u = r.usage_metadata
    txt = ""
    if cand and cand.content and cand.content.parts:
        txt = "".join(p.text or "" for p in cand.content.parts)
    print(f"--- {label} (max_output_tokens={max_out}) ---")
    print(f"  finish_reason : {cand.finish_reason if cand else 'NO CANDIDATE'}")
    print(f"  prompt_tokens : {u.prompt_token_count}")
    print(f"  thoughts      : {getattr(u, 'thoughts_token_count', None)}   <-- thinking 소모")
    print(f"  output_tokens : {u.candidates_token_count}")
    print(f"  total         : {u.total_token_count}")
    print(f"  답변 길이     : {len(txt)}자")
    print(f"  끝            : ...{txt.rstrip()[-40:]!r}")
    print()


async def main():
    async with async_session() as s:
        sp = (await s.execute(text("SELECT system_prompt FROM bots WHERE id=:b"),
                              {"b": BOT_ID})).scalar()
        q = (await s.execute(text("SELECT question FROM redteam_question_groups WHERE id=:g"),
                             {"g": GID})).scalar()
    rag = GeminiRAGService()
    store = await rag.ensure_store()
    print(f"질문 #{GID}: {q}\n시스템프롬프트 {len(sp)}자 · 모델 {MODEL}\n")
    await probe(rag, sp, store, q, 2048 + 256, "현행 설정")
    await asyncio.sleep(12)
    await probe(rag, sp, store, q, 8192, "한도 확대")


asyncio.run(main())
