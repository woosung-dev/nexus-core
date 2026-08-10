"""재질문 트리거 측정 — 45문항.

    --stage judge      45문항에 B 판정을 돌린다 (Gemini 45회)
    --stage reanswer   ask 로 걸린 문항을 슬롯 선택지별로 되물어 다시 답한다
    --retry-failed     빈 셀만 다시 채운다. **재실행할 때는 반드시 붙인다.**

`_run.py`(wiki_eval) 규약을 그대로 따른다 — BM25 전용, 봇 11, 4.2초 페이싱,
`answers_prev.json` 스냅샷. 감사는 기존 자를 그대로 쓴다:

    AUDIT_DIR=$PWD/exports/clarify_eval AUDIT_ARMS=baseline,clarify \\
      uv run python -u ../exports/wiki_eval/_audit.py --stage all

산출:
    results.json   판정 단계 원장 (문항별 status·reason·missing·rule_id·주입 원문)
    answers.json   감사기가 먹을 수 있는 모양. arm 은 baseline(현행 어휘팔 냉동본)과 clarify.
"""

from __future__ import annotations

import argparse
import asyncio
import itertools
import json
import logging
import os
import sys
import time
from pathlib import Path

# ★ import 전에 dense 를 끈다 — 임베딩 API 를 한 번도 부르지 않는다 (_run.py:42 방식)
os.environ.setdefault("WIKI_DENSE_SCALES", "")

DIR = Path(__file__).resolve().parent
REPO = DIR.parents[1]
sys.path.insert(0, str(REPO / "backend"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO / "backend" / ".env")

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.schemas.clarification_policy import ClarificationPolicy  # noqa: E402
from app.services.clarification_service import retrieval_query_from_summary  # noqa: E402
from app.services.clarification_trigger import decide  # noqa: E402
from app.services.wiki.service import _select_units, answer_with_wiki  # noqa: E402
from app.services.wiki.store import get_index  # noqa: E402

BOT_ID = 11
MODEL = "gemini-3.5-flash-lite"
MAX_TOKENS = 2048
CONTEXT_MODE = "raw_budget"  # = retrieval_mode "lexical"
GEN_INTERVAL = 4.2  # 초. 쿼터 페이싱 — wiki_eval/_run.py 와 같은 값
MAX_BRANCHES = 4  # 문항당 슬롯 조합 상한. 넘으면 로그에 버린 수를 남긴다

QUESTIONS = REPO / "exports" / "wiki_eval" / "questions.json"
FROZEN = REPO / "exports" / "wiki_eval" / "answers.json"
POLICY = REPO / "docs" / "architecture" / "clarification-policy-seed-2026-08-11.json"
RESULTS = DIR / "results.json"
ANSWERS = DIR / "answers.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(DIR / "_run.log", encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger("clarify_eval")
# 인덱스 빌드·SQL 에코가 45번 반복되면 진행 상황을 읽을 수가 없다.
logging.getLogger("app.services.wiki.store").setLevel(logging.WARNING)
for noisy in ("sqlalchemy", "sqlalchemy.engine", "sqlalchemy.engine.Engine"):
    logging.getLogger(noisy).setLevel(logging.WARNING)
    logging.getLogger(noisy).propagate = False

_last_gen = 0.0


async def _paced() -> None:
    """생성 호출 간격을 벌린다. 쿼터를 한 번에 태우면 그날 측정이 끝난다."""
    global _last_gen
    gap = GEN_INTERVAL - (time.monotonic() - _last_gen)
    if gap > 0:
        await asyncio.sleep(gap)
    _last_gen = time.monotonic()


def _load_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _save(path: Path, payload) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def _policy() -> ClarificationPolicy:
    raw = _load_json(POLICY, {})
    return ClarificationPolicy.model_validate({k: v for k, v in raw.items() if not k.startswith("_")})


# 냉동 기준선(wiki_eval/answers.json)은 `system_prompt + GUIDE` 로 생성됐다.
# 재답변에서 이걸 빼면 프롬프트가 다른 두 시스템을 비교하게 된다 — 그대로 가져온다.
GUIDE = (
    "\n\n[근거 규칙]\n"
    "제공된 규정 자료에 근거해서만 답한다. 자료에 없는 내용은 지어내지 말고, "
    "확인되지 않는다고 말한 뒤 담당 부서 안내로 넘긴다."
)


async def _system_prompt() -> str:
    engine = create_async_engine(os.environ["DATABASE_URL"])
    async with engine.connect() as conn:
        prompt = (
            await conn.execute(text("select system_prompt from bots where id = :i"), {"i": BOT_ID})
        ).scalar()
    await engine.dispose()
    return prompt or ""


class _Bot:
    """`decide` 가 보는 최소 봇. DB 모델을 끌고 오지 않는다."""

    def __init__(self, system_prompt: str) -> None:
        self.id = BOT_ID
        self.llm_model = MODEL
        self.system_prompt = system_prompt
        self.clarification_policy = None


# ────────────────────────────────────────────────── ① 판정


async def stage_judge(retry_failed: bool) -> None:
    questions = _load_json(QUESTIONS, [])
    policy = _policy()
    bot = _Bot(await _system_prompt() + GUIDE)
    index = await get_index(BOT_ID)
    state = _load_json(RESULTS, {})

    for q in questions:
        key = str(q["n"])
        if retry_failed and (state.get(key) or {}).get("status"):
            continue

        retrieved = await index.search(q["question"], top_k=3)
        units = _select_units(retrieved, CONTEXT_MODE)
        await _paced()
        try:
            decision = await decide(
                question=q["question"], units=units, bot=bot, policy_override=policy
            )
            record = {
                "n": q["n"],
                "question": q["question"],
                "status": decision.status,
                "reason": decision.reason,
                "missing": decision.missing,
                "rule_id": decision.rule_id,
                "questions": [
                    {"id": c.id, "question": c.question, "options": c.options}
                    for c in decision.questions
                ],
                "injected": [u.src_id for u in units],
                "error": None,
            }
        except Exception as exc:  # 한 문항이 죽어도 나머지는 계속 — 재개는 --retry-failed
            log.warning("판정 실패 n=%s: %s", q["n"], exc)
            record = {"n": q["n"], "question": q["question"], "status": None, "error": str(exc)}

        state[key] = record
        _save(RESULTS, state)
        log.info("n=%-3s %-8s %s", q["n"], record.get("status"), record.get("reason", "")[:60])

    done = [r for r in state.values() if r.get("status")]
    log.info(
        "판정 완료 %d/%d — ask %d · handoff %d · answer %d",
        len(done),
        len(questions),
        sum(1 for r in done if r["status"] == "ask"),
        sum(1 for r in done if r["status"] == "handoff"),
        sum(1 for r in done if r["status"] == "answer"),
    )


# ────────────────────────────────────────────────── ② 되물은 뒤 재답변


def _branches(record: dict) -> list[list[tuple[str, str]]]:
    """슬롯 조합. 사용자를 지어내지 않으려고 선택지를 전수한다(상한까지)."""
    cards = record.get("questions") or []
    if not cards:
        return []
    combos = list(itertools.product(*[[(c["question"], o) for o in c["options"]] for c in cards]))
    if len(combos) > MAX_BRANCHES:
        log.info("n=%s 조합 %d개 중 %d개만 — 나머지는 버린다", record["n"], len(combos), MAX_BRANCHES)
    return [list(c) for c in combos[:MAX_BRANCHES]]


def _summary(question: str, picks: list[tuple[str, str]]) -> str:
    """`_ready_response` 와 같은 모양. 되물어 받은 답이 이 형식으로 들어온다."""
    lines = "\n".join(f"- {slot}: {value}" for slot, value in picks)
    return f"[요청 요약]\n- 최초 요청: {question}\n{lines}"


async def stage_reanswer(retry_failed: bool) -> None:
    results = _load_json(RESULTS, {})
    asked = [r for r in results.values() if r.get("status") == "ask"]
    if not asked:
        log.warning("ask 로 걸린 문항이 없다. --stage judge 를 먼저 돌려라.")
        return

    frozen = {r["n"]: r for r in _load_json(FROZEN, [])}
    system_prompt = await _system_prompt() + GUIDE
    rows = {r["n"]: r for r in _load_json(ANSWERS, [])}
    if ANSWERS.exists():
        _save(DIR / "answers_prev.json", list(rows.values()))

    for record in sorted(asked, key=lambda r: r["n"]):
        n = record["n"]
        # 냉동 기준선 — 현행 어휘팔이 실제로 낸 답. 새로 생성하지 않는다.
        base = (frozen.get(n) or {}).get("wiki_budget") or {}
        rows[str(n)] = {
            "n": str(n),
            "question": record["question"],
            "baseline": {
                "answer": base.get("answer", ""),
                "units": base.get("units") or [],
                "error": None,
            },
        }

        for i, picks in enumerate(_branches(record)):
            key = f"{n}b{i}"
            if retry_failed and (rows.get(key, {}).get("clarify", {}).get("answer") or "").strip():
                continue
            query = retrieval_query_from_summary(_summary(record["question"], picks))
            await _paced()
            try:
                response, retrieved = await answer_with_wiki(
                    bot_id=BOT_ID,
                    question=query,
                    system_prompt=system_prompt,
                    model_name=MODEL,
                    max_tokens=MAX_TOKENS,
                    context_mode=CONTEXT_MODE,
                )
                cell = {
                    "answer": response.answer,
                    "units": [c.uri for c in response.citations if c.uri],
                    "picks": picks,
                    "query": query,
                    "stage1": [{"slug": p.slug, "score": round(s, 4)} for p, s in retrieved.pages],
                    "error": None,
                }
            except Exception as exc:
                log.warning("재답변 실패 %s: %s", key, exc)
                cell = {"answer": "", "units": [], "picks": picks, "query": query, "error": str(exc)}

            rows[key] = {"n": key, "question": query, "clarify": cell}
            _save(ANSWERS, list(rows.values()))
            log.info("%-8s %s", key, (cell["answer"] or cell.get("error", ""))[:70].replace("\n", " "))

    filled = sum(1 for r in rows.values() if (r.get("clarify") or {}).get("answer"))
    log.info("재답변 완료 — 기준선 %d · 분기 %d", len(asked), filled)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["judge", "reanswer"], required=True)
    ap.add_argument("--retry-failed", action="store_true", help="빈 셀만 채운다. 재실행 시 필수.")
    args = ap.parse_args()

    if args.stage == "judge":
        asyncio.run(stage_judge(args.retry_failed))
    else:
        asyncio.run(stage_reanswer(args.retry_failed))


if __name__ == "__main__":
    main()
