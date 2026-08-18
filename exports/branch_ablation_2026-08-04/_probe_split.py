# 문서 단위 검색 분리가 가능한가 — metadata_filter 로 content_sha256 를 걸어 본다.
#
# 봇11 store 에는 문서가 둘뿐이다: 규정집(2026 개정초안) · 용어집(대사전 행정용어 통합본).
# 현재는 metadata_filter="bot_id = 11" 하나라 둘이 같은 top_k 를 두고 경쟁한다.
# 이 스크립트는 세 조건을 같은 질문에 돌려 (a) 필터가 먹는지 (b) 무엇이 달라지는지 본다.
#
# 읽기 전용. DB 접근 없음(봇 프롬프트 안 씀 — 중립 프롬프트로 검색 거동만 본다).
import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
sys.path.insert(0, str(ROOT / "backend"))
for _n in ("sqlalchemy.engine", "sqlalchemy.pool", "httpx", "google_genai",
           "app.services.rag.gemini"):
    logging.getLogger(_n).setLevel(logging.WARNING)

from google.genai import types  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.services.llm.gemini import build_gemini_contents, safe_response_text  # noqa: E402
from app.services.rag.gemini import GeminiRAGService  # noqa: E402

for _n in ("sqlalchemy.engine", "sqlalchemy.engine.Engine"):
    logging.getLogger(_n).setLevel(logging.WARNING)

DIR = Path(__file__).parent
BOT = 11
MODEL = "gemini-3.1-flash-lite"   # 봇11 설정은 3.5 지만 오늘 free-tier 일일한도(500) 소진
NEUTRAL = ("너는 자료 검색기다. 제공된 문서에서 질문과 관련된 근거를 찾아 간단히 답하라. "
           "자료에 없으면 '자료에서 확인되지 않음'이라고만 답하라.")

SHA_REG = "7cab18fd146cdcacfce2623f87da16a61fc241b1590fe7ca6eba445c6c8131fd"   # 규정집 2026
SHA_GLO = "000f1e47b999b60726c750d520ca488d150591bee0c474ea576b83c685c5f436"   # 용어집 대사전

FILTERS = {
    "현행(둘다)": f"bot_id = {BOT}",
    "규정집만": f'bot_id = {BOT} AND content_sha256 = "{SHA_REG}"',
    "용어집만": f'bot_id = {BOT} AND content_sha256 = "{SHA_GLO}"',
}

# 두 문서의 성격 차이가 드러나도록 질문 유형을 섞는다.
QUESTIONS = [
    ("T1", "용어", "'2세가정 편성'이라는 말은 지금 뭐라고 부르나요?"),
    ("T2", "용어", "축복자녀가 정확히 무슨 뜻인가요?"),
    ("T3", "용어", "은사축복과 기성축복은 용어상 어떻게 구분되나요?"),
    ("P1", "절차", "나는 2세고 1세와 올해 축복을 받을거야. 축복 받고 나서 해야되는 의식이 뭐가 있어?"),
    ("P2", "절차", "1세가정 편성과 2세가정 편성은 의식 절차가 어떻게 다른가요?"),
    ("P3", "절차", "축복 받고 40일 안에 부부관계를 가지면 어떻게 되나요?"),
]


async def call(rag, store, q, mfilter, tries=4):
    cfg = types.GenerateContentConfig(
        system_instruction=NEUTRAL,
        temperature=get_settings().RAG_TEMPERATURE,
        max_output_tokens=1200,
        tools=[types.Tool(file_search=types.FileSearch(
            file_search_store_names=[store], metadata_filter=mfilter,
            top_k=get_settings().RAG_TOP_K))],
    )
    delay = 20
    for i in range(tries):
        try:
            t0 = time.perf_counter()
            resp = await asyncio.wait_for(rag._client.aio.models.generate_content(
                model=MODEL, contents=build_gemini_contents(q, None), config=cfg), timeout=150)
            g = getattr((resp.candidates or [None])[0], "grounding_metadata", None)
            chunks = []
            for gc in (getattr(g, "grounding_chunks", None) or []):
                rc = gc.retrieved_context
                if rc is None:
                    continue
                chunks.append({"title": rc.title, "page": rc.page_number,
                               "text": (rc.text or "")[:700]})
            return {"ok": True, "elapsed_s": round(time.perf_counter() - t0, 1),
                    "n_chunks": len(chunks), "chunks": chunks,
                    "answer": safe_response_text(resp)}
        except Exception as e:
            msg = str(e)
            if i == tries - 1:
                return {"ok": False, "error": f"{type(e).__name__}: {msg[:200]}"}
            await asyncio.sleep(delay if ("503" in msg or "429" in msg) else 5)
            delay = min(int(delay * 1.5), 90)


async def main(throttle):
    rag = GeminiRAGService()
    store = await rag.ensure_store()
    out = DIR / "_probe_split.json"
    prev = {}
    if out.exists():
        prev = {(r["qid"], r["cond"]): r for r in json.loads(out.read_text(encoding="utf-8"))["results"]
                if r.get("ok")}
        print(f"이전 결과 {len(prev)}건 재사용", flush=True)

    results, idx = [], 0
    total = len(QUESTIONS) * len(FILTERS)
    for qid, kind, q in QUESTIONS:
        for cond, mf in FILTERS.items():
            idx += 1
            if (qid, cond) in prev:
                results.append(prev[(qid, cond)])
                continue
            r = await call(rag, store, q, mf)
            rec = {"qid": qid, "kind": kind, "q": q, "cond": cond, "filter": mf, **r}
            results.append(rec)
            flag = "ERR" if not r.get("ok") else ("빈손" if r["n_chunks"] == 0 else "ok")
            print(f"[{idx:>2}/{total}] {qid} {kind} {cond:<10} {flag:<4} "
                  f"chunks={r.get('n_chunks','-')}", flush=True)
            out.write_text(json.dumps({"bot": BOT, "model": MODEL, "store": store,
                                       "filters": FILTERS, "results": results},
                                      ensure_ascii=False, indent=1), encoding="utf-8")
            await asyncio.sleep(throttle)
    out.write_text(json.dumps({"bot": BOT, "model": MODEL, "store": store,
                               "filters": FILTERS, "results": results},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--throttle", type=int, default=8)
    asyncio.run(main(ap.parse_args().throttle))
