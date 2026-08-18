"""두 replay 산출물을 **같은 질문에 대해** 나란히 놓는다. LLM 호출 0회.

## 무엇을 재나

「검색 적중률」은 대리 지표다. 이 세션에서 대리 지표로 네 번 틀렸다.
**진짜 지표는 답변률** — 사용자가 답을 받았느냐다. 그래서 여기서는 그것만 잰다.

    답 받음   = 게이트가 안 막고, 봇도 스스로 거절하지 않았다
    게이트 차단 = strict 가 막았다(`_kpi.replay().blocked`)
    자체 거절  = 봇이 「확인되지 않습니다」라고 했다(`is_self_refusal`)

교집합 질문만 비교한다 — 한쪽에만 있는 문항이 섞이면 차이가 문항 구성 탓인지 설정 탓인지 못 가른다.

## 쓰는 법

    cd backend && .venv/bin/python ../exports/replay_2026-08/_compare.py --a replay_0815 --b dense150
"""

import argparse
import json
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
ROOT = DIR.parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "exports/regression"))

from _kpi import replay as gate_replay  # noqa: E402


def load(tag: str) -> dict:
    src = ROOT / f"exports/regression/_e2e_{tag}.json"
    if not src.exists():
        sys.exit(f"없다: {src}")
    rows = json.loads(src.read_text(encoding="utf-8"))["results"]
    return {r["cid"]: r for r in rows if r.get("cid") and not r.get("error")}


def state(row: dict) -> str:
    d = gate_replay(row)
    if d["blocked"]:
        return "게이트 차단"
    if d["sr"]:
        return "자체 거절"
    return "답 받음"


def units(row: dict) -> list[str]:
    for s in ((row.get("trace") or {}).get("stages") or []):
        if s.get("stage") == "retrieval":
            return [x.split(":", 1)[0] for x in (s.get("unit_refs") or [])
                    if not x.startswith("…")]
    return []


def main(ta: str, tb: str, show: int) -> None:
    A, B = load(ta), load(tb)
    both = sorted(set(A) & set(B))
    if not both:
        sys.exit("교집합 문항이 없다")
    kmap = {}
    inp = DIR / "_input.json"
    if inp.exists():
        for it in json.loads(inp.read_text(encoding="utf-8"))["items"]:
            kmap[it["cid"]] = it["k"]

    from collections import Counter
    ca, cb = Counter(), Counter()
    flips = []
    for cid in both:
        sa, sb = state(A[cid]), state(B[cid])
        ca[sa] += 1
        cb[sb] += 1
        if sa != sb:
            flips.append((kmap.get(cid, 1), cid, A[cid]["q"], sa, sb))
    flips.sort(key=lambda x: -x[0])

    n = len(both)
    pc = lambda c: f"{c / n * 100:5.1f}% ({c:>3})"  # noqa: E731
    print(f"\n═══ {ta} vs {tb} · 교집합 {n}문항 ═══\n")
    print(f"{'':<12}{ta:>18}{tb:>18}")
    for k in ("답 받음", "게이트 차단", "자체 거절"):
        arrow = ""
        if cb[k] != ca[k]:
            arrow = f"   {'+' if cb[k] > ca[k] else ''}{cb[k] - ca[k]}"
        print(f"{k:<12}{pc(ca[k]):>18}{pc(cb[k]):>18}{arrow}")

    gain = cb["답 받음"] - ca["답 받음"]
    print(f"\n답변률 {ca['답 받음'] / n * 100:.1f}% → {cb['답 받음'] / n * 100:.1f}% "
          f"({'+' if gain >= 0 else ''}{gain / n * 100:.1f}%p)")

    up = [f for f in flips if f[4] == "답 받음"]
    down = [f for f in flips if f[3] == "답 받음"]
    print(f"\n뒤집힌 문항 {len(flips)}건 — 좋아짐 {len(up)} · 나빠짐 {len(down)}")
    for label, group in (("좋아짐", up), ("나빠짐", down)):
        if not group:
            continue
        print(f"\n  [{label}]")
        for k, cid, q, sa, sb in group[:show]:
            print(f"    k={k:>2} {cid} {q[:44]}")
            print(f"         {sa} → {sb}")
            print(f"         주입 {', '.join(units(A[cid])[:5])}")
            print(f"           → {', '.join(units(B[cid])[:5])}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="기준 태그")
    ap.add_argument("--b", required=True, help="비교 태그")
    ap.add_argument("--show", type=int, default=8, help="뒤집힌 문항 몇 건까지 보일까")
    a = ap.parse_args()
    main(a.a, a.b, a.show)
