# strict 게이트 측정 — 「마커 id 를 주입 목록과 대조한다」가 게이트로 쓸 만한가.
#
# 재는 것은 셋이다.
#   마커 출현율      답변에 근거 id 가 붙는 비율. 이게 낮으면 게이트가 멀쩡한 답을 죽인다
#   프롬프트 밖 id   주입하지 않은 id 를 썼는가. 0 이어야 대조가 성립한다
#   코퍼스 밖 id     아예 없는 id 를 지어냈는가
#
# **대조 대상은 원문 블록과 위키 블록 둘 다다.** 원문 유닛만으로 잡으면 위키 페이지가
# 싣고 있는 src id 를 「지어냄」으로 오판한다 — 인계 §2 의 거짓양성 2건이 그것이었다.
#
# 봇 29 로 잰다(11 아님). 인계가 인용한 현행 문구 「규정 근거를 밝힐 수 있으면 함께
# 언급합니다」는 봇 29 의 [출력 형식]에만 있다. 로컬 봇 11 은 opus2_v4(5,608자)로 그 문구가
# 없다. 봇 29 = 라이브 D-1 ver2 복제본(1,341자 · lexical · 위키 138쪽 · 봇 11 과 같은 코퍼스).
#
# `_run.py` 의 GUIDE 는 **붙이지 않는다.** 그것은 팔끼리 공정하게 비교하려고 건 장치이고,
# 여기서 재는 것은 프로덕션 경로 그대로의 거동이다. 붙이면 라이브와 다른 것을 재게 된다.
#
# 사용: cd backend && uv run python ../exports/wiki_eval/_gate_probe.py [--runs 2] [--limit N]
import argparse
import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path

DIR = Path(__file__).parent
sys.path.insert(0, str(DIR))
sys.path.insert(0, str(DIR.parents[1] / "backend"))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(DIR.parents[1] / "backend" / ".env")

# 빈 값 = 모든 스케일 BM25 전용. 임베딩 API 를 한 번도 부르지 않는다.
# 이 줄이 없으면 첫 요청에서 1,401건을 임베딩해 하루 상한(1,000회)을 넘긴다.
os.environ.setdefault("WIKI_DENSE_SCALES", "")

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.services.wiki.service import (  # noqa: E402
    _context_block,
    _select_units,
    _wiki_block,
    answer_with_wiki,
)
from app.services.wiki.store import get_index  # noqa: E402

# 페이싱·429 재시도는 `_run.py` 것을 그대로 쓴다. 복사하면 두 하네스가 갈라진다.
from _run import DailyQuotaExhausted, with_retry  # noqa: E402

BOT_ID = 29
MODEL = "gemini-3.5-flash-lite"
MAX_TOKENS = 2048
CONTEXT_MODE = "raw_budget"  # 프로덕션 어휘 경로와 같은 값 (chat_service.py:358)

OUT = DIR / "_gate_probe.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[logging.FileHandler(DIR / "_gate_probe.log", encoding="utf-8")],
)

# 인계 §2 가 실측에 쓴 문구 그대로. 여기서만 붙이고 DB 에는 저장하지 않는다.
FORCE_BLOCK = """

[인용 표기 — 반드시 지킬 것]
사실을 서술하는 문장은 **모두** 문장 끝에 근거를 [[src: id]] 형식으로 붙인다.
id 는 제공된 원문에 실제로 있는 것만 쓴다. 없으면 그 문장을 쓰지 않는다."""

# src_id 는 reg-* 100건 · glo-* 150건 두 가지뿐이다 (wiki_source_units 확인).
IDRE = re.compile(r"\b(?:reg|glo)-\d+\b")

# 관측된 마커 두 형식. `[[src: reg-3, glo-132]]` 와 `[근거: reg-25 ⑤]`.
# 대괄호 밖에 맨몸으로 쓴 id 도 인용으로 친다 — 게이트를 관대하게 잡아야 과잉 거절이 준다.
MARKER_RE = re.compile(r"\[\[?\s*(?:src|근거)\s*[::][^\]]*\]\]?")

# 코퍼스 밖 4문항. 앞 둘은 완전 무관, 뒤 둘은 **주제는 축복인데 규정집에 없는 것**이다.
# 뒤 둘이 진짜 시험이다 — 빈손이 아니라 엉뚱한 원문이 붙은 채 그럴듯하게 답하는 경우를 잡는다.
OUT_OF_CORPUS = [
    {"n": 901, "question": "오늘 서울 날씨 어때요?", "category": "코퍼스밖·무관"},
    {"n": 902, "question": "파이썬에서 리스트를 정렬하는 방법 알려주세요.", "category": "코퍼스밖·무관"},
    {"n": 903, "question": "2027년 세계 축복식은 언제 어디에서 열리나요?",
     "category": "코퍼스밖·축복"},
    {"n": 904, "question": "축복 가정이 반려동물을 키울 때 지켜야 할 규정이 있나요?",
     "category": "코퍼스밖·축복"},
]


def pick_questions(limit: int = 20) -> list[dict]:
    """카테고리 라운드로빈. 난수를 쓰지 않으므로 다시 돌려도 같은 20문항이다.

    45문항 중 위험도 `상` 이 28건이라 고르게 뽑아도 자연히 위험 문항 위주가 된다.
    """
    rows = json.loads((DIR / "questions.json").read_text(encoding="utf-8"))
    buckets: dict[str, list[dict]] = {}
    for r in rows:  # 파일 순서를 유지한다 — 카테고리 등장 순서가 곧 라운드로빈 순서다
        buckets.setdefault(r["category"], []).append(r)

    picked: list[dict] = []
    while len(picked) < limit and any(buckets.values()):
        for cat in list(buckets):
            if not buckets[cat]:
                continue
            picked.append(buckets[cat].pop(0))
            if len(picked) >= limit:
                break
    return picked


def marker_ids(answer: str) -> tuple[set[str], set[str]]:
    """(마커 안 id, 답변 전체 id). 둘을 따로 낸다 — 게이트를 어느 쪽으로 잡을지가 결정이다."""
    marked: set[str] = set()
    for m in MARKER_RE.findall(answer or ""):
        marked |= set(IDRE.findall(m))
    return marked, set(IDRE.findall(answer or ""))


async def load_corpus_ids() -> set[str]:
    engine = create_async_engine(os.environ["DATABASE_URL"])
    async with engine.connect() as conn:
        rows = (await conn.execute(text("select src_id from wiki_source_units"))).scalars().all()
    await engine.dispose()
    return set(rows)


async def load_system_prompt() -> str:
    engine = create_async_engine(os.environ["DATABASE_URL"])
    async with engine.connect() as conn:
        sp = (
            await conn.execute(text("select system_prompt from bots where id = :i"), {"i": BOT_ID})
        ).scalar()
    await engine.dispose()
    return sp or ""


async def probe(item: dict, prompt: str, corpus: set[str], index) -> dict:
    """문항 하나 × 팔 하나. 검색은 프로덕션과 같은 경로로 두 번 부르지 않는다."""
    q = item["question"]
    retrieved = await index.search(q, top_k=3)
    units = _select_units(retrieved, CONTEXT_MODE)
    # ⚠ 위키 블록도 반드시 함께. 원문 유닛만 잡으면 「지어냄」 거짓양성이 난다 (인계 §2)
    inprompt = set(IDRE.findall(_context_block(units) + "\n" + _wiki_block(retrieved)))

    try:
        (res, _), secs = await with_retry(
            lambda: answer_with_wiki(
                bot_id=BOT_ID,
                question=q,
                system_prompt=prompt,
                model_name=MODEL,
                max_tokens=MAX_TOKENS,
                context_mode=CONTEXT_MODE,
            )
        )
    except DailyQuotaExhausted:
        raise
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "answer": "", "inprompt": sorted(inprompt)}

    answer = res.answer or ""
    marked, allids = marker_ids(answer)
    return {
        "error": None,
        "answer": answer,
        "elapsed_s": secs,
        "empty": not answer.strip(),
        "stage1": [p.slug for p, _ in retrieved.pages],
        "inprompt": sorted(inprompt),
        "ids_marked": sorted(marked),
        "ids_all": sorted(allids),
        # 프롬프트 밖 / 코퍼스 밖. 관대한 쪽(ids_all)으로 잡아야 지어냄을 놓치지 않는다.
        "out_of_prompt": sorted(allids - inprompt),
        "out_of_corpus": sorted(allids - corpus),
    }


def summarize(rows: list[dict], runs: int) -> None:
    """코퍼스 안과 밖을 갈라서 낸다.

    섞으면 안 된다. 코퍼스 밖 문항은 **마커가 없는 게 정답**이라 함께 세면 출현율이
    가짜로 낮아진다. 게이트 판단에 쓸 수치는 코퍼스 안쪽 것이다.
    """
    print(f"\n{'=' * 78}\n봇 {BOT_ID} · {len(rows)}문항 · {runs}회\n{'=' * 78}")
    for label, want in (("코퍼스 안", False), ("코퍼스 밖", True)):
        subset = [r for r in rows if str(r["category"]).startswith("코퍼스밖") == want]
        print(f"\n[{label} {len(subset)}문항]")
        for arm in ("current", "forced"):
            for run in range(runs):
                cells = [r[arm][run] for r in subset if len(r.get(arm, [])) > run]
                ok = [c for c in cells if not c.get("error")]
                if not ok:
                    continue
                body = [c for c in ok if not c["empty"]]
                with_marker = [c for c in body if c["ids_all"]]
                oop = sum(len(c["out_of_prompt"]) for c in ok)
                ooc = sum(len(c["out_of_corpus"]) for c in ok)
                rate = 100 * len(with_marker) / len(body) if body else 0
                print(
                    f"  {arm:8} {run + 1}회차  마커 {len(with_marker):2d}/{len(body):2d}"
                    f" = {rate:5.1f}%   프롬프트밖 id {oop}   코퍼스밖 id {ooc}"
                    f"   빈답변 {len(ok) - len(body)}   실패 {len(cells) - len(ok)}"
                )

    print("\n[마커 없는 답변 — 직접 읽어야 할 것]")
    for r in rows:
        for arm in ("current", "forced"):
            for run, c in enumerate(r.get(arm, [])):
                if c.get("error") or c["empty"] or c["ids_all"]:
                    continue
                print(f"  #{r['n']:<4} {arm:8} {run + 1}회차  {r['question'][:44]}")


async def main(runs: int, limit: int) -> None:
    corpus = await load_corpus_ids()
    base = await load_system_prompt()
    index = await get_index(BOT_ID)
    print(f"봇 {BOT_ID} · 프롬프트 {len(base)}자 · 코퍼스 {len(corpus)}건 · "
          + " · ".join(f"{n} {len(s.ids)}" for n, s in index.scales.items()))

    items = pick_questions(limit) + OUT_OF_CORPUS
    arms = {"current": base, "forced": base + FORCE_BLOCK}
    rows = [{**{k: it.get(k) for k in ("n", "question", "category", "risk")},
             "current": [], "forced": []} for it in items]

    aborted = False
    try:
        for run in range(runs):
            for i, (item, row) in enumerate(zip(items, rows), 1):
                for arm, prompt in arms.items():
                    cell = await probe(item, prompt, corpus, index)
                    row[arm].append(cell)
                    mark = "-" if cell.get("error") else (
                        "빈답" if cell["empty"] else (
                            ",".join(cell["ids_all"][:3]) or "마커없음"))
                    print(f"[{run + 1}/{runs}] {i:2d}/{len(items)} #{item['n']:<4} "
                          f"{arm:8} {mark}")
                # 한 문항이 끝날 때마다 쓴다 — 하루 상한에 걸려도 앞선 결과를 잃지 않는다
                OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    except DailyQuotaExhausted as e:
        aborted = True
        print(f"\n⚠ 하루 생성 상한 — 여기까지만 저장됐다: {str(e)[:120]}")

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    summarize(rows, runs)
    print(f"\n→ {OUT}" + ("   ← 중단됨" if aborted else ""))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--limit", type=int, default=20, help="코퍼스 안 문항 수 (밖 4문항은 항상 붙는다)")
    a = ap.parse_args()
    asyncio.run(main(a.runs, a.limit))
