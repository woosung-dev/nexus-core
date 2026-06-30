# google-genai 2.x 격리환경에서 M2 구현 전 5개 핵심 호출 경로를 검증하는 스크립트.
import asyncio
import inspect
import os

# DB 는 docker 공유(localhost) — .env 가 이미 localhost 이지만 안전하게 보정.
os.environ.setdefault("PYTHONUNBUFFERED", "1")

import google.genai as genai  # noqa: E402
from google.genai import types  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.services.llm.gemini import (  # noqa: E402
    _get_genai_client,
    build_gemini_contents,
    is_blocked,
    safe_response_text,
)

STORE_DISPLAY = "nexus-core-knowledge-base"
BOT_ID = 5
Q = "축복식 드레스와 턱시도는 어디서 구매하나요?"
CITE = (
    "\n\n[인용 지침] 답변에 사용한 모든 사실은 file_search로 검색한 문서에 근거해야 한다. "
    "각 핵심 주장이 어떤 문서에 근거하는지 반드시 file_citation 인용으로 표기하라."
)


async def load_persona(bot_id: int) -> str:
    # DB(crud_bot.get_active_bot)로 봇 system_prompt 로드.
    from app.core.database import async_session
    from app.crud import crud_bot

    async with async_session() as session:
        bot = await crud_bot.get_active_bot(session, bot_id)
        return bot.system_prompt if bot else ""


def resolve_store(client) -> str:
    # ensure_store 로직: display_name 으로 list→resolve.
    for store in client.file_search_stores.list():
        if store.display_name == STORE_DISPLAY:
            return store.name
    raise RuntimeError("store not found")


def main():
    print("genai version:", genai.__version__)
    settings = get_settings()
    persona = asyncio.run(load_persona(BOT_ID))
    print(f"persona loaded: {len(persona)}자")

    client = _get_genai_client()
    results = {}

    # --- 3. store resolve + documents.list (읽기 전용) ---
    try:
        store = resolve_store(client)
        docs = list(client.file_search_stores.documents.list(parent=store, config={"page_size": 20}))
        # upload 시그니처 호환만 확인 (실제 호출 X)
        up_sig = inspect.signature(client.file_search_stores.upload_to_file_search_store)
        results["3_store_docs"] = f"OK store={store} docs={len(docs)} upload_sig_ok={'file' in up_sig.parameters}"
    except Exception as e:
        results["3_store_docs"] = f"FAIL {type(e).__name__}: {e}"
        store = None

    # --- 1. generate_content + Tool(file_search) + persona ---
    try:
        config = types.GenerateContentConfig(
            system_instruction=persona or None,
            temperature=settings.RAG_TEMPERATURE,
            max_output_tokens=2048,
            tools=[
                types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=[store],
                        metadata_filter=f"bot_id = {BOT_ID}",
                        top_k=settings.RAG_TOP_K,
                    )
                )
            ],
        )
        resp = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=build_gemini_contents(Q, None),
            config=config,
        )
        txt = safe_response_text(resp)
        results["1_generate_content"] = (
            f"OK blocked={is_blocked(resp)} answer_len={len(txt)} preview={txt[:60]!r}"
        )
    except Exception as e:
        results["1_generate_content"] = f"FAIL {type(e).__name__}: {e}"

    # --- 2. generate_content_stream + grounding ---
    try:
        n_chunks = 0
        last_grounding = None
        for chunk in client.models.generate_content_stream(
            model="gemini-3.1-flash-lite",
            contents=build_gemini_contents(Q, None),
            config=config,
        ):
            try:
                cand = chunk.candidates[0] if chunk.candidates else None
                gm = cand.grounding_metadata if cand else None
                if gm and gm.grounding_chunks:
                    last_grounding = gm
            except (AttributeError, IndexError):
                pass
            if chunk.text:
                n_chunks += 1
        gc = len(last_grounding.grounding_chunks) if last_grounding and last_grounding.grounding_chunks else 0
        results["2_stream"] = f"OK text_chunks={n_chunks} grounding_chunks={gc}"
    except Exception as e:
        results["2_stream"] = f"FAIL {type(e).__name__}: {e}"

    # --- 4. interactions.create + persona + CITE → annotations file_citation ---
    try:
        tool = {
            "type": "file_search",
            "file_search_store_names": [store],
            "metadata_filter": f"bot_id = {BOT_ID}",
            "top_k": settings.RAG_TOP_K,
        }
        hits = 0
        total_anns = 0
        questions = [
            Q,
            "축복을 받고 가정회비를 내는 이유가 무엇인가요?",
            "금식 중에 실수하면 어떻게 해야 해?",
        ]
        for q in questions:
            it = client.interactions.create(
                model="gemini-3.1-flash-lite",
                input=q,
                system_instruction=persona + CITE,
                tools=[tool],
            )
            d = it.model_dump(mode="json", exclude_none=True)
            anns = [
                a
                for s in (d.get("steps") or [])
                for c in (s.get("content") or [])
                for a in (c.get("annotations") or [])
                if a.get("type") == "file_citation"
            ]
            if anns:
                hits += 1
            total_anns += len(anns)
            print(f"  interactions q={q[:20]!r} file_citations={len(anns)}")
            if anns:
                sample = anns[0]
                print(f"    sample keys: {list(sample.keys())}")
        results["4_interactions"] = f"OK report_rate={hits}/{len(questions)} total_file_citations={total_anns}"
    except Exception as e:
        import traceback

        traceback.print_exc()
        results["4_interactions"] = f"FAIL {type(e).__name__}: {e}"

    # --- 5. helpers import/work ---
    results["5_helpers"] = (
        f"OK is_blocked/safe_response_text/build_gemini_contents importable, "
        f"build_contents_type={type(build_gemini_contents('q', None)).__name__}"
    )

    print("\n" + "=" * 60)
    ok_all = True
    for k in sorted(results):
        v = results[k]
        if v.startswith("FAIL"):
            ok_all = False
        print(f"[{'PASS' if v.startswith('OK') else 'FAIL'}] {k}: {v}")
    print("=" * 60)
    print("ALL PASS" if ok_all else "SOME FAILED — STOP & REPORT")


if __name__ == "__main__":
    main()
