# interactions.create(신 API)가 persona system_instruction에서도 annotations(인용)를 주는지 검증
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
from app.services.rag.gemini import GeminiRAGService  # noqa: E402
from app.core.database import async_session  # noqa: E402
from app.crud import crud_bot  # noqa: E402

BID = 5
Q = "축복식 드레스와 턱시도는 어디서 구매하나요?"  # 깨끗앵커(크리스티나 한) 포함 질문


def extract_annotations(dump):
    """interaction.steps[].content[].annotations 를 평탄화."""
    anns = []
    for step in dump.get("steps", []) or []:
        for content in (step.get("content") or []):
            for a in (content.get("annotations") or []):
                anns.append(a)
    return anns


async def call(client, store, model, q, system_instruction):
    tool = {"type": "file_search",
            "file_search_store_names": [store],
            "metadata_filter": f"bot_id = {BID}",
            "top_k": 12}
    kwargs = dict(model=model, input=q, tools=[tool])
    if system_instruction:
        kwargs["system_instruction"] = system_instruction
    interaction = await client.aio.interactions.create(**kwargs)
    dump = interaction.model_dump(mode="json", exclude_none=True) if hasattr(interaction, "model_dump") else dict(interaction)
    return dump


async def main():
    client = _get_genai_client()
    rag = GeminiRAGService()
    store = await rag.ensure_store()
    async with async_session() as s:
        bot = await crud_bot.get_active_bot(s, BID)
    persona, model = bot.system_prompt or "", bot.llm_model
    print(f"store={store} model={model} persona_len={len(persona)}\n")

    for label, sysi in [("PERSONA 있음", persona), ("persona 없음", None)]:
        try:
            dump = await call(client, store, model, Q, sysi)
            anns = extract_annotations(dump)
            print(f"=== {label} === annotations={len(anns)} | top keys={list(dump.keys())}")
            for a in anns[:5]:
                print("   ", json.dumps(a, ensure_ascii=False)[:240])
            if not anns:
                # 구조 파악용: steps/content 타입 덤프
                outp = ROOT / f"exports/rag_citation_audit/_interaction_{'persona' if sysi else 'plain'}.json"
                outp.write_text(json.dumps(dump, ensure_ascii=False, indent=1), encoding="utf-8")
                steps = dump.get("steps", [])
                print(f"    (annotations 0) steps={len(steps)} types={[s.get('type') for s in steps]} → {outp.name}")
        except Exception as e:
            print(f"=== {label} === ERROR {type(e).__name__}: {str(e)[:160]}")
        await asyncio.sleep(4)


asyncio.run(main())
