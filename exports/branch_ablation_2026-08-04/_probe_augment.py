# 용어집 증강(2단) 이 현행(1단 혼합검색)보다 나은가 — 실측.
#
# 검증 대상 가설: "질문에 나온 용어의 정의를 먼저 사전에서 뽑아 중간 지식으로 주입하면
# 답변이 좋아진다." 이건 '두 검색결과를 병합'하는 것과 다른 메커니즘이라 따로 재야 한다.
#
#   A (현행)  = 규정집+용어집 한 풀에서 top_k 경쟁 → 페르소나로 답변      ← _dump_bot11full.json 재사용
#   G (증강)  = ① 용어집만 검색해 용어 정의 추출 (중립)
#               ② 규정집만 검색 + ①을 system_prompt 에 주입 → 페르소나로 답변
#
# ②에서 규정집만 거는 이유: 용어집의 기여를 '주입' 경로로만 만들어 효과를 귀속시키기 위해서다.
# (운영에선 둘 다 켜도 되지만 그러면 무엇이 효과를 냈는지 못 가른다.)
#
# 읽기 전용. bots.system_prompt 미변경.
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
from sqlalchemy import text  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.database import async_session  # noqa: E402
from app.services.llm.gemini import build_gemini_contents, safe_response_text  # noqa: E402
from app.services.rag.gemini import (  # noqa: E402
    GeminiRAGService, _FOLLOWUPS_INSTRUCTION,
    _citations_from_grounding, _split_answer_and_followups,
)
for _n in ("sqlalchemy.engine", "sqlalchemy.engine.Engine"):
    logging.getLogger(_n).setLevel(logging.WARNING)

DIR = Path(__file__).parent
BOT = 11
MODEL = "gemini-3.1-flash-lite"   # 봇11 설정은 3.5 지만 free-tier 일일한도 소진
SHA_REG = "7cab18fd146cdcacfce2623f87da16a61fc241b1590fe7ca6eba445c6c8131fd"
SHA_GLO = "000f1e47b999b60726c750d520ca488d150591bee0c474ea576b83c685c5f436"

# ① 용어 추출 — 페르소나 없음. 문서에 없는 용어를 만들지 못하게 못 박는다.
LOOKUP_SP = (
    "너는 축복행정 용어사전 검색기다. 사용자 질문에 등장하거나 질문을 이해하는 데 필요한 "
    "행정 용어를 사전에서 찾아 아래 형식으로만 답하라.\n"
    "- 용어: <표준 명칭> | 기존 표기: <있으면> | 근거: <조문 번호 있으면> | 정의: <한 줄>\n"
    "사전에 없는 용어는 절대 지어내지 마라. 해당 용어가 없으면 '해당 없음'만 출력하라. "
    "설명·인사·서론 없이 목록만 출력하라."
)

INJECT_HEADER = (
    "\n\n---\n[참고 — 행정용어 사전에서 조회된 정의]\n"
    "아래는 이 질문과 관련해 공식 용어사전에서 조회한 항목이다. 용어를 정확히 쓰는 데만 사용하고, "
    "여기에 없는 내용을 지어내지 마라. 답변의 근거는 규정집 검색 결과를 따른다.\n"
)


async def gen(rag, store, model, sp, q, mfilter, max_tokens, tries=4):
    cfg = types.GenerateContentConfig(
        system_instruction=sp or None,
        temperature=get_settings().RAG_TEMPERATURE,
        max_output_tokens=max_tokens,
        tools=[types.Tool(file_search=types.FileSearch(
            file_search_store_names=[store], metadata_filter=mfilter,
            top_k=get_settings().RAG_TOP_K))],
    )
    delay = 20
    for i in range(tries):
        try:
            t0 = time.perf_counter()
            resp = await asyncio.wait_for(rag._client.aio.models.generate_content(
                model=model, contents=build_gemini_contents(q, None), config=cfg), timeout=180)
            g = getattr((resp.candidates or [None])[0], "grounding_metadata", None)
            chunks = []
            for gc in (getattr(g, "grounding_chunks", None) or []):
                rc = gc.retrieved_context
                if rc:
                    chunks.append({"title": rc.title, "page": rc.page_number,
                                   "text": (rc.text or "")[:900]})
            ans, fu = _split_answer_and_followups(safe_response_text(resp))
            cits = _citations_from_grounding(g) if g else []
            return {"ok": True, "elapsed_s": round(time.perf_counter() - t0, 1),
                    "answer": ans, "followups": fu, "n_citations": len(cits),
                    "n_chunks": len(chunks), "chunks": chunks}
        except Exception as e:
            msg = str(e)
            if i == tries - 1:
                return {"ok": False, "error": f"{type(e).__name__}: {msg[:180]}"}
            await asyncio.sleep(delay if ("503" in msg or "429" in msg) else 5)
            delay = min(int(delay * 1.5), 90)


async def main(reps, throttle, limit):
    items = json.loads((DIR / "questions.json").read_text(encoding="utf-8"))["items"]
    if limit:
        items = items[:limit]
    async with async_session() as s:
        row = (await s.execute(text("SELECT name,system_prompt FROM bots WHERE id=:b"),
                               {"b": BOT})).mappings().first()
    persona = row["system_prompt"] or ""

    rag = GeminiRAGService()
    store = await rag.ensure_store()
    out = DIR / "_probe_augment.json"
    prev = {}
    if out.exists():
        prev = {(r["qid"], r["rep"]): r for r in json.loads(out.read_text(encoding="utf-8"))["results"]
                if r.get("ok")}
        print(f"이전 결과 {len(prev)}건 재사용", flush=True)

    print(f"봇 {BOT} '{row['name']}' · model={MODEL} · persona={len(persona)}자")
    print(f"G 팔: 용어조회(용어집만) → 정의주입 + 규정집만 검색")
    print(f"문항 {len(items)} × {reps}회 × 3호출(조회·G·대조C) = {len(items)*reps*3} 호출\n", flush=True)

    results, idx = [], 0
    for it in items:
        for rep in range(1, reps + 1):
            idx += 1
            if (it["qid"], rep) in prev:
                results.append(prev[(it["qid"], rep)])
                continue

            # ① 용어 조회
            look = await gen(rag, store, MODEL, LOOKUP_SP, it["q"],
                             f'bot_id = {BOT} AND content_sha256 = "{SHA_GLO}"', 800)
            await asyncio.sleep(throttle)

            defs = (look.get("answer") or "").strip() if look.get("ok") else ""
            found = bool(defs) and "해당 없음" not in defs

            # ② 정의 주입 + 규정집 검색
            sp = persona + _FOLLOWUPS_INSTRUCTION + ((INJECT_HEADER + defs) if found else "")
            ans = await gen(rag, store, MODEL, sp, it["q"],
                            f'bot_id = {BOT} AND content_sha256 = "{SHA_REG}"', 2048 + 256)

            await asyncio.sleep(throttle)

            # ③ 대조군 C — 주입 없이 규정집만. G 의 이득이 '주입' 때문인지
            #    '용어집을 풀에서 뺀 것' 때문인지 가르기 위해 필요하다.
            ctl = await gen(rag, store, MODEL, persona + _FOLLOWUPS_INSTRUCTION, it["q"],
                            f'bot_id = {BOT} AND content_sha256 = "{SHA_REG}"', 2048 + 256)

            rec = {"qid": it["qid"], "gid": it["gid"], "q": it["q"], "rep": rep,
                   "ok": bool(look.get("ok") and ans.get("ok") and ctl.get("ok")),
                   "control": {"answer": ctl.get("answer"), "n_chunks": ctl.get("n_chunks"),
                               "n_citations": ctl.get("n_citations"),
                               "elapsed_s": ctl.get("elapsed_s"), "chunks": ctl.get("chunks")},
                   "lookup": {"ok": look.get("ok"), "n_chunks": look.get("n_chunks"),
                              "defs": defs, "found_terms": found,
                              "elapsed_s": look.get("elapsed_s")},
                   "answer": ans.get("answer"), "n_chunks": ans.get("n_chunks"),
                   "n_citations": ans.get("n_citations"), "chunks": ans.get("chunks"),
                   "elapsed_s": ans.get("elapsed_s"),
                   "total_s": round((look.get("elapsed_s") or 0) + (ans.get("elapsed_s") or 0), 1),
                   "sp_len": len(sp)}
            results.append(rec)
            print(f"[{idx:>2}] {it['qid']:<6} r{rep} 용어{'O' if found else 'X'} → "
                  f"G {len(ans.get('answer') or ''):>4}자/{ans.get('n_chunks','-')}청크 · "
                  f"C {len(ctl.get('answer') or ''):>4}자/{ctl.get('n_chunks','-')}청크 · "
                  f"{rec['total_s']}s", flush=True)
            out.write_text(json.dumps({"bot": BOT, "model": MODEL, "persona_len": len(persona),
                                       "results": results}, ensure_ascii=False, indent=1),
                           encoding="utf-8")
            await asyncio.sleep(throttle)

    out.write_text(json.dumps({"bot": BOT, "model": MODEL, "persona_len": len(persona),
                               "results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    hit = sum(1 for r in results if r["lookup"]["found_terms"])
    print(f"\n완료 {len(results)}건 · 용어 조회 성공 {hit}/{len(results)} → {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--throttle", type=int, default=7)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    asyncio.run(main(a.reps, a.throttle, a.limit))
