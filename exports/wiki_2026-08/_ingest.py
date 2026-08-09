# 위키 ingest — 소스 1건씩 codex 에게 주고 봇 폴더의 위키를 고치게 한다.
#
# 카파시 llm-wiki 의 Ingest 동작: 소스 1건이 위키 여러 쪽을 갱신한다.
# 에이전트는 `bots/<id>/AGENTS.md` 를 규약으로 읽고(codex 가 cwd 의 AGENTS.md 를 자동으로 읽는다)
# `wiki/index.md` 를 먼저 본 뒤 관련 페이지를 고른다.
#
# 규율
#   · **순차 실행. 병렬 금지.** 두 세션이 같은 엔티티 페이지를 동시에 고치면 덮어쓴다.
#   · **resume 키 = src_id.** 소스 1건이 끝날 때마다 상태를 디스크에 쓴다.
#     (18번째 배치에서 터져 앞선 17배치 ≈50분을 날린 전례가 있다 — _draft.py:207-216)
#   · 실패한 소스는 건너뛰고 계속한다. 재실행이 이어붙인다.
#   · **stdin 이 원문을 통째로 나른다.** 에이전트가 sources/ 를 읽으러 봇 폴더 밖으로 나갈
#     이유를 없앤다 — 쓰기 샌드박스(cwd)를 좁게 유지하는 게 목적이다.
#
# 사용:
#   python3 _ingest.py --bot 11 --only reg-17,reg-33,reg-35,reg-42,reg-43   # 스모크
#   python3 _ingest.py --bot 11                                             # 전량
#   python3 _ingest.py --bot 11 --redo reg-43                               # 특정 건 재실행
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from _common import BOTS, load_sources, sort_key

TIMEOUT = 900
REASONING = "high"

INSTRUCTION = """\
너는 이 폴더(cwd)의 위키를 점진적으로 쌓아 올리는 편집자다.
**작업 규약은 cwd 의 `AGENTS.md` 에 전부 적혀 있다. 먼저 읽고 그대로 따르라.**

<stdin> 으로 소스 1건이 JSON 으로 들어온다:
  src_id  : 출처 앵커에 쓸 식별자 (예: reg-43)
  doc     : 문서 이름
  locator : 사람이 읽는 위치 (예: 제43조(12일 가정출발의식))
  text    : **원문 전문.** 인용은 반드시 여기서 그대로 복사한다.
  today   : 로그에 적을 날짜

절차(AGENTS.md §4):
 1. `wiki/index.md` 를 읽는다.
 2. 이 소스가 건드릴 페이지를 고른다(없으면 `wiki/pages/<슬러그>.md` 를 새로 만든다).
 3. `## 사실` 에 항목을 **더한다**. 기존 항목을 지우지 마라.
 4. 기존 내용과 어긋나면 한쪽을 고르지 말고 `## 모순` 에 양쪽을 적는다.
 5. 문서가 답하지 않는 것은 `## 문서에 없음` 에 질문으로 남긴다.
 6. `## 관련` 교차참조를 **양방향으로** 넣는다.
 7. `wiki/index.md` 와 `wiki/log.md` 를 갱신한다.

절대 규칙:
 - 모든 항목은 `[[src: ...]]` 앵커로 끝난다. 앵커 없는 문장은 쓰지 마라.
 - `>` 인용은 text 에서 그대로 복사한 20~120자 연속 구간이다. 한 글자도 바꾸지 마라.
   숫자와 한글 사이의 공백("12 일", "제 43 조")도 원문 그대로 둔다.
 - 본문 문장에 조문번호를 쓰지 마라(앵커와 `## 근거 좌표` 에만 쓴다).
 - text 에 없는 것을 추측으로 채우지 마라.
 - cwd 바깥을 읽거나 쓰지 마라.

파일을 고치는 것이 산출물이다. **답변으로 요약을 출력하지 마라.**"""


def state_path(bot: int) -> Path:
    return BOTS / str(bot) / "_ingest_state.json"


def load_state(bot: int) -> dict:
    p = state_path(bot)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_state(bot: int, state: dict) -> None:
    """소스 1건이 끝날 때마다 쓴다. 비싼 생성물은 만들어지는 즉시 남긴다."""
    state_path(bot).write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def ingest_one(bot_dir: Path, unit: dict, today: str) -> tuple[bool, str]:
    payload = {"src_id": unit["src_id"], "doc": unit["doc"],
               "locator": unit["locator"], "text": unit["text"], "today": today}
    try:
        p = subprocess.run(
            ["codex", "exec", INSTRUCTION,
             "-s", "workspace-write",      # 기존 스크립트는 read-only. 위키는 써야 한다.
             "-c", f'model_reasoning_effort="{REASONING}"'],
            cwd=str(bot_dir),              # 쓰기 범위를 봇 폴더로 가둔다
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return False, f"timeout {TIMEOUT}s"
    if p.returncode != 0:
        return False, f"exit {p.returncode}: {p.stderr[-300:]}"
    return True, p.stdout.strip()[-200:]


def main(bot: int, only: set[str] | None, redo: set[str], today: str, limit: int | None) -> None:
    bot_dir = BOTS / str(bot)
    if not (bot_dir / "AGENTS.md").exists():
        sys.exit(f"규약 없음: {bot_dir}/AGENTS.md")
    (bot_dir / "wiki" / "pages").mkdir(parents=True, exist_ok=True)

    units = load_sources(bot)
    state = load_state(bot)

    todo = sorted(units, key=sort_key)
    if only:
        unknown = only - set(units)
        if unknown:
            sys.exit(f"없는 src_id: {sorted(unknown)}")
        todo = [s for s in todo if s in only]
    todo = [s for s in todo if s in redo or state.get(s, {}).get("ok") is not True]
    if limit:
        todo = todo[:limit]

    print(f"봇 {bot} · 소스 {len(units)}건 중 대상 {len(todo)}건 "
          f"(완료 {sum(1 for v in state.values() if v.get('ok'))}건)")
    if not todo:
        return

    t0 = time.time()
    for i, sid in enumerate(todo, 1):
        u = units[sid]
        print(f"[{i}/{len(todo)}] {sid} · {u['locator'][:40]} ({len(u['text']):,}자)…",
              end="", flush=True)
        s = time.time()
        ok, msg = ingest_one(bot_dir, u, today)
        state[sid] = {"ok": ok, "locator": u["locator"], "sec": round(time.time() - s, 1),
                      "msg": msg if not ok else ""}
        save_state(bot, state)   # 매 건 저장 — 중간에 터져도 앞선 것을 잃지 않는다
        print(f" {'✓' if ok else '✗'} {state[sid]['sec']}s"
              + ("" if ok else f"  {msg[:160]}"))

    done = sum(1 for s in todo if state[s]["ok"])
    print(f"\n{done}/{len(todo)} 성공 · {(time.time()-t0)/60:.1f}분")
    failed = [s for s in todo if not state[s]["ok"]]
    if failed:
        print(f"실패 {len(failed)}건: {failed} — 재실행하면 이어붙인다")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bot", type=int, default=11)
    ap.add_argument("--only", default="", help="src_id 콤마목록 (예: reg-17,reg-43)")
    ap.add_argument("--redo", default="", help="완료됐어도 다시 돌릴 src_id")
    ap.add_argument("--today", default="2026-08-07", help="log.md 에 적을 날짜")
    ap.add_argument("--limit", type=int, default=0, help="앞에서 N건만")
    a = ap.parse_args()
    main(a.bot,
         {x.strip() for x in a.only.split(",") if x.strip()} or None,
         {x.strip() for x in a.redo.split(",") if x.strip()},
         a.today, a.limit or None)
