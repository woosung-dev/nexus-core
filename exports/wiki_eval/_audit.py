"""근거 위반 탐지기 — 「이 답의 주장이 규정 원문에 있는가」를 정답지 없이 잰다.

## 왜

지금 유해를 셀 수 있는 건 관리자 정답 10건 위에서뿐이다. 팔 간 격차(±0.5)와 채점 잡음(±0.6)이
같은 크기라 n=10 으로는 아무것도 못 가른다(handoff-wiki-retrieval-2026-08-08.md §2-5).

정답지 없이 잴 수 있는 것이 하나 있다 — 「이 답의 주장이 규정 원문에 있는가」.
정답이 필요 없으므로 45문항 전체, 나중엔 회귀 하네스·실제 대화 로그까지 같은 자로 잰다.

## 방법 — 프로덕션 기법의 반전

`backend/app/services/rag/evidence.py` 는 「LLM 추출 + 원문 대조」로 카드 95% 를 달성했다
(어휘 매칭은 25% 로 기각). `snap_to_source` 는 모델이 낸 문자열을 쓰지 않고 원문 위 위치를
찾는 데만 쓰고, 못 찾으면 버린다. **이걸 뒤집는다: 근거 구절을 못 찾은 주장 = 근거 없는 주장.**

팔 A 는 무엇을 검색했는지 알 수 없으므로(grounding 보고 부실) 주입 근거가 아니라
**코퍼스 전체 250건**에 대고 대조한다.

## 단계

    1 분해   답변 → 사실 주장 목록          codex   (의견·인사말·안내문구 제외)
    2 후보   주장별 BM25 상위 5             로컬 · API 0회
    3 대조   지지 / 미지지 / 모순 + 원문 인용  codex
    3′ 스냅  인용이 원문에 실재하는지         로컬 · snap_to_source
    4 적대   미지지·모순만 3시선이 반박 시도    codex   (2명 이상 뒤집으면 기각)
    5 종합   팔별 위반율 + 문항별 위반 목록

Gemini 호출 0회. codex 는 구독이라 과금 0.

## 사용

    cd backend && uv run python -u ../exports/wiki_eval/_audit.py --stage all
    cd backend && uv run python -u ../exports/wiki_eval/_audit.py --selftest

단계별 재실행이 가능하다(resume-safe). `audit.json` 에 완료분이 남고 다시 안 부른다.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ★ import 전에 dense 를 끈다 — 임베딩 API 를 한 번도 부르지 않기 위한 것이다 (_run.py:42 방식)
os.environ.setdefault("WIKI_DENSE_SCALES", "")

# 다른 측정 세트(재질문 하네스 등)를 같은 자로 재려고 디렉터리·팔을 환경변수로 연다.
# 기본값은 이 디렉터리 · 5팔이므로 기존 실행은 그대로다.
DIR = Path(os.getenv("AUDIT_DIR") or Path(__file__).resolve().parent)
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO / "backend" / ".env")

from app.services.rag.evidence import snap_to_source  # noqa: E402
from app.services.wiki.store import get_index  # noqa: E402

BOT_ID = 11
ANSWERS = DIR / "answers.json"
OUT = DIR / "audit.json"
LOG = DIR / "_audit.log"

# 측정 5팔. 키는 answers.json 의 셀 키다 (_run.py:73 ARM_KEY).
ARMS = (os.getenv("AUDIT_ARMS") or "rag,wiki,wiki_budget,wiki_first,hybrid").split(",")
ARM_LABEL = {
    "rag": "A · file_search",
    "wiki": "B · 위키→원문 24건",
    "wiki_budget": "B′ · 예산 3,000자",
    "wiki_first": "C · 위키 본문",
    "hybrid": "F · A + BM25 원문",
}

CANDIDATES = 5      # ② 후보 검색 상위 N
WIDE = 10           # ④ b·c 시선이 보는 넓은 후보
WORKERS = 8         # codex 병렬 (12코어)
WORKERS_HEAVY = 3   # ④-a 는 코퍼스 전체를 실으므로 낮춘다
TIMEOUT = 1800
REASONING = "medium"
DECOMPOSE_BATCH = 3
MAX_CLAIMS = 12

_WRITE_LOCK = threading.Lock()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("audit")


# ────────────────────────────────────────────────────────────── codex

def codex(instruction: str, payload, schema: dict, tries: int = 3, label: str = ""):
    """codex exec 한 번. `--output-schema` 로 형식을 강제하고 `-o` 로 최종 메시지만 받는다.

    stdout 파싱(`_grade.py` 의 greedy 정규식, `_branches.py` 의 raw_decode 스캔)보다 견고하다 —
    codex 가 프롬프트와 훅 로그를 stdout 에 함께 뱉기 때문에 `[` ~ `]` 슬라이싱은 깨진다.
    """
    last: Exception = RuntimeError("codex 호출 실패")
    for attempt in range(tries):
        with tempfile.TemporaryDirectory() as td:
            sf, of = Path(td) / "schema.json", Path(td) / "out.json"
            sf.write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")
            try:
                p = subprocess.run(
                    ["codex", "exec", instruction,
                     "-s", "read-only", "--ephemeral", "--skip-git-repo-check",
                     "-c", f'model_reasoning_effort="{REASONING}"',
                     "--output-schema", str(sf), "-o", str(of)],
                    input=json.dumps(payload, ensure_ascii=False),
                    capture_output=True, text=True, cwd=str(REPO), timeout=TIMEOUT,
                )
            except subprocess.TimeoutExpired:
                last = RuntimeError(f"codex timeout {TIMEOUT}s")
                log.warning("  %s 타임아웃 — 재시도 %d/%d", label, attempt + 1, tries)
                continue
            if p.returncode != 0:
                last = RuntimeError(f"codex exit {p.returncode}: {p.stderr[-300:]}")
                log.warning("  %s exit=%s — 재시도 %d/%d", label, p.returncode, attempt + 1, tries)
                continue
            if not of.exists():
                last = RuntimeError("출력 파일 없음")
                log.warning("  %s 출력 없음 — 재시도 %d/%d", label, attempt + 1, tries)
                continue
            try:
                return json.loads(of.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                last = e
                log.warning("  %s JSON 오류 — 재시도 %d/%d", label, attempt + 1, tries)
    raise last


def _schema(item_props: dict, required: list[str]) -> dict:
    """{"results": [ ...item... ]} 형태의 최상위 스키마."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["results"],
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": required,
                    "properties": item_props,
                },
            }
        },
    }


# ────────────────────────────────────────────────────────────── 상태

def load_state() -> dict:
    if OUT.exists():
        return json.loads(OUT.read_text(encoding="utf-8"))
    return {"version": 1, "cells": {}}


def save_state(state: dict) -> None:
    with _WRITE_LOCK:
        tmp = OUT.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(OUT)


def load_cells() -> dict:
    """answers.json 에서 성공한 셀만. 키는 `{n}:{arm}`."""
    rows = json.loads(ANSWERS.read_text(encoding="utf-8"))
    cells = {}
    for r in rows:
        for arm in ARMS:
            c = r.get(arm) or {}
            if c.get("error") or not (c.get("answer") or "").strip():
                continue
            cells[f"{r['n']}:{arm}"] = {
                "n": r["n"], "arm": arm,
                "question": r["question"],
                "answer": c["answer"],
                "injected": c.get("units") or [c["uri"] for c in c.get("citations", []) if c.get("uri")],
            }
    return cells


# ────────────────────────────────────────────────────────────── ① 분해

DECOMPOSE = """너는 종교(세계평화통일가정연합) 축복·가정관리 챗봇의 답변에서 「사실 주장」만 뽑아내는 분해기다.

<stdin> 으로 JSON 배열이 온다. 각 항목: {key, question, answer}

각 답변을 검증 가능한 원자적 사실 주장으로 쪼개라.

주장으로 세는 것 — 규정·절차·수치·기간·자격·명칭·소속·금액·순서·조건에 관한 단정.

주장으로 세지 않는 것:
  - 인사말·공감·위로 (「마음이 많이 힘드셨겠습니다」)
  - 의견·권유·해석 (「~하시길 권합니다」, 「~이 중요합니다」, 「기도가 도움이 됩니다」)
  - 안내 문구 (「자세한 것은 담당자에게 문의하세요」, 「확인되지 않습니다」, 「규정에 없습니다」)
  - 되묻는 질문
  - 답변이 스스로 불확실하다고 밝힌 것 (「~일 수 있습니다」, 「~로 알려져 있습니다」)

규칙:
  - 한 주장에 검증 가능한 사실 하나만. 「만 20세 이상이고 부모 동의가 필요하다」 → 2개로 쪼갠다
  - 답변의 표현을 최대한 그대로 쓰되 대명사·생략어는 풀어 쓴다 (「그 경우」 → 무슨 경우인지 명시)
  - 주장이 하나도 없으면 빈 배열
  - 한 답변에서 최대 12개. 넘으면 중요한 것부터 12개

설명 없이 results 배열만 낸다. 입력과 같은 개수·순서·key 로."""

DECOMPOSE_SCHEMA = _schema(
    {"key": {"type": "string"},
     "claims": {"type": "array", "items": {"type": "string"}}},
    ["key", "claims"],
)


def stage_decompose(state: dict, cells: dict) -> None:
    todo = [k for k in cells if "claims" not in state["cells"].get(k, {})]
    if not todo:
        log.info("① 분해 — 할 일 없음")
        return
    batches = [todo[i:i + DECOMPOSE_BATCH] for i in range(0, len(todo), DECOMPOSE_BATCH)]
    log.info("① 분해 — %d셀 / %d배치", len(todo), len(batches))

    def run(batch):
        payload = [{"key": k, "question": cells[k]["question"], "answer": cells[k]["answer"]}
                   for k in batch]
        res = codex(DECOMPOSE, payload, DECOMPOSE_SCHEMA, label=f"분해 {batch[0]}")
        return batch, {r["key"]: r["claims"][:MAX_CLAIMS] for r in res.get("results", [])}

    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(run, b): b for b in batches}
        for f in as_completed(futs):
            batch = futs[f]
            try:
                _, mapping = f.result()
            except Exception as e:  # 이 배치만 포기하고 기록한다
                log.error("① 배치 실패 %s: %s", batch, e)
                continue
            for k in batch:
                cell = state["cells"].setdefault(k, dict(cells[k]))
                cell["claims"] = [
                    {"id": f"{k}#{i}", "text": t}
                    for i, t in enumerate(mapping.get(k, []))
                    if t and t.strip()
                ]
            done += len(batch)
            save_state(state)
            log.info("  ① %d/%d", done, len(todo))


# ────────────────────────────────────────────────────────────── ② 후보 검색 (로컬 · 무료)

async def stage_candidates(state: dict, units: dict) -> None:
    index = await get_index(BOT_ID)
    todo = [(k, c) for k, cell in state["cells"].items()
            for c in cell.get("claims", []) if "cand" not in c]
    if not todo:
        log.info("② 후보 — 할 일 없음")
        return
    log.info("② 후보 — 주장 %d건 (BM25 로컬 · API 0회)", len(todo))
    for i, (_, claim) in enumerate(todo, 1):
        ret = await index.search(claim["text"], top_k=3)
        claim["cand"] = [u.src_id for u, _ in ret.ranked_units[:WIDE]]
        if i % 200 == 0:
            log.info("  ② %d/%d", i, len(todo))
    save_state(state)
    log.info("  ② 완료 %d건", len(todo))


# ────────────────────────────────────────────────────────────── ③ 대조

VERIFY = """너는 규정 원문과 주장을 대조하는 심사관이다.

<stdin> 으로 JSON 객체가 온다:
  question — 사용자 질문 (맥락 참고용)
  sources  — 후보 원문 [{src_id, doc, locator, text}]
  claims   — 판정 대상 [{id, text, cand}] · cand 는 그 주장의 후보 src_id 목록

각 주장을 그 주장의 cand 원문에 대고 판정하라.

  지지   — 후보 원문이 그 주장을 직접 뒷받침한다
  미지지 — 후보 원문에 그 내용이 없다 (틀렸다는 뜻이 아니다. 이 후보들로는 확인이 안 된다는 뜻)
  모순   — 후보 원문이 그 주장과 다르게 말한다

「지지」 또는 「모순」이면 반드시 함께 낸다:
  src_id — 근거가 된 후보의 src_id (cand 안에 있어야 한다)
  quote  — 그 원문에서 **한 글자도 바꾸지 않고 그대로 복사한** 20~150자 구간.
           요약·의역·존댓말 변환·줄임 금지. 원문에 없는 문자열을 쓰면 그 판정은 무효 처리된다.
「미지지」면 src_id 와 quote 는 빈 문자열로 둔다.

반드시 지킬 것:
  - 원문은 PDF 추출본이라 숫자와 한글 사이에 공백이 있다 —「만 20 세」·「제 55 조」·「15,000 원」.
    공백 차이는 무시하고 같은 것으로 본다. quote 는 원문에 있는 그대로(공백 포함) 복사한다.
  - 표현이 달라도 같은 내용이면 지지다. 어휘가 겹쳐도 다른 내용이면 지지가 아니다.
  - 확신이 어려우면 「지지」로 하지 마라. 미지지로 두면 뒤 단계가 더 넓게 다시 본다.
  - 주장이 후보 원문의 내용을 **일반화·확대**한 것이면 지지가 아니다.
    (원문이 특정 대상에만 적용된다고 하는데 주장이 전체에 적용된다고 하면 미지지 또는 모순)

설명 없이 results 배열만. 입력 claims 와 같은 개수·순서·id 로."""

VERIFY_SCHEMA = _schema(
    {"id": {"type": "string"},
     "verdict": {"type": "string", "enum": ["지지", "미지지", "모순"]},
     "src_id": {"type": "string"},
     "quote": {"type": "string"},
     "reason": {"type": "string"}},
    ["id", "verdict", "src_id", "quote", "reason"],
)


def _src_payload(src_ids, units) -> list[dict]:
    out = []
    for s in src_ids:
        u = units.get(s)
        if u:
            out.append({"src_id": s, "doc": u["doc"], "locator": u["locator"], "text": u["text"]})
    return out


def stage_verify(state: dict, units: dict) -> None:
    todo = [k for k, cell in state["cells"].items()
            if cell.get("claims") and any("verdict" not in c for c in cell["claims"])]
    if not todo:
        log.info("③ 대조 — 할 일 없음")
        return
    log.info("③ 대조 — %d셀", len(todo))

    def run(k):
        cell = state["cells"][k]
        claims = [c for c in cell["claims"] if "verdict" not in c]
        pool = sorted({s for c in claims for s in c["cand"][:CANDIDATES]})
        payload = {
            "question": cell["question"],
            "sources": _src_payload(pool, units),
            "claims": [{"id": c["id"], "text": c["text"], "cand": c["cand"][:CANDIDATES]}
                       for c in claims],
        }
        res = codex(VERIFY, payload, VERIFY_SCHEMA, label=f"대조 {k}")
        return k, {r["id"]: r for r in res.get("results", [])}

    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(run, k): k for k in todo}
        for f in as_completed(futs):
            k = futs[f]
            try:
                _, mapping = f.result()
            except Exception as e:
                log.error("③ 셀 실패 %s: %s", k, e)
                continue
            for c in state["cells"][k]["claims"]:
                r = mapping.get(c["id"])
                if not r:
                    continue
                c["verdict"] = r["verdict"]
                c["src_id"] = r.get("src_id") or ""
                c["quote"] = r.get("quote") or ""
                c["reason"] = r.get("reason") or ""
                _snap(c, units)
            done += 1
            save_state(state)
            if done % 10 == 0:
                log.info("  ③ %d/%d", done, len(todo))
    log.info("  ③ 완료 %d/%d", done, len(todo))


# ────────────────────────────────────────────────────────────── ③′ 인용 스냅 (로컬)

def _snap(claim: dict, units: dict) -> None:
    """codex 가 낸 quote 가 원문에 실재하는지. 없으면 「지지」를 무효화한다.

    `evidence.py` 의 snap_to_source 를 그대로 쓴다 — 모델이 낸 문자열을 신뢰하지 않고
    원문 위 위치를 찾는 데만 쓰고, 못 찾으면 버린다. 이 검사가 없으면 codex 가 지어낸
    인용으로 「지지」가 통과해 위반율이 과소평가된다.
    """
    if claim["verdict"] == "미지지":
        claim["snap"] = None
        return
    q = claim.get("quote") or ""
    pool = [claim.get("src_id")] + list(claim.get("cand", []))
    for s in pool:
        u = units.get(s)
        if not u:
            continue
        hit = snap_to_source(q, u["text"])
        if hit:
            claim["snap"] = True
            claim["snap_src"] = s
            claim["snap_text"] = hit
            return
    claim["snap"] = False
    # 인용을 못 붙였으므로 이 판정은 신뢰할 수 없다 → 미지지로 낮춰 ④에서 다시 본다
    claim["verdict_raw"] = claim["verdict"]
    claim["verdict"] = "미지지"


# ────────────────────────────────────────────────────────────── ④ 적대 검증

_COMMON_TAIL = """
반드시 지킬 것:
  - 원문은 PDF 추출본이라 숫자와 한글 사이에 공백이 있다 —「만 20 세」·「제 55 조」·「15,000 원」.
    공백 차이는 무시하고 같은 것으로 본다.
  - grounded=true 로 뒤집을 때는 src_ids 를 반드시 대고, quote 는 원문에서 한 글자도 바꾸지 않고
    그대로 복사한다. 지어낸 인용은 무효 처리된다.
  - 억지로 뒤집지 마라. 근거가 정말 없으면 grounded=false 가 옳은 답이다.

설명 없이 results 배열만. 입력 claims 와 같은 개수·순서·id 로."""

ADV_A = """너는 「이 주장은 규정에 근거가 없다」는 판정을 뒤집으려는 반대 심문관이다.

<stdin>: {corpus, claims: [{id, question, text, prior_reason}]}

corpus 는 이 봇이 가진 **원문 전체**다. 코퍼스는 이것이 전부이고 다른 자료는 없다.
각 주장에 대해 corpus 를 처음부터 끝까지 뒤져서, 뒷받침하는 대목이 **정말로** 없는지 확인하라.
앞 단계는 어휘 검색으로 후보 5건만 봤다. 검색이 놓쳤을 뿐인 근거가 있을 수 있다 — 그걸 찾는 것이 네 일이다.

  grounded=true  — corpus 어딘가에 이 주장을 뒷받침하는 대목이 있다
  grounded=false — corpus 전체를 봐도 없다
""" + _COMMON_TAIL

ADV_B = """너는 「표현만 다른 것 아닌가」를 보는 반대 심문관이다.

<stdin>: {sources, claims: [{id, question, text, cand, prior_reason}]}

앞 단계가 「근거 없음」으로 본 주장들이다. 그런데 원문과 주장이 **같은 내용을 다른 말로**
하고 있을 수 있다 — 존댓말 변환, 요약, 동의어, 어순 변경, 한자어↔고유어, 조문 번호 표기 차이.

각 주장이 cand 원문과 실질적으로 같은 내용인지 보라.
  grounded=true  — 표현만 다를 뿐 같은 내용이다
  grounded=false — 표현이 아니라 내용이 다르다 (또는 원문에 아예 없다)

어휘가 겹치는 것만으로 true 로 하지 마라. **말하는 바가 같아야** true 다.
""" + _COMMON_TAIL

ADV_C = """너는 「여러 조문에 나뉘어 있는 것 아닌가」를 보는 반대 심문관이다.

<stdin>: {sources, claims: [{id, question, text, cand, prior_reason}]}

앞 단계는 조문을 하나씩 봤다. 한 조문이 통째로 말하지 않아도 **둘 이상을 합치면** 그 주장이
도출될 수 있다 (정의는 대사전에, 절차는 규정집에 있는 식).

  grounded=true  — 주어진 원문 둘 이상을 합치면 그 주장이 도출된다. src_ids 에 전부 댄다
  grounded=false — 합쳐도 도출되지 않는다

합쳐서 「추론」하는 것과 「도출」하는 것을 구분하라. 원문에 없는 전제를 끼워 넣어야 성립하면 false 다.
""" + _COMMON_TAIL

ADV_SCHEMA = _schema(
    {"id": {"type": "string"},
     "grounded": {"type": "boolean"},
     "src_ids": {"type": "array", "items": {"type": "string"}},
     "quote": {"type": "string"},
     "reason": {"type": "string"}},
    ["id", "grounded", "src_ids", "quote", "reason"],
)

ADV_BATCH = {"a": 12, "b": 8, "c": 8}


def _pending_claims(state: dict) -> list[dict]:
    out = []
    for cell in state["cells"].values():
        for c in cell.get("claims", []):
            if c.get("verdict") in ("미지지", "모순"):
                c["_n"], c["_arm"], c["_q"] = cell["n"], cell["arm"], cell["question"]
                out.append(c)
    return out


def stage_adversarial(state: dict, units: dict, corpus: str) -> None:
    for lens in ("a", "b", "c"):
        todo = [c for c in _pending_claims(state) if lens not in c.get("adv", {})]
        if not todo:
            log.info("④-%s — 할 일 없음", lens)
            continue
        size = ADV_BATCH[lens]
        batches = [todo[i:i + size] for i in range(0, len(todo), size)]
        workers = WORKERS_HEAVY if lens == "a" else WORKERS
        log.info("④-%s — 주장 %d건 / %d배치 (병렬 %d)", lens, len(todo), len(batches), workers)

        def run(batch, lens=lens):
            claims = [{"id": c["id"], "question": c["_q"], "text": c["text"],
                       "prior_reason": c.get("reason", "")} for c in batch]
            if lens == "a":
                payload = {"corpus": corpus, "claims": claims}
                instr = ADV_A
            else:
                pool = sorted({s for c in batch for s in c["cand"][:WIDE]})
                for cl, c in zip(claims, batch):
                    cl["cand"] = c["cand"][:WIDE]
                payload = {"sources": _src_payload(pool, units), "claims": claims}
                instr = ADV_B if lens == "b" else ADV_C
            res = codex(instr, payload, ADV_SCHEMA, label=f"④-{lens} {batch[0]['id']}")
            return {r["id"]: r for r in res.get("results", [])}

        done = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(run, b): b for b in batches}
            for f in as_completed(futs):
                batch = futs[f]
                try:
                    mapping = f.result()
                except Exception as e:
                    log.error("④-%s 배치 실패 %s: %s", lens, batch[0]["id"], e)
                    continue
                for c in batch:
                    r = mapping.get(c["id"])
                    if not r:
                        continue
                    adv = c.setdefault("adv", {})
                    grounded = bool(r["grounded"])
                    if grounded:
                        # 뒤집었다면 인용이 원문에 실재해야 인정한다
                        ok = False
                        for s in (r.get("src_ids") or []) + list(c.get("cand", [])):
                            u = units.get(s)
                            if u and snap_to_source(r.get("quote") or "", u["text"]):
                                ok = True
                                break
                        if lens == "c":
                            ok = ok or bool(r.get("src_ids"))  # 합성 근거는 단일 인용이 없을 수 있다
                        grounded = ok
                    adv[lens] = {"grounded": grounded, "src_ids": r.get("src_ids") or [],
                                 "quote": r.get("quote") or "", "reason": r.get("reason") or "",
                                 "claimed": bool(r["grounded"])}
                done += len(batch)
                save_state(state)
                log.info("  ④-%s %d/%d", lens, done, len(todo))
        _strip_temp(state)


PROMPT_CHECK = """너는 「규정 원문에 없다」로 판정된 주장이 **시스템 프롬프트**에서 온 것인지 가려내는 심사관이다.

<stdin>: {system_prompt, claims: [{id, text}]}

봇에게는 규정 원문 말고도 시스템 프롬프트가 주어진다. 프롬프트에 적혀 있는 내용을 답한 것은
「없는 것을 지어냈다」와 성격이 다르다 — 전화번호·연락처·안내 문구가 대표적이다.

각 주장이 system_prompt 안에 있는지 판정하라.
  in_prompt=true  — 프롬프트에 그 내용이 있다 (표현이 달라도 같은 내용이면 true)
  in_prompt=false — 프롬프트에도 없다

설명 없이 results 배열만. 입력과 같은 개수·순서·id 로."""

PROMPT_SCHEMA = _schema(
    {"id": {"type": "string"}, "in_prompt": {"type": "boolean"}, "reason": {"type": "string"}},
    ["id", "in_prompt", "reason"],
)


def _system_prompt() -> str:
    """봇 11 의 system_prompt 를 라이브 DB 에서 읽는다 (SELECT 만 · _run.py:178-185 와 같은 방식)."""
    import asyncio

    async def go():
        # ORM 이 아니라 컬럼 하나만 raw 로 읽는다 — 모델에 새 컬럼이 생겨도(마이그레이션 전이라
        # 라이브 DB 에 없어도) 이 스크립트가 깨지지 않는다. 실제로 한 번 그렇게 깨졌다.
        #
        # 엔진도 여기서 새로 만든다. app.core.database 의 전역 엔진은 앞선 `asyncio.run`
        # (인덱스 로딩)의 이벤트 루프에 묶여 있어 두 번째 루프에서 쓰면
        # "attached to a different loop" 로 죽는다.
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy.pool import NullPool
        from app.core.config import get_settings

        url = get_settings().DATABASE_URL
        engine = create_async_engine(str(url), poolclass=NullPool)
        try:
            async with engine.connect() as conn:
                row = await conn.execute(
                    text("SELECT system_prompt FROM bots WHERE id = :i"), {"i": BOT_ID})
                return row.scalar_one() or ""
        finally:
            await engine.dispose()

    return asyncio.run(go())


def stage_prompt_check(state: dict) -> None:
    """위반으로 남은 주장 중 시스템 프롬프트에서 온 것을 가른다.

    「가정행복국 전화번호」처럼 프롬프트가 준 사실을 「규정에 없다」로만 세면 위반의 성격이 섞인다.
    규정 위반(=지어냄)과 프롬프트 출처를 나눠서 보고해야 관리자에게 넘길 목록이 쓸모 있다.
    """
    todo = [c for cell in state["cells"].values() for c in cell.get("claims", [])
            if c.get("violation") and "in_prompt" not in c]
    if not todo:
        log.info("④′ 프롬프트 대조 — 할 일 없음")
        return
    sp = _system_prompt()
    log.info("④′ 프롬프트 대조 — %d건 (system_prompt %d자)", len(todo), len(sp))
    batches = [todo[i:i + 15] for i in range(0, len(todo), 15)]

    def run(batch):
        payload = {"system_prompt": sp,
                   "claims": [{"id": c["id"], "text": c["text"]} for c in batch]}
        res = codex(PROMPT_CHECK, payload, PROMPT_SCHEMA, label=f"④′ {batch[0]['id']}")
        return {r["id"]: r for r in res.get("results", [])}

    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(run, b): b for b in batches}
        for f in as_completed(futs):
            batch = futs[f]
            try:
                mapping = f.result()
            except Exception as e:
                log.error("④′ 배치 실패 %s: %s", batch[0]["id"], e)
                continue
            for c in batch:
                r = mapping.get(c["id"])
                if r:
                    c["in_prompt"] = bool(r["in_prompt"])
            done += len(batch)
            save_state(state)
    log.info("  ④′ 완료 %d/%d", done, len(todo))


def _strip_temp(state: dict) -> None:
    for cell in state["cells"].values():
        for c in cell.get("claims", []):
            for t in ("_n", "_arm", "_q"):
                c.pop(t, None)
    save_state(state)


# ────────────────────────────────────────────────────────────── ⑤ 종합

def finalize(state: dict) -> None:
    """적대 검증 2명 이상이 뒤집으면 위반 기각."""
    for cell in state["cells"].values():
        for c in cell.get("claims", []):
            v = c.get("verdict")
            if v is None:
                continue
            if v == "지지":
                c["violation"] = False
                c["final"] = "지지"
                continue
            adv = c.get("adv", {})
            votes = sum(1 for x in adv.values() if x.get("grounded"))
            c["adv_votes"] = votes
            if votes >= 2:
                c["violation"] = False
                c["final"] = "기각(적대검증)"
            else:
                c["violation"] = True
                c["final"] = "모순" if v == "모순" else "미지지"
    save_state(state)


def summarize(state: dict) -> dict:
    cells = state["cells"]
    by_n = {}
    for k, cell in cells.items():
        by_n.setdefault(cell["n"], set()).add(cell["arm"])
    complete = {n for n, arms in by_n.items() if set(ARMS) <= arms}

    def agg(keys):
        out = {}
        for arm in ARMS:
            mine = [k for k in keys if cells[k]["arm"] == arm]
            claims = [c for k in mine for c in cells[k].get("claims", []) if "violation" in c]
            viol = [c for c in claims if c["violation"]]
            # 프롬프트 출처는 「규정에 없다」가 맞지만 지어낸 것과 성격이 다르다 — 나눠서 낸다
            fabricated = [c for c in viol if not c.get("in_prompt")]
            n_contra = sum(1 for c in claims if c.get("final") == "모순")
            out[arm] = {
                "cells": len(mine),
                "silent_cells": sum(1 for k in mine if not cells[k].get("claims")),
                "claims": len(claims),
                "violations": len(viol),
                "fabricated": len(fabricated),
                "from_prompt": len(viol) - len(fabricated),
                "contradictions": n_contra,
                "rate": round(100 * len(viol) / len(claims), 1) if claims else None,
                "fab_rate": round(100 * len(fabricated) / len(claims), 1) if claims else None,
                "per_cell": round(len(fabricated) / len(mine), 2) if mine else None,
            }
        return out

    return {
        "complete_questions": sorted(complete),
        "primary": agg([k for k, c in cells.items() if c["n"] in complete]),
        "all": agg(list(cells)),
    }


def print_summary(state: dict) -> None:
    s = summarize(state)
    for tag, title in (("primary", f"주표 — 5팔 완비 {len(s['complete_questions'])}문항"),
                       ("all", "부표 — 성공셀 전체")):
        print(f"\n## {title}")
        print(f"{'팔':<22} {'셀':>4} {'무주장':>6} {'주장':>5} {'지어냄':>6} "
              f"{'프롬프트':>8} {'모순':>4} {'지어냄율':>9} {'셀당':>6}")
        for arm in ARMS:
            r = s[tag][arm]
            fr = f"{r['fab_rate']}%" if r["fab_rate"] is not None else "—"
            pc = r["per_cell"] if r["per_cell"] is not None else "—"
            print(f"{ARM_LABEL[arm]:<22} {r['cells']:>4} {r['silent_cells']:>6} {r['claims']:>5} "
                  f"{r['fabricated']:>6} {r['from_prompt']:>8} {r['contradictions']:>4} "
                  f"{fr:>9} {pc:>6}")
        print("  지어냄 = 규정 원문에도 시스템 프롬프트에도 없는 주장 · 셀당 = 지어냄/셀")
    (DIR / "audit_summary.json").write_text(
        json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


# ────────────────────────────────────────────────────────────── 검증 (V2-1 · V2-2)

def selftest(units: dict) -> None:
    """자의 거짓양성·거짓음성을 잰다. 본실행 전에 반드시 통과해야 한다.

    V2-1 자기대조 — 원문에서 그대로 뽑은 문장을 주장으로 넣으면 전부 「지지」여야 한다
    V2-2 음성대조 — 코퍼스 밖 주장은 전부 「미지지」여야 한다
    """
    import random
    rnd = random.Random(20260809)
    picked = rnd.sample([u for u in units.values() if len(u["text"]) > 300], 20)
    pos = []
    for i, u in enumerate(picked):
        sents = [s.strip() for s in u["text"].split("\n") if 25 < len(s.strip()) < 160]
        if not sents:
            continue
        pos.append({"id": f"pos#{i}", "text": sents[len(sents) // 2], "src": u["src_id"]})

    neg = [
        "축복 신청비는 50만원이다.",
        "축복식 참석 전에 반드시 3개월간 해외 봉사를 해야 한다.",
        "가정회비를 3회 미납하면 자동으로 제명된다.",
        "축복 후보자는 만 35세를 넘으면 신청할 수 없다.",
        "성혼문답은 총 12개 항목으로 구성된다.",
        "축복가정은 매년 국제본부에 영문 보고서를 제출해야 한다.",
        "가정출발의식은 반드시 화요일에 거행한다.",
        "축복자녀는 출생 후 7일 이내에 출생신고를 해야 한다.",
        "재축복 신청은 온라인으로만 접수한다.",
        "금식정성 기간에는 물도 마실 수 없다.",
    ]
    negs = [{"id": f"neg#{i}", "text": t} for i, t in enumerate(neg)]

    async def prep(items):
        index = await get_index(BOT_ID)
        for it in items:
            ret = await index.search(it["text"], top_k=3)
            it["cand"] = [u.src_id for u, _ in ret.ranked_units[:CANDIDATES]]

    import asyncio
    asyncio.run(prep(pos + negs))

    def judge(items, tag):
        pool = sorted({s for it in items for s in it["cand"]})
        payload = {"question": "(자 보정용)", "sources": _src_payload(pool, units),
                   "claims": [{"id": it["id"], "text": it["text"], "cand": it["cand"]}
                              for it in items]}
        res = codex(VERIFY, payload, VERIFY_SCHEMA, label=f"selftest {tag}")
        return {r["id"]: r for r in res.get("results", [])}

    print("\n## V2-1 자기대조 — 원문 문장 20건 (전부 「지지」여야 한다)")
    got = judge(pos, "pos")
    bad, snap_fail = [], 0
    for it in pos:
        r = got.get(it["id"], {})
        c = {"verdict": r.get("verdict", "?"), "quote": r.get("quote", ""),
             "src_id": r.get("src_id", ""), "cand": it["cand"]}
        if c["verdict"] != "미지지":
            _snap(c, units)
            if c.get("snap") is False:
                snap_fail += 1
        if c["verdict"] != "지지":
            bad.append((it["id"], c["verdict"], it["text"][:50], it["src"]))
    print(f"  지지 {len(pos) - len(bad)}/{len(pos)} · 스냅 실패 {snap_fail}건")
    for b in bad:
        print(f"    ✗ {b[0]} {b[1]} [{b[3]}] {b[2]}")
    print(f"  → V2-1 {'통과' if len(bad) <= 3 else '실패 (미지지 3건 초과 — ③ 프롬프트 수정)'}")

    print("\n## V2-2 음성대조 — 코퍼스 밖 주장 10건 (전부 「미지지」여야 한다)")
    got = judge(negs, "neg")
    wrong = []
    for it in negs:
        r = got.get(it["id"], {})
        c = {"verdict": r.get("verdict", "?"), "quote": r.get("quote", ""),
             "src_id": r.get("src_id", ""), "cand": it["cand"]}
        if c["verdict"] == "지지":
            _snap(c, units)
            if c.get("snap") is not False:  # 스냅까지 통과한 거짓양성만 진짜 문제다
                wrong.append((it["id"], it["text"][:40], c.get("src_id")))
    print(f"  미지지/모순 {len(negs) - len(wrong)}/{len(negs)}")
    for w in wrong:
        print(f"    ✗ {w[0]} 지지로 오판 [{w[2]}] {w[1]}")
    print(f"  → V2-2 {'통과' if not wrong else '실패 (거짓양성)'}")


# ────────────────────────────────────────────────────────────── main

async def _load_units() -> tuple[dict, str]:
    index = await get_index(BOT_ID)
    units = {s: {"src_id": u.src_id, "doc": u.doc, "locator": u.locator, "text": u.text}
             for s, u in index.units.items()}
    corpus = "\n\n".join(f"[{u['src_id']}] {u['doc']} {u['locator']}\n{u['text']}"
                         for u in units.values())
    return units, corpus


def main() -> None:
    ap = argparse.ArgumentParser(description="근거 위반 탐지기")
    ap.add_argument("--stage", default="all",
                    choices=["all", "decompose", "candidates", "verify", "adversarial",
                             "prompt_check", "report"])
    ap.add_argument("--selftest", action="store_true", help="V2-1·V2-2 자 보정만 돌린다")
    ap.add_argument("--limit", type=int, default=None, help="셀 N개만 (예행용)")
    a = ap.parse_args()

    import asyncio
    units, corpus = asyncio.run(_load_units())
    log.info("원문 %d건 · %s자", len(units), f"{len(corpus):,}")

    if a.selftest:
        selftest(units)
        return

    cells = load_cells()
    if a.limit:
        cells = dict(list(cells.items())[:a.limit])
    state = load_state()
    log.info("대상 셀 %d개 (기존 상태 %d개)", len(cells), len(state["cells"]))

    if a.stage in ("all", "decompose"):
        stage_decompose(state, cells)
    if a.stage in ("all", "candidates"):
        asyncio.run(stage_candidates(state, units))
    if a.stage in ("all", "verify"):
        stage_verify(state, units)
    if a.stage in ("all", "adversarial"):
        stage_adversarial(state, units, corpus)
    finalize(state)
    if a.stage in ("all", "prompt_check"):
        stage_prompt_check(state)
        finalize(state)
    print_summary(state)
    log.info("→ %s", OUT)


if __name__ == "__main__":
    main()
