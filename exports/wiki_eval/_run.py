# 45문항 × 여러 팔 실행. 봇 11(D-1 ver2) · gemini-3.5-flash-lite.
#
#   팔 A   RAG          기존 GeminiRAGService — Gemini file_search 가 스토어(PDF 2건)에서 검색
#   팔 B   WIKI         BM25 멀티스케일로 페이지를 고르고 그 페이지의 원문 전부를 주입(최대 24건)
#   팔 B′  WIKI_BUDGET  같은 검색기, 원문은 RRF 유닛 순위 상위 예산분만(3,000자·최대 8건)
#   팔 C   WIKI_FIRST   카파시 원안 — 위키 페이지 본문으로 답한다
#   팔 F   HYBRID       팔 A 를 그대로 돌리되 BM25 원문을 함께 준다 — **보완** 가설
#   팔 D   FULL         원문 250건 통째 주입, 검색 없음 (상한선 측정용)
#
# 공정성: 모델·온도·max_tokens·system_prompt 를 같게 맞추고, 근거 지시 문구(GUIDE)도
# **모든 팔에 동일하게** 붙인다. 남는 차이는 컨텍스트 조달 방식 하나다.
#   알려진 비대칭 하나: 팔 A·F 는 `generate_with_rag` 를 타므로 `_FOLLOWUPS_INSTRUCTION`
#   (추천질문 3개를 붙이라는 출력 형식 지시, 약 700자)이 system_prompt 에 더 붙는다.
#   근거 사용 지침이 아니고 채점 본문에서는 떼어내지만, 팔 A 를 프로덕션 경로 그대로
#   두는 값어치가 더 커서 손대지 않았다.
#
# **우리 검색기는 dense 를 쓰지 않는다.** 의미 검색은 팔 A(file_search)가 이미 하는 일이고,
# 우리가 임베딩 인덱스를 하나 더 만들면 보완이 아니라 복제가 된다 — 실제로 우리 dense 는
# file_search 가 틀리는 방식으로 똑같이 틀렸다(「가정회비」 질문에서 유아회비 1위).
# 그래서 역할을 갈랐다. 팔 A = 의미, 우리 팔 = 어휘(BM25) + 위키 구조.
# 되돌리려면 WIKI_DENSE_SCALES=page,unit — page·unit 벡터는 캐시에 남아 있다.
#
# 사용: cd backend && uv run python ../exports/wiki_eval/_run.py [--limit N] [--arms A,B,B2,C,F,D]
import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[2] / "backend" / ".env")

# 측정 설정은 셸 히스토리가 아니라 여기에 둔다 — 안 그러면 재현할 때 빠뜨린다.
# 빈 값 = 모든 스케일 BM25 전용. 임베딩 API 를 한 번도 부르지 않는다.
os.environ.setdefault("WIKI_DENSE_SCALES", "")

from google import genai  # noqa: E402
from google.genai import types  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.services.rag.gemini import GeminiRAGService  # noqa: E402
from app.services.wiki.service import (  # noqa: E402
    _context_block,
    _select_units,
    answer_with_wiki,
)
from app.services.wiki.store import get_index  # noqa: E402

DIR = Path(__file__).parent
QUESTIONS = DIR / "questions.json"
OUT = DIR / "answers.json"

# 배치로 돌리면 화면 출력은 흘러가 버린다. 어떤 HTTP 호출이 언제 나갔는지가 감사 근거다.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[logging.FileHandler(DIR / "_run.log", encoding="utf-8")],
)

BOT_ID = 11
MODEL = "gemini-3.5-flash-lite"
MAX_TOKENS = 2048

ARM_KEY = {"A": "rag", "B": "wiki", "B2": "wiki_budget", "C": "wiki_first",
           "F": "hybrid", "D": "full"}
ARM_MODE = {"B": "raw", "B2": "raw_budget", "C": "wiki"}

# 모든 팔에 똑같이 거는 지시. 한쪽에만 있으면 검색 성능이 아니라 지시 문구를 재게 된다.
GUIDE = (
    "\n\n[근거 규칙]\n"
    "제공된 규정 자료에 근거해서만 답한다. 자료에 없는 내용은 지어내지 말고, "
    "확인되지 않는다고 말한 뒤 담당 부서 안내로 넘긴다."
)


def squash(s: str) -> str:
    return "".join(unicodedata.normalize("NFKC", s or "").casefold().split())


def score_keywords(answer: str, keywords: list[str]) -> dict:
    """키워드 충족을 두 가지로 잰다.

    통문자 일치만 세면 「담당 목회자에게 보고」 같은 구(句) 키워드가 사실상 절대 안 맞아
    두 팔이 나란히 0이 되고 차이가 안 보인다. 그래서 토큰 부분점수를 주지표로 쓰고,
    통문자 일치는 참고로 함께 남긴다.
    """
    body = squash(answer)
    exact, partials, detail = [], [], []
    for kw in keywords:
        if not squash(kw):
            continue
        tokens = [t for t in re.split(r"[\s,/·()]+", kw) if len(squash(t)) >= 2]
        found = [t for t in tokens if squash(t) in body]
        frac = len(found) / len(tokens) if tokens else 0.0
        partials.append(frac)
        if squash(kw) in body:
            exact.append(kw)
        detail.append({"kw": kw, "frac": round(frac, 2), "found": found})
    return {
        "kw_pct": round(100 * sum(partials) / len(partials)) if partials else None,
        "kw_exact": len(exact),
        "kw_total": len(keywords),
        "kw_detail": detail,
    }


# 무료 티어 **생성** 상한도 둘이다. 임베딩 상한과는 또 별개다.
#
#   분당 15회   GenerateRequestsPerMinutePerProjectPerModel-FreeTier   → 페이싱으로 피한다
#   하루 500회  GenerateRequestsPerDayPerProjectPerModel-FreeTier      → 못 피한다. 총량이다
#
# 45문항 × 5팔 = 225회다. **하루에 두 바퀴가 한계**고, 스모크 테스트도 같은 지갑에서 나간다.
# 첫 전체 실행에서 분당 상한에 11문항이 죽었고, 페이싱을 붙여 다시 돌리다 하루 상한에 걸렸다.
_GEN_INTERVAL = 4.2  # 초. 약 14회/분.
_last_gen = 0.0

_RETRY_DELAY = re.compile(r"'retryDelay': '(\d+)s'")


class DailyQuotaExhausted(RuntimeError):
    """하루 상한. 재시도해도 안 열리므로 배치를 즉시 세운다."""


def _err(e: Exception, **extra) -> dict:
    """실패를 셀에 적는다 — 한 문항 실패로 배치가 죽지 않게.

    단 **하루 상한은 셀에 적을 일이 아니라 배치를 세울 일이다.** 적고 넘어가면
    남은 문항의 멀쩡한 앞선 결과를 전부 ERR 로 덮어쓴다. 실제로 한 번 그렇게 날렸다.
    """
    if isinstance(e, DailyQuotaExhausted):
        raise e
    return {"answer": "", "citations": [], "elapsed_s": 0.0,
            "error": f"{type(e).__name__}: {e}", **extra}


async def _pace() -> None:
    global _last_gen
    gap = _GEN_INTERVAL - (time.monotonic() - _last_gen)
    if gap > 0:
        await asyncio.sleep(gap)
    _last_gen = time.monotonic()


async def with_retry(make, tries: int = 4):
    """생성 호출 하나를 페이싱하고 429 는 물러섰다 다시 시도한다.

    반환은 (결과, 소요초). **소요초는 성공한 호출 하나만** 잰다 — 페이싱 대기와 재시도 시간을
    같이 세면 팔 사이의 지연 비교가 무의미해진다.
    """
    for attempt in range(tries):
        await _pace()
        t0 = time.perf_counter()
        try:
            return await make(), round(time.perf_counter() - t0, 2)
        except Exception as e:
            msg = str(e)
            # 하루 상한은 기다려도 안 열린다. 45문항 × 4회 × 60초를 헛돌지 않게 즉시 세운다.
            if "PerDay" in msg:
                raise DailyQuotaExhausted(msg) from e
            if "429" not in msg or attempt == tries - 1:
                raise
            m = _RETRY_DELAY.search(msg)
            wait = (float(m.group(1)) + 2) if m else 25.0
            logging.warning("생성 429 — %.0f초 후 재시도 (%d/%d)", wait, attempt + 1, tries)
            await asyncio.sleep(wait)
    raise RuntimeError("생성 재시도 소진")


async def load_system_prompt() -> str:
    engine = create_async_engine(os.environ["DATABASE_URL"])
    async with engine.connect() as conn:
        sp = (
            await conn.execute(text("select system_prompt from bots where id = :i"), {"i": BOT_ID})
        ).scalar()
    await engine.dispose()
    return sp or ""


async def run_rag(rag, q: str, system_prompt: str) -> dict:
    try:
        res, secs = await with_retry(
            lambda: rag.generate_with_rag(
                bot_id=BOT_ID,
                prompt=q,
                system_prompt=system_prompt + GUIDE,
                model_name=MODEL,
                max_tokens=MAX_TOKENS,
            )
        )
        return {
            "answer": res.answer,
            "citations": [{"title": c.title, "uri": c.uri} for c in res.citations],
            "elapsed_s": secs,
            "error": None,
        }
    except Exception as e:
        return _err(e)


async def run_wiki(q: str, system_prompt: str, context_mode: str = "raw") -> dict:
    try:
        (res, ret), secs = await with_retry(
            lambda: answer_with_wiki(
                bot_id=BOT_ID,
                question=q,
                system_prompt=system_prompt + GUIDE,
                model_name=MODEL,
                max_tokens=MAX_TOKENS,
                context_mode=context_mode,
            )
        )
        return {
            "answer": res.answer,
            "citations": [{"title": c.title, "uri": c.uri} for c in res.citations],
            "elapsed_s": secs,
            "error": None,
            # 1단이 뭘 골랐는지 — 팔 B 가 틀렸을 때 검색 탓인지 생성 탓인지 가른다.
            "stage1": [{"slug": p.slug, "score": round(s, 4)} for p, s in ret.pages],
            # 실제 주입한 원문. 인용 목록이 곧 주입 목록이다(`_citations` 가 같은 것을 낸다).
            "units": [c.uri for c in res.citations],
            # dense 만·BM25 만 썼으면 뭐가 1위였는지 — 하이브리드가 순위를 바꿨는지 본다.
            "retrieval": ret.debug,
        }
    except Exception as e:
        return _err(e, stage1=[], units=[])


async def run_hybrid(rag, q: str, system_prompt: str) -> dict:
    """팔 F — file_search 를 그대로 돌리되 BM25 로 뽑은 원문을 함께 준다.

    묻는 질문이 다르다. 팔 B~C 는 「위키가 file_search 를 **대체**하나」이고,
    이 팔은 「BM25 원문이 file_search 를 **보완**하나」다. dense 를 우리 쪽에서 뺀 이상
    이쪽이 진짜 가설이다 — 의미 검색은 file_search 가, 어휘 검색은 우리가 맡는 구성.

    원문은 **앞선 턴**으로 넣는다. 질문 앞에 붙이면 file_search 의 검색 질의가
    3,000자짜리 원문 덩어리로 오염돼, 재는 대상이 검색이 아니라 질의 오염이 된다.
    """
    try:
        index = await get_index(BOT_ID)
        ret = await index.search(q, top_k=3)
        units = _select_units(ret, "raw_budget")
        history = [
            {"role": "user", "content": f"# 참고 규정 원문\n{_context_block(units)}"},
            {"role": "assistant", "content": "확인했습니다. 질문해 주세요."},
        ]
        res, secs = await with_retry(
            lambda: rag.generate_with_rag(
                bot_id=BOT_ID,
                prompt=q,
                system_prompt=system_prompt + GUIDE,
                model_name=MODEL,
                max_tokens=MAX_TOKENS,
                history=history,
            )
        )
        return {
            "answer": res.answer,
            "citations": [{"title": c.title, "uri": c.uri} for c in res.citations],
            "elapsed_s": secs,
            "error": None,
            "stage1": [{"slug": p.slug, "score": round(s, 4)} for p, s in ret.pages],
            "units": [u.src_id for u in units],
            "retrieval": ret.debug,
        }
    except Exception as e:
        return _err(e, stage1=[], units=[])


_FULL_CONTEXT: str | None = None


async def full_context() -> str:
    """원문 250건 전체. 한 번 만들어 재사용한다 (≈146,000자 ≈ 73k 토큰)."""
    global _FULL_CONTEXT
    if _FULL_CONTEXT is None:
        index = await get_index(BOT_ID)
        _FULL_CONTEXT = "\n\n".join(
            f"[{u.src_id}] {u.doc} {u.locator}\n{u.text}"
            for u in index.units.values()
        )
    return _FULL_CONTEXT


async def run_full(q: str, system_prompt: str) -> dict:
    """팔 D — 검색을 0으로 만든 상한선. 프로덕션 후보가 아니다.

    "검색기가 교란변수였다"는 진단을 위에서 조인다. 전부 넣고도 못 맞히면
    그 문항의 근거는 애초에 코퍼스에 없다 — ③ 유보 정확도의 오라클로도 쓴다.
    """
    settings = get_settings()
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY.get_secret_value())
        contents = [
            types.Content(
                role="user",
                parts=[types.Part(text=f"# 규정 원문\n{await full_context()}\n\n# 질문\n{q}")],
            )
        ]
        response, secs = await with_retry(
            lambda: client.aio.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=(system_prompt + GUIDE) or None,
                    temperature=settings.RAG_TEMPERATURE,
                    max_output_tokens=MAX_TOKENS,
                ),
            )
        )
        return {
            "answer": (response.text or "").strip(),
            "citations": [],
            "elapsed_s": secs,
            "error": None,
        }
    except Exception as e:
        return _err(e)


async def main(limit: int | None, arms: set[str], retry_failed: bool = False) -> None:
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    if limit:
        questions = questions[:limit]

    system_prompt = await load_system_prompt()
    dense = os.environ["WIKI_DENSE_SCALES"] or "(없음 — BM25 전용)"
    print(f"봇 {BOT_ID} · {MODEL} · system_prompt {len(system_prompt)}자 · {len(questions)}문항")
    print(f"팔: {sorted(arms)} · dense 스케일: {dense}\n")

    rag = GeminiRAGService() if arms & {"A", "F"} else None

    # 이미 돈 팔은 다시 돌리지 않는다 — 팔 하나를 덧붙일 때 앞의 결과와 과금을 재활용한다.
    prev = {}
    if OUT.exists():
        prev = {r["n"]: r for r in json.loads(OUT.read_text(encoding="utf-8"))}
        # 실행 전 스냅샷. 하루 상한에 걸려 멀쩡한 결과를 ERR 로 덮어쓴 적이 있다.
        backup = OUT.with_name(f"{OUT.stem}_prev{OUT.suffix}")
        backup.write_text(OUT.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"실행 전 스냅샷 → {backup.name}")

    aborted = False
    results = []
    for i, item in enumerate(questions, 1):
        row = {k: item[k] for k in ("n", "question", "golden", "risk", "category",
                                    "keywords", "baseline_pct")}
        row.update({k: v for k, v in prev.get(item["n"], {}).items() if k in ARM_KEY.values()})

        try:
            for arm, key in ARM_KEY.items():
                if arm not in arms:
                    continue
                # 실패셀만 재시도 — 429 로 죽은 칸을 메울 때 쓴다. 이미 성공한 칸을 다시 부르면
                # 답변이 새로 생성돼 **앞서 감사·채점한 결과와 어긋난다.** 과금 절약이 아니라
                # 비교 가능성 때문에 건너뛴다.
                if retry_failed:
                    got = row.get(key) or {}
                    if (got.get("answer") or "").strip():
                        continue
                if arm == "A":
                    row[key] = await run_rag(rag, item["question"], system_prompt)
                elif arm == "F":
                    row[key] = await run_hybrid(rag, item["question"], system_prompt)
                elif arm == "D":
                    row[key] = await run_full(item["question"], system_prompt)
                else:
                    row[key] = await run_wiki(item["question"], system_prompt, ARM_MODE[arm])
        except DailyQuotaExhausted:
            # 남은 문항은 손대지 않는다. 이 문항의 앞선 결과도 되돌려 반쪽 행을 남기지 않는다.
            row = {**{k: item[k] for k in ("n", "question", "golden", "risk", "category",
                                           "keywords", "baseline_pct")},
                   **{k: v for k, v in prev.get(item["n"], {}).items() if k in ARM_KEY.values()}}
            results.append(row)
            aborted = True
            print(f"\n⚠ 생성 하루 상한(500회) 소진 — #{item['n']} 에서 중단. "
                  f"{i - 1}문항까지 저장됨. 태평양 자정(KST 16시)에 리셋된다")
            break

        for key in ARM_KEY.values():
            if key in row:
                row[key].update(score_keywords(row[key]["answer"], item["keywords"]))

        results.append(row)
        # 중간 저장. **처리하지 않은 문항은 앞선 실행 결과를 그대로 살려 둔다** —
        # `--limit 3` 으로 45문항 파일을 3행으로 덮어쓰는 사고를 한 번 냈다.
        merged = dict(prev)
        merged.update({r["n"]: r for r in results})
        OUT.write_text(
            json.dumps([merged[k] for k in sorted(merged)], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        bits = []
        for key in ARM_KEY.values():
            if key in row:
                r = row[key]
                bits.append(f"{key} {r['kw_pct']}% {r['elapsed_s']}s" + (" ERR" if r["error"] else ""))
        print(f"[{i:2d}/{len(questions)}] #{item['n']:<3} {' | '.join(bits)}  {item['question'][:30]}")

    # `--limit N` 으로 45행 파일을 N행으로 덮어쓴 사고가 있었다. 매번 확인한다.
    saved = json.loads(OUT.read_text(encoding="utf-8"))
    print(f"\n→ {OUT}  ({len(saved)}행)")
    if len(saved) != 45:
        print(f"  ⚠ 45행이 아니다 — {len(saved)}행. answers_2026-08-08_v1.json 에서 복구할 것")

    # 팔별 완비 현황. 중단됐거나 실패가 섞였으면 여기서 드러난다 — 평균만 보면 안 보인다.
    live = [k for k in ARM_KEY.values() if any(k in r for r in saved)]
    full = sum(1 for r in saved
               if all(k in r and not r[k].get("error") and r[k].get("answer") for k in live))
    print(f"  {len(live)}팔이 모두 성공한 문항: {full}/{len(saved)}건"
          + ("   ← 중단됨" if aborted else ""))

    for key in ARM_KEY.values():
        vals = [r[key]["kw_pct"] for r in results if key in r and r[key]["kw_pct"] is not None]
        errs = sum(1 for r in results if key in r and r[key]["error"])
        secs = [r[key]["elapsed_s"] for r in results if key in r]
        if vals:
            print(f"  {key:12} 키워드 평균 {sum(vals)/len(vals):.1f}% · "
                  f"평균 {sum(secs)/len(secs):.1f}초 · 실패 {errs}건")
    base = [r["baseline_pct"] for r in results if r.get("baseline_pct") is not None]
    if base:
        print(f"  (참고) 시트 ⑤ 기존 충족률 평균 {sum(base)/len(base):.1f}%")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--arms", default="A,B,B2,C")
    ap.add_argument("--retry-failed", action="store_true",
                    help="답변이 빈 칸(429 등으로 죽은 셀)만 다시 부른다. 성공한 칸은 그대로 둔다")
    a = ap.parse_args()
    asyncio.run(main(a.limit, {x.strip().upper() for x in a.arms.split(",")}, a.retry_failed))
