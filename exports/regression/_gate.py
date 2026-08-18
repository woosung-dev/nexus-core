"""strict 게이트를 trace 로 오프라인 재현한다. LLM 호출 0회.

## 왜 재현이 성립하나

strict 게이트는 **생성 뒤 판정**이다. legacy 와 strict 는 같은 생성 결과에서 갈린다.
그래서 legacy 로 한 번만 돌리고 여기서 판정만 다시 매긴다. 호출이 절반이고,
같은 답변에서 갈리니 **게이트 효과만 순수하게** 남는다.

## ⚠ 두 갈래를 모두 봐야 한다

`has_grounded_citation` 은 답변의 근거 표기를 두 형식으로 읽는다.

    [[src: reg-53]]      기계 id     → 화면에 나가기 전 `strip_source_markers` 가 지운다
    (근거: 제53조)        조문 형식    → 정보라서 남긴다

**저장된 답변은 표기 제거 후**라 기계 id 가 이미 없다. 답변만 보고 재현하면 첫 갈래가
통째로 빠져 과잉 차단으로 편향된다 — PR #59 가 고친 바로 그 함정이다
(src_id 만 보면 과잉 거절 22.5%, 조문을 함께 보면 5.0%).

그래서 **제거 전 id 는 trace 의 `strict.cited` 에서** 가져오고, 조문 형식은 저장된
답변에서 읽는다. 둘의 합집합이 실제 게이트와 같다.
"""

import argparse
import json
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR.parent.parent / "backend"))

from app.services.strict_mode import _locator_keys  # noqa: E402
from app.services.unanswered import is_self_refusal  # noqa: E402


def stage(trace: dict, name: str) -> dict:
    for s in (trace or {}).get("stages", []):
        if s.get("stage") == name:
            return s
    return {}


def split_ref(ref: str) -> tuple[str, str]:
    i = ref.find(":")
    return (ref, "") if i < 0 else (ref[:i], ref[i + 1:])


def replay(row: dict) -> dict:
    """이 턴이 strict 였다면 어떻게 됐을지."""
    trace = row.get("trace") or {}
    mode = (trace.get("config") or {}).get("retrieval_mode") or "lexical"
    ret, strict = stage(trace, "retrieval"), stage(trace, "strict")
    ops = stage(trace, "ops_facts")
    answer = row.get("answer") or ""

    # 위기 턴은 게이트를 안 탄다(`chat_service._strict_blocks` 의 `crisis_active`).
    # 여기서 재현 안 하면 게이트 보고서가 위기 문항을 「차단」으로 세어 유보율이 부풀려진다.
    # ⚠ `kinds` 는 **없을 수 있는 키**다 — `TurnTrace.stage` 가 None 값을 버려서
    # 사실 0건인 턴에는 아예 안 실린다. `.get(...) or []` 로 받아야 한다.
    crisis = "crisis" in (ops.get("kinds") or [])

    refs = [split_ref(r) for r in (ret.get("unit_refs") or []) if not r.startswith("…")]
    inj_ids = {i for i, _ in refs}
    inj_loc: set = set()
    for _, loc in refs:
        inj_loc |= _locator_keys(loc)

    cited = [c for c in (strict.get("cited") or []) if not c.startswith("…")]
    ghost = sorted(set(cited) - inj_ids)

    # 런타임은 **폴백했으면 어휘 경로가 아니라고 본다** (`chat_service._strict_blocks`:
    # `fell_back` 이면 `has_direct_citation` 자로 돌아간다). 여기서 `config.retrieval_mode`
    # 만 보면 두 자가 갈라진다. 지금 데이터에서는 `폴백 ∧ direct_citation=True` 가 0건이라
    # 무증상이지만, 안 맞춰 두면 crisis 예외를 넣는 순간 「위기라서 안 막힌 것」과
    # 「재현 오류로 안 막힌 것」이 섞여 구분이 안 된다.
    reasons = ret.get("reasons") or []
    fell_back = bool({"lexical_empty", "corpus_unavailable"} & set(reasons))

    if mode != "lexical" or fell_back:
        # file_search·both 는 「근사 백필이 아닌 인용이 하나라도 있나」만 본다.
        grounded = bool(ret.get("direct_citation"))
        blocked = not grounded
    else:
        # 런타임은 `evidence_ok` = ①주입 근거를 짚었나 **∧** ②지어낸 게 없나 다.
        # ① 만 재현하면 「맞는 근거 하나에 가짜 셋을 얹은 답변」을 통과로 세어
        # 유보율을 13.7pp 낮게 보고한다(110셀 실측 54.5% vs 실제 68.2%).
        # 이 파일은 게이트가 ①∪② 로 바뀌기 전(`97ab98c`)에 쓰였고 그때 안 따라왔다.
        grounded = bool(set(cited) & inj_ids) or bool(_locator_keys(answer) & inj_loc)
        fabricated = bool(ghost) or bool(_locator_keys(answer) - inj_loc)
        evidence_ok = bool(refs) and grounded and not fabricated
        blocked = not evidence_ok and not is_self_refusal(answer)
        if not refs:
            blocked = True  # 주입 0건이면 `has_grounded_citation` 이 False 다

    if crisis:
        blocked = False

    return {
        "gid": row.get("gid"), "cid": row.get("cid"), "rep": row["rep"], "mode": mode,
        "risk": row.get("risk"), "crisis": crisis,
        "blocked": blocked, "grounded": grounded,
        "self_refusal": is_self_refusal(answer),
        "injected": len(refs), "cited": len(cited), "ghost": ghost,
        "answer_len": len(answer),
        "reasons": ret.get("reasons") or [],
    }


def main(tag: str) -> None:
    src = DIR / f"_e2e_{tag}.json"
    data = json.loads(src.read_text(encoding="utf-8"))
    rows = [r for r in data["results"] if not r.get("error")]
    out = [replay(r) for r in rows]

    n = len(out)
    blocked = [r for r in out if r["blocked"]]
    refusal = [r for r in out if r["self_refusal"]]
    ghosty = [r for r in out if r["ghost"]]
    fallback = [r for r in out if "lexical_empty" in r["reasons"] or "corpus_unavailable" in r["reasons"]]
    crises = [r for r in out if r["crisis"]]

    print(f"═══ {tag} · {n}건 (오류 {len(data['results']) - n}건 제외) ═══")
    if crises:
        cids = sorted({r["cid"] or r["gid"] for r in crises})
        print(f"  위기 턴(게이트 면제)              {len(crises):>4}건  {cids}")
    print(f"  legacy 에서 봇이 스스로 거절   {len(refusal):>4}건  {len(refusal)/n*100:5.1f}%")
    print(f"  strict 였다면 차단             {len(blocked):>4}건  {len(blocked)/n*100:5.1f}%")
    print(f"    ├ 그중 이미 자기거절         {sum(1 for r in blocked if r['self_refusal']):>4}건")
    print(f"    └ 새로 막히는 답변           {sum(1 for r in blocked if not r['self_refusal']):>4}건  ← 유보율 증가분")
    print(f"  출처 불명 표기가 있는 턴        {len(ghosty):>4}건  {len(ghosty)/n*100:5.1f}%")
    print(f"  검색 폴백(lexical→file_search)  {len(fallback):>4}건")

    print("\n  위험도별 차단:")
    for risk in ("상", "중", "하", "없음", None):
        sub = [r for r in out if r["risk"] == risk]
        if sub:
            b = sum(1 for r in sub if r["blocked"])
            print(f"    {str(risk):5} {len(sub):>3}건 중 {b:>3}건 차단 ({b/len(sub)*100:5.1f}%)")

    ghost_ids: dict = {}
    for r in ghosty:
        for g in r["ghost"]:
            ghost_ids[g] = ghost_ids.get(g, 0) + 1
    if ghost_ids:
        print("\n  자주 지어내는 근거 표기 상위:")
        for k, v in sorted(ghost_ids.items(), key=lambda x: -x[1])[:10]:
            print(f"    {k:10} {v}회")

    dst = DIR / f"_gate_{tag}.json"
    dst.write_text(json.dumps({"tag": tag, "n": n, "rows": out}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\n→ {dst}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    main(ap.parse_args().tag)
