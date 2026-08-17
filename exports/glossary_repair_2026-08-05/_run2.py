# 편성축 문항 러너 — reps 5, 팔 P·NP·M1·NM1 (resume-safe, 읽기 전용).
#
# 선행 `glossary_steering_2026-08-04/_run.py` 의 복사본이고 **바꾼 것은 셋뿐**이다.
#   ① `--questions` / `--glossary` 경로 인자 (선행은 선행 디렉터리 파일에 하드코딩)
#   ② M2 팔은 `_map.json` 이 있을 때만. 없으면 건너뛴다 (선행은 SystemExit)
#   ③ `--reps` 기본 5 (선행은 2). 기준선이 n=2 로는 안 잡힌다는 것이 실측됐다.
#
# 바꾸지 않은 것 — 이게 같아야 선행 세션 결과와 비교가 성립한다:
#   모델 gemini-3.1-flash-lite 고정 · 봇11 · metadata_filter · top_k · temperature ·
#   페르소나 system_instruction = bot.system_prompt + _FOLLOWUPS_INSTRUCTION ·
#   중립 프롬프트 문자열 · 팔별 max_output_tokens · 429/503 백오프 · 일일한도 중단.
#
# 읽기 전용: DB 는 봇 행 SELECT 만. bots.system_prompt 는 건드리지 않는다.
#
# 사용:
#   cd backend && .venv/bin/python ../exports/glossary_repair_2026-08-05/_run2.py \
#       --arms P,NP,M1,NM1 --reps 5
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
STEER = DIR.parent / "glossary_steering_2026-08-04"
sys.path.insert(0, str(STEER))
sys.path.insert(0, str(DIR))
from _common import DailyQuotaExhausted, agenerate  # noqa: E402
from _expand2 import expand_one, load_questions, use_glossary  # noqa: E402

BOT = 11
MODEL = "gemini-3.1-flash-lite"    # 봇11 설정은 3.5 지만 free-tier 일일한도 소진 (선행 세션)
M2_MODE = "names"
DEFAULT_QUESTIONS = DIR / "_questions_pyeongseong.json"
DEFAULT_GLOSSARY = DIR / "_glossary_terms_v2.json"
OUT = DIR / "_dump2.json"     # --out 으로 덮어쓴다. 판(코퍼스)이 바뀌면 파일을 갈라야
                              # 이전 판 관측이 섞이지 않는다.

# exports/regression/_l1.py:30-31 · 선행 세션과 동일 문자열. 회귀 baseline 과 비교 가능하게 유지.
NEUTRAL_SP = ("너는 자료 검색기다. 제공된 축복행정 규정집·공문 문서에서 질문과 관련된 근거 조항을 "
              "찾아 인용하며 간단히 답하라. 자료에 없으면 '자료에서 확인되지 않음'이라고만 답하라.")

# 선행 `branch_ablation_2026-08-04/_run.py` 의 BRANCH_BLOCK 과 **바이트 단위로 동일**.
# 그 파일 주석: "핸드오프 §4 원문 그대로. 3번 규칙이 과분기를 잡는 안전장치이므로 변형 금지."
BRANCH_BLOCK = """

---
[조건부 분기 원칙]
1. 단정 금지 — 검색된 문서에 상황별로 다른 지침이 있는데 사용자의 상황이 확정되지 않았다면,
   하나의 결론으로 단정하지 마라.
2. 분기 출력 — 조건이 갈리면 조건별로 나누어 쓴다. 각 분기는 아래 한 줄 형식으로 시작한다.
   · ~인 경우: [해당 지침]
3. 근거 밖 조건 금지 — 검색된 문서에 없는 조건이나 구분을 만들지 마라.
   문서가 나누지 않은 것을 나누는 것은, 나누지 않는 것보다 나쁘다.
4. 마감 — 문서에 명시되지 않은 상황은
   "문서에 명시되지 않은 그 밖의 경우는 담당자에게 확인해 주세요"로 닫는다.
"""

# B 팔 — 쿼리는 P 와 같고 system_instruction 만 다르다. 검색을 고정하고 생성만 바꾼다.
PERSONA_ARMS = ("P", "M1", "M2", "B")
NEUTRAL_ARMS = {"NP": "P", "NM1": "M1", "NM2": "M2"}      # 중립팔 → 같은 쿼리를 쓰는 페르소나팔
QUERY_OF = {"B": "P"}                                      # B 는 P 의 쿼리를 그대로 쓴다
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


def build_queries(items, reps, maps):
    """문항 × 반복 → 팔별 사용자 메시지.

    M1 은 결정론이라 반복 간 같다. M2 는 매핑 반복과 답변 반복을 짝 맞춘다(선행과 동일).
    _map.json 이 없으면 M2 항목을 만들지 않는다 — M2 팔을 안 돌리면 필요 없다.
    """
    by = {(r["mode"], r["qid"], r["rep"]): r for r in (maps or [])}
    out = {}
    for it in items:
        terms, arts, m1_q, m1_exp = expand_one(it["q"])
        for rep in range(1, reps + 1):
            row = {
                "P": {"q": it["q"], "expanded": False, "terms": [], "articles": []},
                "M1": {"q": m1_q, "expanded": m1_exp, "terms": terms, "articles": arts},
            }
            m = by.get((M2_MODE, it["qid"], rep))
            if m is not None:
                row["M2"] = {"q": m["expanded_query"], "expanded": m["expanded"],
                             "terms": m["terms"], "articles": m["articles"]}
            out[(it["qid"], rep)] = row
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
                                        config, label=f"run2/{arm}")
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


async def main(arms, reps, limit, throttle, qpath, gpath, out_name):
    global OUT
    OUT = DIR / out_name
    n_terms = use_glossary(gpath)
    items = load_questions(qpath)
    if limit:
        items = items[:limit]

    maps = None
    mp = STEER / "_map.json"
    if any(a in ("M2", "NM2") for a in arms):
        if not mp.exists():
            raise SystemExit(f"M2 팔을 요청했는데 {mp} 가 없다. _map.py 를 먼저 돌린다.")
        maps = json.loads(mp.read_text(encoding="utf-8"))["results"]
    queries = build_queries(items, reps, maps)

    async with async_session() as s:
        row = (await s.execute(
            text("SELECT id,name,system_prompt,llm_model,evidence_policy_mode,history_window "
                 "FROM bots WHERE id=:b"), {"b": BOT})).mappings().first()
    if not row:
        raise SystemExit(f"bots.id={BOT} 없음")

    bot_prompt = row["system_prompt"] or ""
    persona_sp = bot_prompt + _FOLLOWUPS_INSTRUCTION
    branch_sp = persona_sp + BRANCH_BLOCK
    sp_of = {a: (persona_sp if a in PERSONA_ARMS else NEUTRAL_SP) for a in ALL_ARMS}
    sp_of["B"] = branch_sp          # 유일한 변수: system_instruction

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
        "questions": str(Path(qpath)), "glossary": str(Path(gpath)), "glossary_terms": n_terms,
        "persona_sp_sha256": hashlib.sha256(persona_sp.encode()).hexdigest()[:16],
        "branch_sp_sha256": hashlib.sha256(branch_sp.encode()).hexdigest()[:16],
        "neutral_sp_sha256": hashlib.sha256(NEUTRAL_SP.encode()).hexdigest()[:16],
        "metadata_filter": f"bot_id = {BOT}",
        "rag_top_k": get_settings().RAG_TOP_K,
        "rag_temperature": get_settings().RAG_TEMPERATURE,
        "history": None,
        "queries": {f"{q}|r{r}": v for (q, r), v in queries.items()},
    }
    print(f"봇 {BOT} '{row['name']}' model={MODEL} sp={len(bot_prompt)}자 "
          f"mode={row['evidence_policy_mode']}")
    print(f"용어집 {Path(gpath).name} {n_terms}개 · 문항 {Path(qpath).name} {len(items)}건")
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
                qkey = NEUTRAL_ARMS.get(arm) or QUERY_OF.get(arm, arm)
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
    # B 는 의도적으로 다른 system_instruction 을 쓴다. 팔별로 기대 해시를 따로 본다.
    expect_sp = {a: meta["branch_sp_sha256"] if a == "B" else meta["persona_sp_sha256"]
                 for a in PERSONA_ARMS}
    bad_sp = sum(1 for r in results if r.get("ok") and r["arm"] in PERSONA_ARMS
                 and r.get("sp_sha256") != expect_sp[r["arm"]])
    bad_model = sum(1 for r in results if r.get("model") != MODEL)
    print(f"\n완료 {len(results)}건 (신규 {n_new} · 오류 {errs} · 청크빈손 {empty})")
    print(f"페르소나 팔 프롬프트 해시 불일치: {bad_sp} (0 이어야 의도한 조건)")
    print(f"모델 불일치: {bad_model} (0 이어야 팔 사이 조건 고정)")
    print(f"→ {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="P,NP,M1,NM1")
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--throttle", type=int, default=10)
    ap.add_argument("--questions", default=str(DEFAULT_QUESTIONS))
    ap.add_argument("--glossary", default=str(DEFAULT_GLOSSARY))
    ap.add_argument("--out", default="_dump2.json")
    a = ap.parse_args()
    arms = [x.strip() for x in a.arms.split(",") if x.strip()]
    bad = [x for x in arms if x not in ARM_TOKENS]
    if bad:
        raise SystemExit(f"알 수 없는 팔: {bad}")
    asyncio.run(main(arms, a.reps, a.limit, a.throttle, a.questions, a.glossary, a.out))
