"""게이트가 막은 턴의 **답변과 주입 원문을 나란히** 놓는다. LLM 호출 0회.

## 왜 필요한가

replay 600건에서 답 못 한 373건 중 **199건(53%)이 「①표기 누락」**이다 — 자료는 제대로 받았는데
모델이 본문에 `(근거: …)` 를 안 써서 strict 게이트가 막았다. 다 풀리면 답변률이 37.8% → 71% 다.

**그런데 그 답변들이 정말 쓸 만한지는 아직 아무도 안 봤다.** 쓸 만하면 게이트가 손해를 내고 있는
것이고, 쓸 만하지 않으면 게이트가 옳다. **이걸 확인하기 전에 게이트를 고치면 4전 4패가 된다.**

## 판정 기준 — 읽기 전에 정하고 시작한다

나중에 기준을 바꾸면 결론이 흔들린다(인계문서 「채점 기준을 또 바꾸지 마라」).

| 판정 | 뜻 |
|---|---|
| `쓸만함` | 주입된 원문에 실제로 있는 내용으로, 질문에 답하고 있다 → **게이트가 손해를 냈다** |
| `빗나감` | 근거는 진짜인데 **질문과 다른 것**을 답한다 → 게이트가 막은 게 결과적으로 낫다 |
| `근거밖` | 주입 원문에 없는 내용을 말한다 → **게이트가 옳다** |
| `자체거절` | 모델이 스스로 「확인되지 않습니다」라고 했다 → 게이트와 무관 |

`근거밖` 을 사람이 가리려면 원문이 있어야 한다. 그래서 이 스크립트는 **주입 유닛 원문을 같이 뽑는다.**

## 쓰는 법

    cd backend && .venv/bin/python ../exports/replay_2026-08/_inspect.py --tag replay_0815 --top 20
    cd backend && .venv/bin/python ../exports/replay_2026-08/_inspect.py --tag replay_0815 --top 30 --md
"""

import argparse
import json
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
ROOT = DIR.parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "exports/wiki_2026-08"))
sys.path.insert(0, str(ROOT / "exports/regression"))

from _common import load_sources  # noqa: E402
from _kpi import replay as gate_replay  # noqa: E402

SNIP = 420  # 유닛 원문 발췌 길이. 너무 길면 사람이 안 읽는다


def stage(row: dict, name: str) -> dict:
    for s in ((row.get("trace") or {}).get("stages") or []):
        if s.get("stage") == name:
            return s
    return {}


def injected(row: dict) -> list[str]:
    refs = stage(row, "retrieval").get("unit_refs") or []
    return [r.split(":", 1)[0] for r in refs if not r.startswith("…")]


def collect(tag: str, why_prefix: str) -> list[dict]:
    src = ROOT / f"exports/regression/_e2e_{tag}.json"
    rows = [r for r in json.loads(src.read_text(encoding="utf-8"))["results"] if not r.get("error")]
    kmap = {}
    inp = DIR / "_input.json"
    if inp.exists():
        for it in json.loads(inp.read_text(encoding="utf-8"))["items"]:
            kmap[it["cid"]] = it["k"]
    out = []
    for r in rows:
        d = gate_replay(r)
        if not (d["blocked"] or d["sr"]):
            continue
        # ⚠ `why` 는 **게이트가 막았는지와 무관하게** 계산된다. 봇이 스스로 거절한 턴도
        # 근거를 안 짚었으므로 「①표기 누락」으로 라벨된다 — 199건 중 게이트가 실제로 막은 것은
        # 29건뿐이었다(2026-08-15 실측). 그래서 `--why self` 로 자체 거절만 따로 본다.
        if why_prefix == "self":
            if not (d["sr"] and not d["blocked"]):
                continue
        elif why_prefix == "gate":
            if not d["blocked"]:
                continue
        elif not d["why"].startswith(why_prefix):
            continue
        out.append({"cid": r.get("cid"), "k": kmap.get(r.get("cid"), 1), "q": r["q"],
                    "answer": r.get("answer") or "", "injected": injected(r),
                    "cited": [c for c in (stage(r, "strict").get("cited") or [])
                              if not c.startswith("…")],
                    "why": d["why"]})
    out.sort(key=lambda x: (-x["k"], x["cid"] or ""))
    return out


def render(items: list[dict], units: dict, md: bool) -> str:
    L = []
    if md:
        L += [
            "# 게이트가 막은 답변 — 쓸 만한가?",
            "",
            "> `_inspect.py` 생성 · LLM 호출 0회 · **판정 열은 사람이 채운다**",
            "",
            "## 판정 기준 (읽기 전에 정했다)",
            "",
            "| 판정 | 뜻 |",
            "|---|---|",
            "| `쓸만함` | 주입 원문에 있는 내용으로 질문에 답한다 → **게이트가 손해를 냈다** |",
            "| `빗나감` | 근거는 진짜인데 질문과 다른 것을 답한다 |",
            "| `근거밖` | 주입 원문에 없는 내용을 말한다 → **게이트가 옳다** |",
            "| `자체거절` | 모델이 스스로 「확인되지 않습니다」라고 했다 |",
            "",
            "---",
            "",
        ]
    for i, it in enumerate(items, 1):
        head = f"## {i}. [k={it['k']}] {it['q']}" if md else \
               f"\n{'=' * 78}\n[{i}] k={it['k']} · {it['cid']} · {it['why']}\nQ: {it['q']}"
        L.append(head)
        if md:
            L += ["", f"`{it['cid']}` · 주입 {len(it['injected'])}건 · 게이트가 읽은 표기 "
                      f"{it['cited'] or '없음'}", "", "**답변**", "", "> " +
                  it["answer"].replace("\n", "\n> "), "", "**주입된 원문**", ""]
        else:
            L.append(f"\n--- 답변 ---\n{it['answer']}\n\n--- 주입된 원문 ---")
        for sid in it["injected"]:
            u = units.get(sid)
            if not u:
                continue
            txt = " ".join(u["text"].split())[:SNIP]
            if md:
                L.append(f"- **`{sid}`** {u['locator']}  \n  {txt}…")
            else:
                L.append(f"[{sid}] {u['locator']}\n  {txt}…")
        if md:
            L += ["", "**판정**: `쓸만함` / `빗나감` / `근거밖` / `자체거절` → ____", "", "---", ""]
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--top", type=int, default=20, help="k 상위 N건")
    ap.add_argument("--why", default="self",
                    help="self=봇이 스스로 거절(기본) · gate=게이트가 막음 · ①/② = 사유 접두")
    ap.add_argument("--md", action="store_true", help="INSPECT.md 로 쓴다")
    a = ap.parse_args()

    items = collect(a.tag, a.why)
    print(f"「{a.why}」로 막힌 턴 {len(items)}건 · 상위 {a.top}건을 뽑는다", file=sys.stderr)
    units = load_sources(11)
    text = render(items[:a.top], units, a.md)
    if a.md:
        dst = DIR / "INSPECT.md"
        dst.write_text(text + "\n", encoding="utf-8")
        print(f"→ {dst}", file=sys.stderr)
    else:
        print(text)
