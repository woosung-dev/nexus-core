# M2 — 147개 닫힌어휘 LLM 매핑. 이 세션의 1차 판정 재료다.
#
# 핸드오프 §3 "M2 매핑 호출 규격":
#   · 페르소나 없음 (페르소나는 판정을 왜곡한다)
#   · File Search 끄고 순수 분류로 호출 (툴 자체를 붙이지 않는다)
#   · 147개 목록을 프롬프트에 직접 넣고 그 안에서만 고르게 한다
#   · 목록 밖 용어가 나오면 폐기하고 재시도
#
# 어휘목록 2모드를 나란히 잰다 — 실패가 '어휘가 불투명해서'인지 '매핑 능력 자체'인지 가른다.
#   names = 이름·별칭만 (1,945자)      handoff §3 을 좁게 읽은 것
#   defs  = 이름·별칭+정의 (11,233자)  R-219 처럼 사용자가 용어를 안 쓰는 질문의 상한
#
# 조문은 LLM 이 만들지 않는다. 고른 용어를 _glossary_terms.json 에서 결정론으로 룩업한다.
# 읽기 전용 — DB 접근 없음(페르소나를 안 쓰므로 bots 조회조차 불필요).
import argparse
import asyncio
import json
import logging
import sys
import unicodedata
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
sys.path.insert(0, str(ROOT / "backend"))
for _n in ("sqlalchemy.engine", "sqlalchemy.pool", "httpx", "google_genai"):
    logging.getLogger(_n).setLevel(logging.WARNING)

from google.genai import types  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.services.llm.gemini import build_gemini_contents, safe_response_text  # noqa: E402
from app.services.rag.gemini import GeminiRAGService  # noqa: E402

DIR = Path(__file__).parent
sys.path.insert(0, str(DIR))
from _common import DailyQuotaExhausted, agenerate  # noqa: E402
from _expand import (  # noqa: E402
    MAX_TERMS, build_query, canonical, load_questions, vocab_prompt,
)

MODEL = "gemini-3.1-flash-lite"      # 봇11 설정은 3.5 지만 free-tier 일일한도 소진 (선행 세션)
MODES = ("names", "defs")
MAX_TOKENS = 1024
OUT = DIR / "_map.json"

# 페르소나 없음. '질문에 그 단어가 없어도 상황으로 고르라'가 이 과제의 핵심이다 —
# 표면 문자열로 도달 가능한 것은 M1 이 이미 잡는다.
SYS = """너는 축복행정 용어 분류기다. 아래 <용어목록>의 147개 표준용어 중에서, 사용자 질문에 정확히 답하려면 어떤 용어의 규정 조문을 찾아봐야 하는지 고른다.

규칙:
- <용어목록>에 있는 표준용어만 출력한다. 목록에 없는 말을 절대 만들지 마라.
- 질문에 그 단어가 그대로 나오지 않아도 된다. 질문이 말하는 상황이 어느 용어에 해당하는지로 고른다.
- 관련도가 높은 순으로 최대 %d개. 해당하는 용어가 없으면 빈 배열을 출력한다.
- 설명·인사·서론 없이 JSON 배열 하나만 출력한다.

출력 예시: ["축복자녀가정 편성", "1세가정 편성"]

<용어목록>
%s
</용어목록>"""


def extract_json_array(text):
    """모델 출력에서 JSON 배열을 꺼낸다. 코드펜스·앞뒤 설명을 허용한다."""
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1]
        t = t.rsplit("```", 1)[0]
    dec = json.JSONDecoder()
    for i, ch in enumerate(t):
        if ch != "[":
            continue
        try:
            obj, _ = dec.raw_decode(t[i:])
        except ValueError:
            continue
        if isinstance(obj, list):
            return obj
    raise ValueError("JSON 배열 없음")


def validate(names):
    """(정규화된 hit 목록, 목록 밖 항목들). 하나라도 밖이면 호출자가 응답 전체를 폐기한다."""
    hits, bad = [], []
    seen = set()
    for n in names:
        if not isinstance(n, str):
            bad.append(repr(n))
            continue
        t = canonical(n)
        if t is None:
            bad.append(n)
            continue
        key = unicodedata.normalize("NFC", t["term"])
        if key in seen:
            continue
        seen.add(key)
        hits.append({"term": t["term"], "no": t["no"], "surface": n.strip(),
                     "articles": list(t["source_articles"]), "definition": t["definition"]})
    return hits[:MAX_TERMS], bad


async def map_once(client, mode, q, tries=3):
    """닫힌어휘 매핑 1건. 목록 밖 용어가 나오면 폐기하고 재시도한다."""
    cfg = types.GenerateContentConfig(
        system_instruction=SYS % (MAX_TERMS, vocab_prompt(mode)),
        temperature=get_settings().RAG_TEMPERATURE,
        max_output_tokens=MAX_TOKENS,
    )
    rejected, total_s = [], 0.0
    for attempt in range(1, tries + 1):
        resp, el = await agenerate(client, MODEL, build_gemini_contents(q, None), cfg,
                                   label=f"map/{mode}")
        total_s += el
        raw = safe_response_text(resp)
        um = getattr(resp, "usage_metadata", None)
        usage = None if um is None else {
            "prompt": getattr(um, "prompt_token_count", None),
            "candidates": getattr(um, "candidates_token_count", None),
            "thoughts": getattr(um, "thoughts_token_count", None),
            "total": getattr(um, "total_token_count", None)}
        try:
            names = extract_json_array(raw)
        except ValueError as e:
            rejected.append({"attempt": attempt, "reason": f"파싱 실패: {e}", "raw": raw[:400]})
            continue
        hits, bad = validate(names)
        if bad:
            rejected.append({"attempt": attempt, "reason": "목록 밖 용어", "out_of_vocab": bad,
                             "raw": raw[:400]})
            continue
        return {"ok": True, "hits": hits, "raw": raw[:600], "attempts": attempt,
                "rejected": rejected, "elapsed_s": round(total_s, 1), "usage": usage}
    return {"ok": False, "hits": [], "raw": None, "attempts": tries, "rejected": rejected,
            "elapsed_s": round(total_s, 1), "usage": None}


async def main(reps, throttle, modes, limit):
    items = load_questions()
    if limit:
        items = items[:limit]

    prev = {}
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8"))
        prev = {(r["mode"], r["qid"], r["rep"]): r for r in old["results"] if r.get("ok")}
        print(f"이전 결과 {len(prev)}건 재사용", flush=True)

    rag = GeminiRAGService()
    client = rag._client

    meta = {"model": MODEL, "temperature": get_settings().RAG_TEMPERATURE,
            "max_output_tokens": MAX_TOKENS, "modes": list(modes), "reps": reps,
            "max_terms": MAX_TERMS,
            "vocab_chars": {m: len(vocab_prompt(m)) for m in modes},
            "file_search": False, "persona": False}
    print(f"M2 매핑 · model={MODEL} · temp={meta['temperature']} · File Search 없음 · 페르소나 없음")
    print(f"어휘목록 {meta['vocab_chars']}")
    print(f"문항 {len(items)} × 모드 {list(modes)} × {reps}회 = {len(items)*len(modes)*reps} 호출\n",
          flush=True)

    results, idx, n_new = [], 0, 0
    total = len(items) * len(modes) * reps

    def save():
        OUT.write_text(json.dumps({**meta, "count": len(results), "results": results},
                                  ensure_ascii=False, indent=1), encoding="utf-8")

    try:
        for mode in modes:
            for it in items:
                for rep in range(1, reps + 1):
                    idx += 1
                    key = (mode, it["qid"], rep)
                    if key in prev:
                        results.append(prev[key])
                        continue

                    r = await map_once(client, mode, it["q"])
                    eq, expanded, arts = build_query(it["q"], r["hits"])
                    rec = {"mode": mode, "qid": it["qid"], "gid": it["gid"], "rep": rep,
                           "q": it["q"], **r,
                           "terms": [h["term"] for h in r["hits"]],
                           "articles": arts, "expanded": expanded, "expanded_query": eq}
                    results.append(rec)
                    n_new += 1
                    flag = "ERR" if not r["ok"] else ("확장X" if not expanded else "ok")
                    print(f"[{idx:>3}/{total}] {mode:<5} {it['qid']:<6} r{rep} {flag:<5} "
                          f"시도{r['attempts']} 폐기{len(r['rejected'])} "
                          f"{len(r['hits'])}용어 {len(arts)}조문 {r['elapsed_s']}s "
                          f"{[h['term'] for h in r['hits']]}", flush=True)
                    save()
                    await asyncio.sleep(throttle)
    except DailyQuotaExhausted as e:
        save()
        print(f"\n⚠ 중단: {e}", flush=True)
        raise SystemExit(2)

    save()
    errs = [r for r in results if not r["ok"]]
    oov = sum(len([x for x in r["rejected"] if x.get("out_of_vocab")]) for r in results)
    print(f"\n완료 {len(results)}건 (신규 {n_new}) · 매핑실패 {len(errs)} · 목록밖 폐기 {oov}회 → {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--throttle", type=int, default=8)
    ap.add_argument("--modes", default=",".join(MODES))
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    ms = [m.strip() for m in a.modes.split(",") if m.strip()]
    bad = [m for m in ms if m not in MODES]
    if bad:
        raise SystemExit(f"알 수 없는 모드: {bad}")
    asyncio.run(main(a.reps, a.throttle, ms, a.limit))
