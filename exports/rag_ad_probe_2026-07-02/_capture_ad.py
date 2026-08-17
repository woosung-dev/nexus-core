# 질문당 P(운영 표시답변)/A(interactions 단일패스)/PF(persona-free 재검색) 3콜을 캡처하는 resume-safe 스크립트
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

from app.services.llm.gemini import _get_genai_client  # noqa: E402
from app.services.rag.gemini import (  # noqa: E402
    GeminiRAGService,
    _CITATION_INSTRUCTION,
    _split_answer_and_followups,
)
from app.core.config import get_settings  # noqa: E402
from app.core.database import async_session  # noqa: E402
from app.crud import crud_bot  # noqa: E402

BID = 3
DIR = Path(__file__).parent
QUESTIONS = json.loads((DIR / "questions.json").read_text())
OUT = DIR / "captures.json"
REPEAT_A_QIDS = set(range(5))  # 결정성 체크: 앞 5문항은 A 콜 2회
CALL_GAP = 5.0


def load_captures() -> dict:
    if OUT.exists():
        return json.loads(OUT.read_text())
    return {}


def save_captures(caps: dict) -> None:
    OUT.write_text(json.dumps(caps, ensure_ascii=False, indent=1), encoding="utf-8")


async def with_retry(coro_fn, label: str):
    delay = 20.0
    for attempt in range(5):
        try:
            return await coro_fn()
        except Exception as e:
            msg = str(e)
            transient = any(t in msg for t in ("429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE", "overloaded"))
            if attempt == 4 or not transient:
                return {"error": f"{type(e).__name__}: {msg[:300]}"}
            print(f"    [{label}] 재시도 {attempt + 1} ({msg[:80]}) — {delay:.0f}s 대기")
            await asyncio.sleep(delay)
            delay = min(delay * 1.5, 90.0)


async def call_p(rag: GeminiRAGService, q: str, persona: str, model: str) -> dict:
    r = await rag.generate_with_rag(bot_id=BID, prompt=q, system_prompt=persona, model_name=model, max_tokens=2048)
    return {
        "answer": r.answer,
        "citations": [c.model_dump() for c in r.citations],
        "followups": r.followups,
    }


async def call_a(client, store: str, q: str, persona: str, model: str) -> dict:
    interaction = await client.aio.interactions.create(
        model=model,
        input=q,
        system_instruction=(persona or "") + _CITATION_INSTRUCTION,
        tools=[{
            "type": "file_search",
            "file_search_store_names": [store],
            "metadata_filter": f"bot_id = {BID}",
            "top_k": get_settings().RAG_TOP_K,
        }],
    )
    dump = interaction.model_dump(mode="json", exclude_none=True)
    texts, anns = [], []
    for step in dump.get("steps") or []:
        for content in step.get("content") or []:
            if content.get("text"):
                texts.append(content["text"])
            for a in content.get("annotations") or []:
                anns.append(a)
    raw_answer = "\n".join(texts)
    clean_answer, followups = _split_answer_and_followups(raw_answer)
    return {
        "answer": clean_answer,
        "raw_answer": raw_answer,
        "followups": followups,
        "annotations": anns,
        "steps_types": [s.get("type") for s in dump.get("steps") or []],
    }


async def call_pf(client, store: str, q: str, model: str) -> dict:
    """persona 없이 generate_content — D의 후보 청크(전문 텍스트)를 grounding에서 수확."""
    settings = get_settings()
    config = types.GenerateContentConfig(
        system_instruction=None,
        temperature=settings.RAG_TEMPERATURE,
        max_output_tokens=2048,
        tools=[types.Tool(file_search=types.FileSearch(
            file_search_store_names=[store],
            metadata_filter=f"bot_id = {BID}",
            top_k=settings.RAG_TOP_K,
        ))],
    )
    response = await client.aio.models.generate_content(model=model, contents=q, config=config)
    chunks, supports = [], []
    try:
        grounding = response.candidates[0].grounding_metadata
        if grounding and grounding.grounding_chunks:
            for ch in grounding.grounding_chunks:
                rc = ch.retrieved_context
                if rc:
                    chunks.append({"title": rc.title, "text": rc.text or ""})
        if grounding and grounding.grounding_supports:
            for sp in grounding.grounding_supports:
                supports.append(sp.model_dump(mode="json", exclude_none=True))
    except (AttributeError, IndexError):
        pass
    try:
        answer = response.text or ""
    except Exception:
        answer = ""
    return {"answer": answer, "chunks": chunks, "supports": supports}


def has_error(v) -> bool:
    return not isinstance(v, dict) or bool(v.get("error"))


async def main():
    client = _get_genai_client()
    rag = GeminiRAGService()
    store = await rag.ensure_store()
    async with async_session() as s:
        bot = await crud_bot.get_active_bot(s, BID)
    assert bot is not None
    persona, model = bot.system_prompt or "", bot.llm_model
    print(f"bot={bot.name} model={model} persona_len={len(persona)} questions={len(QUESTIONS)}")

    caps = load_captures()
    n_calls = 0
    for qid, item in enumerate(QUESTIONS):
        key = str(qid)
        rec = caps.get(key) or {"question": item["question"], "meta": item}
        caps[key] = rec
        plan = [("P", lambda q=item["question"]: call_p(rag, q, persona, model)),
                ("A", lambda q=item["question"]: call_a(client, store, q, persona, model)),
                ("PF", lambda q=item["question"]: call_pf(client, store, q, model))]
        if qid in REPEAT_A_QIDS:
            plan.append(("A2", lambda q=item["question"]: call_a(client, store, q, persona, model)))
        for slot, fn in plan:
            if slot in rec and not has_error(rec[slot]):
                continue
            rec[slot] = await with_retry(fn, f"q{qid}:{slot}")
            n_calls += 1
            err = rec[slot].get("error", "")
            print(f"  q{qid:02d} {slot:<3} {'ERROR ' + err[:60] if err else 'ok'}")
            save_captures(caps)
            await asyncio.sleep(CALL_GAP)

    errs = sum(1 for r in caps.values() for k in ("P", "A", "PF", "A2") if k in r and has_error(r[k]))
    print(f"\n완료 — 이번 실행 호출 {n_calls}회, 잔여 에러 슬롯 {errs}개 (재실행 시 에러만 재시도)")


asyncio.run(main())
