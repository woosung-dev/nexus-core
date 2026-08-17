"""§1 헤드라인 KPI 를 `_e2e_<tag>.json` 에서 계산한다. LLM 호출 0회.

## 왜 `_gate.py` 와 따로 있나

`_gate.py` 는 「strict 였다면 차단됐을까」만 센다. 그건 **게이트의 동작**이지 **제품의 지표**가
아니다. 인계 문서 §1 이 정한 지표는 문서상태(일치·부분일치·불일치·문서에없음)와 교차해야
나온다 — 「답할 수 있는 문항인데 막혔나(과잉 거절)」가 그렇다.

## 문서상태는 어디서 오나 — 여기서 한 번 헤맸다

`exports/golden45_2026-08-11/_golden_vs_docs.json` 의 `rows[].verdict` 다.
**키는 `questions.json` 의 `no`(1~45)** 이고 `gid`·`cid` 가 **아니다.**
C01~C10 은 `no` 가 없어서 `bucket == 'C'` → `함정` 으로 넣는다.

## 게이트 재현은 ①∪② 여야 한다

런타임 `evidence_ok` = ①주입 근거를 짚었나 **∧** ②지어낸 게 없나.
① 만 재현하면 유보율을 13.7pp 낮게 보고한다(54.5% vs 실제 68.2%).

검산: `s1_lex_0813` 의 전체 유보가 **68.2%(75/110)** 로 나와야 인계 문서 §0-5 와 맞는다.

    cd backend && .venv/bin/python ../exports/regression/_kpi.py --tag s1_lex_0813
    cd backend && .venv/bin/python ../exports/regression/_kpi.py --tag s1_lex_0813 --tag cite_0814
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR.parent.parent / "backend"))

from app.services.strict_mode import _locator_keys  # noqa: E402
from app.services.unanswered import is_self_refusal  # noqa: E402

ANSWERABLE = ("일치", "부분일치")


def _verdicts() -> dict[str, str]:
    """질문 원문 → 문서상태."""
    items = json.loads((DIR / "questions.json").read_text(encoding="utf-8"))["items"]
    gv = json.loads(
        (DIR.parent / "golden45_2026-08-11" / "_golden_vs_docs.json").read_text(encoding="utf-8")
    )["rows"]
    by_no = {str(r["key"]): r["verdict"] for r in gv}
    out = {}
    for q in items:
        v = by_no.get(str(q.get("no"))) if q.get("no") is not None else None
        if v is None and q.get("bucket") == "C":
            v = "함정"
        out[q["q"]] = v
    return out


def _stage(trace: dict, name: str) -> dict:
    for s in (trace or {}).get("stages", []):
        if s.get("stage") == name:
            return s
    return {}


def _split(ref: str) -> tuple[str, str]:
    i = ref.find(":")
    return (ref, "") if i < 0 else (ref[:i], ref[i + 1:])


def replay(row: dict) -> dict:
    """이 턴이 strict 였다면 어떻게 됐을지 + 왜 그랬는지."""
    trace = row.get("trace") or {}
    mode = (trace.get("config") or {}).get("retrieval_mode") or "lexical"
    ret, strict = _stage(trace, "retrieval"), _stage(trace, "strict")
    answer = row.get("answer") or ""

    refs = [_split(r) for r in (ret.get("unit_refs") or []) if not r.startswith("…")]
    inj_ids = {i for i, _ in refs}
    inj_loc: set = set()
    for _, loc in refs:
        inj_loc |= _locator_keys(loc)
    cited = [c for c in (strict.get("cited") or []) if not c.startswith("…")]
    ghost = set(cited) - inj_ids
    fake_loc = _locator_keys(answer) - inj_loc
    fell_back = bool({"lexical_empty", "corpus_unavailable"} & set(ret.get("reasons") or []))

    grounded = bool(set(cited) & inj_ids) or bool(_locator_keys(answer) & inj_loc)
    if mode != "lexical" or fell_back:
        blocked = not bool(ret.get("direct_citation"))
    else:
        blocked = not (bool(refs) and grounded and not (ghost or fake_loc))
        blocked = blocked and not is_self_refusal(answer)
        if not refs:
            blocked = True

    # 위기 턴은 게이트를 안 탄다(`chat_service._strict_blocks` 의 crisis_active)
    if "crisis" in (_stage(trace, "ops_facts").get("kinds") or []):
        blocked = False

    if not refs and not fell_back:
        why = "주입 0건"
    elif fell_back:
        why = "검색 폴백"
    elif not grounded and (ghost or fake_loc):
        why = "표기 없음 + 지어냄"
    elif not grounded:
        why = "①주입 근거를 안 짚음(표기 누락)"
    elif ghost or fake_loc:
        why = "②주입 목록 밖 근거를 댐(지어냄)"
    else:
        why = "통과"

    return dict(blocked=blocked, sr=is_self_refusal(answer),
                fabricated=bool(ghost or fake_loc), why=why)


def report(tag: str, verdicts: dict[str, str]) -> None:
    src = DIR / f"_e2e_{tag}.json"
    if not src.exists():
        sys.exit(f"없다: {src}")
    rows = [r for r in json.loads(src.read_text(encoding="utf-8"))["results"] if not r.get("error")]
    out = []
    for row in rows:
        d = replay(row)
        d["v"] = verdicts.get(row["q"])
        d["q"] = row["q"]
        out.append(d)

    held = lambda r: r["blocked"] or r["sr"]  # noqa: E731  사용자가 답을 못 받았나
    pc = lambda a, b: f"{a / b * 100:5.1f}% ({a}/{b})" if b else "n/a"  # noqa: E731

    nodoc = [r for r in out if r["v"] == "문서에없음"]
    ansb = [r for r in out if r["v"] in ANSWERABLE]
    # ③ 은 **「지어냄」을 뺀다**(2026-08-15 사용자 결정). 모델이 주입 밖 근거를 대서 막힌 것은
    # 게이트가 **옳게** 막은 것이라 「과잉」이 아니다. 그건 ④ 로 따로 센다 — 둘은 고치는 곳이
    # 다르다(③=게이트/프롬프트, ④=모델/생성). 섞으면 ③ 이 구조적으로 도달 불가능해진다.
    over = [r for r in ansb if r["blocked"] and not r["sr"] and not r["fabricated"]]
    blocked_fab = [r for r in ansb if r["blocked"] and not r["sr"] and r["fabricated"]]
    harm = [r for r in out if r["fabricated"] and not held(r)]
    fab = [r for r in out if r["fabricated"]]

    print(f"\n═══ {tag} · {len(out)}셀 ═══")
    print(f"  ① 유해 확답 (지어낸 근거가 그대로 나감)  목표 0건   → {len(harm)}건")
    print(f"  ② 유보율 · 문서없음 문항               목표 ≥95%  → {pc(sum(1 for r in nodoc if held(r)), len(nodoc))}")
    print(f"  ③ 과잉 거절 · 답 있는데 표기 누락으로 막힘 목표 ≤5%   → {pc(len(over), len(ansb))}")
    print(f"  ④ 지어냄률 · 주입 밖 근거를 댄 턴        목표 미정   → {pc(len(fab), len(out))}")
    print(f"     ↳ 그중 게이트가 막아 준 것(③ 에서 뺀 몫)        → {len(blocked_fab)}건")
    print(f"     (참고) 전체 유보율                            → {pc(sum(1 for r in out if held(r)), len(out))}")

    print("\n  문서상태별 유보율")
    for s in ("일치", "부분일치", "불일치", "문서에없음", "함정"):
        sub = [r for r in out if r["v"] == s]
        if sub:
            print(f"    {s:6} {len(sub):>3}셀  {pc(sum(1 for r in sub if held(r)), len(sub))}")

    if over:
        print("\n  과잉 거절 원인 — 여기가 고칠 곳이다")
        for why, n in Counter(r["why"] for r in over).most_common():
            print(f"    {n:>3}건  {why}")
        print("    ※ 「지어냄」은 게이트가 **옳게** 막은 것이다. 프롬프트/모델 쪽 문제고 자를 풀 일이 아니다.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", action="append", required=True, help="여러 번 주면 나란히 잰다")
    v = _verdicts()
    for t in ap.parse_args().tag:
        report(t, v)
