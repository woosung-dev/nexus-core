"""편성 오귀속 채점 — 「조건 명시 여부」 기준 (2026-08-16 사용자 확정)

## 왜 이 기준인가

실물 답변이 대부분 조건을 붙이고 있다. 「1세 편성 가정 및 기성축복 가정의 경우…」처럼.
그래서 「한 갈래만 답했나」로 세면 거의 전부 실패가 되고, 개선폭을 못 본다.
사용자가 고른 기준은 **조건을 밝혔는가**다 — 한 갈래만 답해도 조건을 명시했으면 통과,
조건 없이 단정하면 실패.

## 어휘로 판정하지 않는다

「1세」가 답변에 있다고 조건을 명시한 게 아니다. 근거 인용 안에 우연히 들어간 것일 수도
있다. 레포가 어휘 판정으로 3전 3패한 이력이 있어(`next-session-gate-overblock` §3),
판정은 codex 에 맡기고 어휘는 **참고 신호로만** 같이 남긴다.

## 사용법

    python3 exports/branch_2026-08/_grade.py --tag branch43_0816
    python3 exports/branch_2026-08/_grade.py --tag branch43_0816 --summary   # 재채점 없이 집계
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
E2E = DIR.parent / "regression"

VERDICTS = ("조건명시", "단정", "축무관", "유보")

PROMPT = """너는 축복(통일교) 규정 챗봇의 답변을 채점한다. 판정만 하고 설명은 짧게.

배경: 축복 절차는 「축복 편성」에 따라 갈린다.
  - 미혼 1세 편성 가정 / 기성축복 가정 → 3일행사
  - 2세 가정(축복자녀) 편성 → 12일 가정출발의식
사용자가 자기 편성을 밝히지 않았을 때, 봇이 한쪽 절차만 조건 없이 단정하면
사용자는 남의 절차를 자기 것으로 읽는다. 이걸 잡는 것이 목적이다.

아래 넷 중 하나로만 판정한다. **위에서부터 순서대로 본다** — 「축무관」이 먼저다.
질문이 애초에 편성으로 안 갈리면, 봇이 유보했든 답했든 「축무관」이다.

  축무관 : 이 질문은 애초에 편성으로 답이 갈리지 않는다.
           (예: 축도 원문 조회, 용어 설명, 일반 신앙 상담, 비용)
  유보   : 봇이 답을 하지 않았다. (규정집에 없다 / 담당자 문의만 안내)
  조건명시: 편성으로 갈리는 질문인데, 답변이 어느 편성에 해당하는지 밝혔다.
           한 갈래만 설명해도 「1세 편성 가정의 경우」처럼 조건을 달았으면 여기다.
           「당사자 구성에 따라 절차가 구분된다」고 알린 것도 여기다.
  단정   : 편성으로 갈리는 질문인데, 조건 없이 하나의 절차를 답으로 제시했다.

주의:
  - 답변 안에 「1세」라는 말이 있다고 조건명시가 아니다. 그 말이 **이 답이 누구에게
    해당하는지**를 한정하고 있어야 한다. 인용 원문에 우연히 섞인 것은 아니다.
  - 조건을 밝혔는지만 본다. 사실이 맞는지는 채점하지 않는다.

출력은 JSON 한 줄만:
{{"verdict":"<넷 중 하나>","why":"<20자 이내>"}}

[질문]
{q}

[답변]
{a}
"""

# 참고 신호 — 판정에 쓰지 않는다. codex 와 어긋나는 건을 사람이 보라고 남긴다.
_COND_HINT = re.compile(
    r"(1세\s*편성|2세\s*가정\s*편성|축복자녀\s*가정|기성축복\s*가정|"
    r"당사자\s*구성에\s*따라|편성에\s*따라|경우에는|의\s*경우)")


def grade_one(q: str, a: str) -> dict:
    if not (a or "").strip():
        return {"verdict": "유보", "why": "빈 답변", "by": "rule"}
    p = PROMPT.format(q=q, a=a[:3000])
    try:
        r = subprocess.run(["codex", "exec", "-"], input=p, capture_output=True,
                           text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return {"verdict": None, "why": "codex timeout", "by": "error"}
    out = r.stdout or ""
    m = None
    for cand in re.finditer(r"\{[^{}]*\"verdict\"[^{}]*\}", out):
        m = cand
    if not m:
        return {"verdict": None, "why": f"파싱 실패: {out[-120:]}", "by": "error"}
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"verdict": None, "why": "JSON 오류", "by": "error"}
    v = d.get("verdict")
    if v not in VERDICTS:
        return {"verdict": None, "why": f"미지 판정 {v}", "by": "error"}
    return {"verdict": v, "why": (d.get("why") or "")[:40], "by": "codex"}


def summarize(rows: list[dict]) -> None:
    import collections
    by_cid: dict[str, list[str]] = collections.defaultdict(list)
    for r in rows:
        if r.get("verdict"):
            by_cid[r["cid"]].append(r["verdict"])

    c = collections.Counter(r["verdict"] for r in rows if r.get("verdict"))
    tot = sum(c.values())
    print(f"\n── 셀 단위 ({tot}개) ──")
    for k in VERDICTS:
        print(f"  {k:6s} {c[k]:4d}  {c[k] / tot * 100:5.1f}%" if tot else k)
    err = sum(1 for r in rows if not r.get("verdict"))
    if err:
        print(f"  (판정 실패 {err}건)")

    forked = {k: v for k, v in by_cid.items() if any(x in ("조건명시", "단정") for x in v)}
    print(f"\n── 문항 단위 · 편성으로 갈리는 것 {len(forked)}건 ──")
    stable_ok = sum(1 for v in forked.values() if all(x == "조건명시" for x in v))
    stable_bad = sum(1 for v in forked.values() if all(x == "단정" for x in v))
    unstable = len(forked) - stable_ok - stable_bad
    print(f"  3회 모두 조건명시   {stable_ok}")
    print(f"  3회 모두 단정       {stable_bad}   ← 확정 결함")
    print(f"  회차마다 흔들림     {unstable}   ← 비결정성")

    print("\n── 3회 모두 단정 (확정 결함) ──")
    for cid, v in sorted(forked.items()):
        if all(x == "단정" for x in v):
            q = next(r["q"] for r in rows if r["cid"] == cid)
            print(f"  {cid}  {q[:64]}")
    print("\n── 흔들린 문항 ──")
    for cid, v in sorted(forked.items()):
        if len(set(v)) > 1:
            q = next(r["q"] for r in rows if r["cid"] == cid)
            print(f"  {cid}  {'/'.join(v):24s} {q[:52]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--summary", action="store_true", help="재채점 없이 기존 결과만 집계")
    a = ap.parse_args()

    out = DIR / f"_grade_{a.tag}.json"
    if a.summary:
        if not out.exists():
            sys.exit(f"채점 결과 없음: {out}")
        summarize(json.loads(out.read_text(encoding="utf-8"))["rows"])
        return

    src = E2E / f"_e2e_{a.tag}.json"
    if not src.exists():
        sys.exit(f"실행 결과 없음: {src}")
    results = json.loads(src.read_text(encoding="utf-8"))["results"]

    rows: list[dict] = []
    done: set[tuple] = set()
    if out.exists():  # resume
        rows = json.loads(out.read_text(encoding="utf-8"))["rows"]
        done = {(r["cid"], r["rep"]) for r in rows if r.get("verdict")}
        print(f"resume — 기존 {len(done)}건 이어간다")

    todo = [r for r in results if (r["cid"], r["rep"]) not in done]
    for i, r in enumerate(todo, 1):
        g = grade_one(r["q"], r.get("answer") or "")
        rows.append({"cid": r["cid"], "rep": r["rep"], "q": r["q"],
                     "answer": r.get("answer") or "",
                     "hint": bool(_COND_HINT.search(r.get("answer") or "")), **g})
        print(f"[{i}/{len(todo)}] {r['cid']} r{r['rep']} → {g['verdict']} ({g['why']})",
              flush=True)
        out.write_text(json.dumps({"tag": a.tag, "rows": rows}, ensure_ascii=False, indent=1),
                       encoding="utf-8")

    summarize(rows)
    print(f"\n→ {out}")


if __name__ == "__main__":
    main()
