# 조건부 분기 답변 절제 실험 러너 — A/B/R 3팔 × 문항 × 반복 (resume-safe, 읽기 전용).
#
# 왜 generate_with_rag 를 안 쓰나: 그 함수는 RAGResponse 만 반환하고 raw 응답을 버린다
# (gemini.py:497). 이 실험은 grounding_chunks 원문이 산출물이라 SDK 를 직접 호출한다.
# 운영 config(gemini.py:440-453)를 그대로 재구성하므로 제품 코드는 손대지 않는다.
# 선례: exports/rag_citation_audit/_pilot_dump.py
#
# 팔:
#   A = bot.system_prompt + _FOLLOWUPS_INSTRUCTION           (운영과 동일)
#   B = A + 분기 지시 블록                                    (핸드오프 §4 원문)
#   R = NEUTRAL_SP 단독, followups 없음                       (검색 프로브 — 청크 노출용)
#
# 읽기 전용: DB 는 봇 행 SELECT 만. bots.system_prompt 는 건드리지 않는다.
import argparse
import asyncio
import hashlib
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
from app.services.llm.gemini import build_gemini_contents, is_blocked, safe_response_text  # noqa: E402
from app.services.rag.gemini import (  # noqa: E402
    GeminiRAGService,
    _FOLLOWUPS_INSTRUCTION,
    _citations_from_grounding,
    _split_answer_and_followups,
)

# app.core.database 는 import 시점에 echo=DEBUG 로 엔진을 만든다. 위쪽 setLevel 은 그 전에
# 실행돼 덮어써지므로, import 이후에 한 번 더 낮춘다 (진행 로그를 읽을 수 있게).
for _n in ("sqlalchemy.engine", "sqlalchemy.engine.Engine", "sqlalchemy.pool"):
    logging.getLogger(_n).setLevel(logging.WARNING)

DIR = Path(__file__).parent

# exports/regression/_l1.py:30-31 과 동일 문자열. 회귀 baseline 과 비교 가능하게 유지한다.
NEUTRAL_SP = ("너는 자료 검색기다. 제공된 축복행정 규정집·공문 문서에서 질문과 관련된 근거 조항을 "
              "찾아 인용하며 간단히 답하라. 자료에 없으면 '자료에서 확인되지 않음'이라고만 답하라.")

# 핸드오프 §4 원문 그대로. 3번 규칙이 과분기를 잡는 안전장치이므로 변형 금지.
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

# 팔별 (system_instruction 조립, max_output_tokens).
# A·B 는 운영값 2048+256. R 은 답변 품질이 목적이 아니라 1500 (_capture_raw.py 와 동일).
ARM_TOKENS = {"A": 2048 + 256, "B": 2048 + 256, "R": 1500}


def system_instruction(arm: str, bot_prompt: str) -> str:
    if arm == "A":
        return (bot_prompt or "") + _FOLLOWUPS_INSTRUCTION
    if arm == "B":
        return (bot_prompt or "") + _FOLLOWUPS_INSTRUCTION + BRANCH_BLOCK
    if arm == "R":
        return NEUTRAL_SP
    raise ValueError(f"unknown arm: {arm}")


def dump_grounding(g) -> dict:
    """grounding_metadata → 핸드오프 §5 필드. custom_metadata 는 체크 A 의 관측 대상이라
    없으면 빈 리스트가 아니라 None 으로 남겨 '부재'와 '빈값'을 구분한다."""
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
            "i": i,
            "title": rc.title,
            "uri": rc.uri,
            "page_number": rc.page_number,
            "text": (rc.text or "")[:1500],
            "text_len": len(rc.text or ""),
            "custom_metadata": None if cm is None else [
                {"key": m.key, "string_value": m.string_value,
                 "numeric_value": m.numeric_value,
                 "string_list_value": list(m.string_list_value) if m.string_list_value else None}
                for m in cm
            ],
        })

    supports = []
    for s in (g.grounding_supports or []):
        supports.append({
            "segment": (getattr(s.segment, "text", None) if s.segment else None),
            "chunk_indices": list(s.grounding_chunk_indices or []),
            "confidence_scores": list(s.confidence_scores or []),
        })

    return {"n_chunks": len(chunks), "chunks": chunks, "supports": supports,
            "grounding_absent": False}


async def call_once(rag, store, bot_id, model, q, arm, bot_prompt, tries=5):
    """generate_content 1회. 운영 config 재구성. 429/503 백오프."""
    sp = system_instruction(arm, bot_prompt)
    settings = get_settings()
    config = types.GenerateContentConfig(
        system_instruction=sp or None,
        temperature=settings.RAG_TEMPERATURE,
        max_output_tokens=ARM_TOKENS[arm],
        tools=[types.Tool(file_search=types.FileSearch(
            file_search_store_names=[store],
            metadata_filter=f"bot_id = {bot_id}",
            top_k=settings.RAG_TOP_K))],
    )

    delay = 20
    for attempt in range(tries):
        t0 = time.perf_counter()
        try:
            resp = await asyncio.wait_for(
                rag._client.aio.models.generate_content(
                    model=model, contents=build_gemini_contents(q, None), config=config),
                timeout=180)
            elapsed = round(time.perf_counter() - t0, 1)

            base = {
                "arm": arm, "model": model, "elapsed_s": elapsed,
                "sp_len": len(sp), "sp_sha256": hashlib.sha256(sp.encode()).hexdigest()[:16],
                "max_output_tokens": ARM_TOKENS[arm],
            }

            if is_blocked(resp):
                return {**base, "ok": True, "blocked": True, "answer": "", "followups": [],
                        "n_citations": 0, "finish_reason": None,
                        "grounding": dump_grounding(None)}

            cand = (resp.candidates or [None])[0]
            g = getattr(cand, "grounding_metadata", None) if cand else None
            answer, followups = _split_answer_and_followups(safe_response_text(resp))
            citations = _citations_from_grounding(g) if g else []

            return {**base, "ok": True, "blocked": False,
                    "answer": answer, "followups": followups,
                    "n_citations": len(citations),
                    "citation_titles": sorted({c.title for c in citations if c.title}),
                    "finish_reason": str(getattr(cand, "finish_reason", None)) if cand else None,
                    "grounding": dump_grounding(g)}

        except (Exception, asyncio.TimeoutError) as e:
            msg = str(e)
            if attempt == tries - 1:
                return {"arm": arm, "model": model, "ok": False,
                        "error": f"{type(e).__name__}: {msg[:150]}",
                        "grounding": dump_grounding(None)}
            await asyncio.sleep(delay if ("503" in msg or "429" in msg) else 5)
            delay = min(int(delay * 1.5), 90)


async def main(bot_id, arms, reps, limit, model_override, throttle, tag):
    items = json.loads((DIR / "questions.json").read_text(encoding="utf-8"))["items"]
    if limit:
        items = items[:limit]

    out = DIR / f"_dump_{tag}.json"

    async with async_session() as s:
        row = (await s.execute(
            text("SELECT id,name,system_prompt,llm_model,evidence_policy_mode,history_window "
                 "FROM bots WHERE id=:b"), {"b": bot_id})).mappings().first()
    if not row:
        raise SystemExit(f"bots.id={bot_id} 없음")

    bot_prompt = row["system_prompt"] or ""
    model = model_override or row["llm_model"]

    # resume: 완료된 (qid, arm, rep) 는 건너뛴다. 오류 레코드는 재시도 대상.
    prev = {}
    if out.exists():
        old = json.loads(out.read_text(encoding="utf-8"))
        for r in old.get("results", []):
            if r.get("ok"):
                prev[(r["qid"], r["arm"], r["rep"])] = r
        print(f"이전 결과 {len(prev)}건 재사용", flush=True)

    rag = GeminiRAGService()
    store = await rag.ensure_store()

    meta = {
        "bot": {"id": bot_id, "name": row["name"], "model": model,
                "model_source": "override" if model_override else "bots.llm_model",
                "evidence_policy_mode": row["evidence_policy_mode"],
                "history_window": row["history_window"],
                "system_prompt_len": len(bot_prompt),
                "system_prompt_sha256": hashlib.sha256(bot_prompt.encode()).hexdigest()[:16]},
        "store": store, "arms": arms, "reps": reps,
        "rag_top_k": get_settings().RAG_TOP_K,
        "rag_temperature": get_settings().RAG_TEMPERATURE,
        "history": None,
    }
    print(f"봇 {bot_id} '{row['name']}' model={model} sp={len(bot_prompt)}자 "
          f"mode={row['evidence_policy_mode']}", flush=True)
    print(f"store={store}", flush=True)
    print(f"문항 {len(items)} × 팔 {arms} × {reps}회 = {len(items)*len(arms)*reps} 호출\n", flush=True)

    results, n_new, idx = [], 0, 0
    total = len(items) * len(arms) * reps

    def save():
        out.write_text(json.dumps({**meta, "count": len(results), "results": results},
                                  ensure_ascii=False, indent=1), encoding="utf-8")

    for it in items:
        for arm in arms:
            for rep in range(1, reps + 1):
                idx += 1
                key = (it["qid"], arm, rep)
                if key in prev:
                    results.append(prev[key])
                    continue

                r = await call_once(rag, store, bot_id, model, it["q"], arm, bot_prompt)
                rec = {"qid": it["qid"], "gid": it["gid"], "source": it["source"],
                       "branch_axis": it["branch_axis"], "q": it["q"],
                       "bot_id": bot_id, "rep": rep, **r}
                results.append(rec)
                n_new += 1

                nch = rec["grounding"]["n_chunks"]
                flag = "ERR" if not rec.get("ok") else ("빈손" if nch == 0 else "ok")
                print(f"[{idx:>3}/{total}] {it['qid']:<6} {arm} r{rep} {flag:<4} "
                      f"chunks={nch:<3} cites={rec.get('n_citations', 0):<3} "
                      f"len={len(rec.get('answer') or ''):<5} "
                      f"{rec.get('elapsed_s', '-')}s", flush=True)
                save()
                await asyncio.sleep(throttle)

    save()
    errs = sum(1 for r in results if not r.get("ok"))
    empty = sum(1 for r in results if r["grounding"]["n_chunks"] == 0)
    print(f"\n완료 {len(results)}건 (신규 {n_new} · 오류 {errs} · 청크빈손 {empty}) → {out}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bot-id", type=int, default=7, help="7=라이브 D, 11=2026 정본")
    ap.add_argument("--arms", default="A,B,R", help="A(기준선) B(분기프롬프트) R(검색프로브)")
    ap.add_argument("--reps", type=int, default=2, help="같은 조건 반복 횟수 (비결정성 확인)")
    ap.add_argument("--limit", type=int, default=0, help="앞 N문항만 (스모크용)")
    ap.add_argument("--model", default="", help="llm_model 오버라이드 (봇11 프로브용)")
    ap.add_argument("--throttle", type=int, default=12, help="호출 간 대기(초)")
    ap.add_argument("--tag", default="", help="산출물 접미사 (기본 bot<N>)")
    a = ap.parse_args()

    arms = [x.strip().upper() for x in a.arms.split(",") if x.strip()]
    bad = [x for x in arms if x not in ARM_TOKENS]
    if bad:
        raise SystemExit(f"알 수 없는 팔: {bad}")

    asyncio.run(main(a.bot_id, arms, a.reps, a.limit, a.model, a.throttle,
                     a.tag or f"bot{a.bot_id}"))
