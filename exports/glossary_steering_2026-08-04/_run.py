# 용어→조문 검색 유도 실험 러너 — 6팔 × 문항 × 반복 (resume-safe, 읽기 전용).
#
# 선행 exports/branch_ablation_2026-08-04/_run.py 골격을 그대로 쓴다. 바꾸는 것은 팔 정의와
# 사용자 메시지뿐. generate_with_rag 대신 SDK 직접 호출도 그대로다 — 그 함수는 raw 응답을
# 버리는데(gemini.py:497) 이 실험은 grounding_chunks 원문이 산출물이다. 운영 config
# (gemini.py:440-453)를 재구성하므로 제품 코드는 손대지 않는다.
#
# 팔 — 변수는 사용자 메시지의 쿼리 확장 방식 하나뿐이다.
#   P   = 페르소나, 원 질문                    (대조군, 운영과 동일 조건)
#   M1  = 페르소나, 어휘매칭 확장
#   M2  = 페르소나, LLM 닫힌어휘 매핑 확장     (_map.json, 반복 짝 맞춤)
#   NP · NM1 · NM2 = 중립 프롬프트, 같은 쿼리   (검색 관측 전용 — 페르소나가 청크를 숨긴다)
#
# 프롬프트·필터·모델·top_k·temperature 는 팔 사이에 바뀌지 않는다.
# 읽기 전용: DB 는 봇 행 SELECT 만. bots.system_prompt 는 건드리지 않는다.
import argparse
import asyncio
import hashlib
import json
import logging
import sys
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
from app.services.llm.gemini import build_gemini_contents, is_blocked, safe_response_text  # noqa: E402
from app.services.rag.gemini import (  # noqa: E402
    GeminiRAGService,
    _FOLLOWUPS_INSTRUCTION,
    _citations_from_grounding,
    _split_answer_and_followups,
)

for _n in ("sqlalchemy.engine", "sqlalchemy.engine.Engine", "sqlalchemy.pool"):
    logging.getLogger(_n).setLevel(logging.WARNING)

DIR = Path(__file__).parent
sys.path.insert(0, str(DIR))
from _common import DailyQuotaExhausted, agenerate  # noqa: E402
from _expand import build_query, lexical_match, load_questions  # noqa: E402

BOT = 11
MODEL = "gemini-3.1-flash-lite"    # 봇11 설정은 3.5 지만 free-tier 일일한도 소진 (선행 세션)
M2_MODE = "names"                  # 1차 관측에서 defs 보다 안정적이고 잡음이 적었다
OUT = DIR / "_dump.json"

# exports/regression/_l1.py:30-31 · 선행 세션과 동일 문자열. 회귀 baseline 과 비교 가능하게 유지.
NEUTRAL_SP = ("너는 자료 검색기다. 제공된 축복행정 규정집·공문 문서에서 질문과 관련된 근거 조항을 "
              "찾아 인용하며 간단히 답하라. 자료에 없으면 '자료에서 확인되지 않음'이라고만 답하라.")

# 페르소나 팔은 운영값 2048+256. 중립 팔은 답변 품질이 목적이 아니라 1500 (선행 R 팔과 동일).
PERSONA_ARMS = ("P", "M1", "M2")
NEUTRAL_ARMS = {"NP": "P", "NM1": "M1", "NM2": "M2"}      # 중립팔 → 같은 쿼리를 쓰는 페르소나팔
ALL_ARMS = list(PERSONA_ARMS) + list(NEUTRAL_ARMS)
ARM_TOKENS = {a: (2048 + 256 if a in PERSONA_ARMS else 1500) for a in ALL_ARMS}


def dump_grounding(g) -> dict:
    """grounding_metadata → 관측 필드. custom_metadata 는 '부재'와 '빈값'을 구분해 남긴다."""
    if g is None:
        return {"n_chunks": 0, "chunks": [], "supports": [], "grounding_absent": True}

    chunks = []
    for i, gc in enumerate(g.grounding_chunks or []):
        rc = gc.retrieved_context
        if rc is None:
            chunks.append({"i": i, "retrieved_context": None})
            continue
        cm = rc.custom_metadata
        chunks.append({
            "i": i, "title": rc.title, "uri": rc.uri, "page_number": rc.page_number,
            "text": (rc.text or "")[:1500], "text_len": len(rc.text or ""),
            "custom_metadata": None if cm is None else [
                {"key": m.key, "string_value": m.string_value,
                 "numeric_value": m.numeric_value} for m in cm],
        })

    supports = [{"segment": (getattr(s.segment, "text", None) if s.segment else None),
                 "chunk_indices": list(s.grounding_chunk_indices or []),
                 "confidence_scores": list(s.confidence_scores or [])}
                for s in (g.grounding_supports or [])]

    return {"n_chunks": len(chunks), "chunks": chunks, "supports": supports,
            "grounding_absent": False}


def build_queries(items, maps):
    """문항 × 반복 → 팔별 사용자 메시지.

    M2 는 매핑 반복과 답변 반복을 짝 맞춘다(rep1 답변은 rep1 매핑 결과를 쓴다).
    매핑 잡음이 그대로 전파되는 게 실제 파이프라인이고, 합집합으로 뭉개면 흔들림을 못 본다.
    """
    by = {(r["mode"], r["qid"], r["rep"]): r for r in maps}
    out = {}
    for it in items:
        m1_hits = lexical_match(it["q"])
        m1_q, m1_exp, m1_arts = build_query(it["q"], m1_hits)
        for rep in (1, 2):
            m = by.get((M2_MODE, it["qid"], rep))
            if m is None:
                raise SystemExit(f"_map.json 에 ({M2_MODE}, {it['qid']}, rep{rep}) 없음 — _map.py 먼저")
            out[(it["qid"], rep)] = {
                "P": {"q": it["q"], "expanded": False, "terms": [], "articles": []},
                "M1": {"q": m1_q, "expanded": m1_exp,
                       "terms": [h["term"] for h in m1_hits], "articles": m1_arts},
                "M2": {"q": m["expanded_query"], "expanded": m["expanded"],
                       "terms": m["terms"], "articles": m["articles"]},
            }
    return out


async def call_once(rag, store, model, q, arm, sp):
    """generate_content 1회. 운영 config 재구성."""
    config = types.GenerateContentConfig(
        system_instruction=sp or None,
        temperature=get_settings().RAG_TEMPERATURE,
        max_output_tokens=ARM_TOKENS[arm],
        tools=[types.Tool(file_search=types.FileSearch(
            file_search_store_names=[store],
            metadata_filter=f"bot_id = {BOT}",
            top_k=get_settings().RAG_TOP_K))],
    )
    try:
        resp, elapsed = await agenerate(rag._client, model, build_gemini_contents(q, None),
                                        config, label=f"run/{arm}")
    except DailyQuotaExhausted:
        raise
    except Exception as e:
        return {"arm": arm, "model": model, "ok": False,
                "error": f"{type(e).__name__}: {str(e)[:150]}", "grounding": dump_grounding(None)}

    base = {"arm": arm, "model": model, "elapsed_s": elapsed, "sp_len": len(sp),
            "sp_sha256": hashlib.sha256(sp.encode()).hexdigest()[:16],
            "max_output_tokens": ARM_TOKENS[arm]}

    if is_blocked(resp):
        return {**base, "ok": True, "blocked": True, "answer": "", "followups": [],
                "n_citations": 0, "finish_reason": None, "grounding": dump_grounding(None)}

    cand = (resp.candidates or [None])[0]
    g = getattr(cand, "grounding_metadata", None) if cand else None
    answer, followups = _split_answer_and_followups(safe_response_text(resp))
    citations = _citations_from_grounding(g) if g else []
    return {**base, "ok": True, "blocked": False, "answer": answer, "followups": followups,
            "n_citations": len(citations),
            "citation_titles": sorted({c.title for c in citations if c.title}),
            "finish_reason": str(getattr(cand, "finish_reason", None)) if cand else None,
            "grounding": dump_grounding(g)}


async def main(arms, reps, limit, throttle):
    items = load_questions()
    if limit:
        items = items[:limit]
    maps = json.loads((DIR / "_map.json").read_text(encoding="utf-8"))["results"]
    queries = build_queries(items, maps)

    async with async_session() as s:
        row = (await s.execute(
            text("SELECT id,name,system_prompt,llm_model,evidence_policy_mode,history_window "
                 "FROM bots WHERE id=:b"), {"b": BOT})).mappings().first()
    if not row:
        raise SystemExit(f"bots.id={BOT} 없음")

    bot_prompt = row["system_prompt"] or ""
    persona_sp = bot_prompt + _FOLLOWUPS_INSTRUCTION
    sp_of = {a: (persona_sp if a in PERSONA_ARMS else NEUTRAL_SP) for a in ALL_ARMS}

    prev = {}
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8"))
        prev = {(r["qid"], r["arm"], r["rep"]): r for r in old.get("results", []) if r.get("ok")}
        print(f"이전 결과 {len(prev)}건 재사용", flush=True)

    rag = GeminiRAGService()
    store = await rag.ensure_store()

    meta = {
        "bot": {"id": BOT, "name": row["name"], "model": MODEL,
                "model_source": "override(free-tier 한도)",
                "bots_llm_model": row["llm_model"],
                "evidence_policy_mode": row["evidence_policy_mode"],
                "history_window": row["history_window"],
                "system_prompt_len": len(bot_prompt),
                "system_prompt_sha256": hashlib.sha256(bot_prompt.encode()).hexdigest()},
        "store": store, "arms": arms, "reps": reps, "m2_mode": M2_MODE,
        "persona_sp_sha256": hashlib.sha256(persona_sp.encode()).hexdigest()[:16],
        "neutral_sp_sha256": hashlib.sha256(NEUTRAL_SP.encode()).hexdigest()[:16],
        "metadata_filter": f"bot_id = {BOT}",
        "rag_top_k": get_settings().RAG_TOP_K,
        "rag_temperature": get_settings().RAG_TEMPERATURE,
        "history": None,
        "queries": {f"{q}|r{r}": v for (q, r), v in queries.items()},
    }
    print(f"봇 {BOT} '{row['name']}' model={MODEL} sp={len(bot_prompt)}자 "
          f"mode={row['evidence_policy_mode']} · M2 어휘목록={M2_MODE}")
    print(f"페르소나 system_instruction sha={meta['persona_sp_sha256']} "
          f"(bot.system_prompt + _FOLLOWUPS_INSTRUCTION)")
    print(f"store={store} · filter='{meta['metadata_filter']}' · top_k={meta['rag_top_k']}")
    print(f"문항 {len(items)} × 팔 {arms} × {reps}회 = {len(items)*len(arms)*reps} 호출\n", flush=True)

    results, idx, n_new = [], 0, 0
    total = len(items) * len(arms) * reps

    def save():
        OUT.write_text(json.dumps({**meta, "count": len(results), "results": results},
                                  ensure_ascii=False, indent=1), encoding="utf-8")

    try:
        for it in items:
            for arm in arms:
                qkey = NEUTRAL_ARMS.get(arm, arm)
                for rep in range(1, reps + 1):
                    idx += 1
                    key = (it["qid"], arm, rep)
                    if key in prev:
                        results.append(prev[key])
                        continue

                    qv = queries[(it["qid"], rep)][qkey]
                    r = await call_once(rag, store, MODEL, qv["q"], arm, sp_of[arm])
                    rec = {"qid": it["qid"], "gid": it["gid"], "source": it["source"],
                           "branch_axis": it["branch_axis"], "arm": arm, "rep": rep,
                           "bot_id": BOT, "query_arm": qkey, "q": qv["q"],
                           "orig_q": it["q"], "expanded": qv["expanded"],
                           "exp_terms": qv["terms"], "exp_articles": qv["articles"], **r}
                    results.append(rec)
                    n_new += 1

                    nch = rec["grounding"]["n_chunks"]
                    pages = sorted({c.get("page_number") for c in rec["grounding"]["chunks"]
                                    if c.get("page_number") is not None})
                    flag = "ERR" if not rec.get("ok") else ("빈손" if nch == 0 else "ok")
                    print(f"[{idx:>3}/{total}] {it['qid']:<6} {arm:<3} r{rep} {flag:<4} "
                          f"chunks={nch:<3} cites={rec.get('n_citations', 0):<3} "
                          f"len={len(rec.get('answer') or ''):<5} "
                          f"p21={'Y' if 21 in pages else '-'} "
                          f"{rec.get('elapsed_s', '-')}s", flush=True)
                    save()
                    await asyncio.sleep(throttle)
    except DailyQuotaExhausted as e:
        save()
        print(f"\n⚠ 중단: {e}", flush=True)
        raise SystemExit(2)

    save()
    errs = sum(1 for r in results if not r.get("ok"))
    empty = sum(1 for r in results if r["grounding"]["n_chunks"] == 0)
    bad_sp = sum(1 for r in results if r.get("ok") and r["arm"] in PERSONA_ARMS
                 and r.get("sp_sha256") != meta["persona_sp_sha256"])
    print(f"\n완료 {len(results)}건 (신규 {n_new} · 오류 {errs} · 청크빈손 {empty})")
    print(f"페르소나 팔 프롬프트 해시 불일치: {bad_sp} (0 이어야 운영과 동일 조건)")
    print(f"→ {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default=",".join(ALL_ARMS))
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--throttle", type=int, default=10)
    a = ap.parse_args()
    arms = [x.strip() for x in a.arms.split(",") if x.strip()]
    bad = [x for x in arms if x not in ARM_TOKENS]
    if bad:
        raise SystemExit(f"알 수 없는 팔: {bad}")
    asyncio.run(main(arms, a.reps, a.limit, a.throttle))
