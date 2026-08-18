# RAG 3·4회차 ↔ 위키 1·2회차 — **회차 수와 측정 시점을 맞춘** 2회 대 2회 비교.
#
# 왜 이렇게 자르나
#   RAG 4회는 8/05(1·2회차)와 8/11(3·4회차)에 나뉘어 돌았다. 6일 간격이다.
#   L1 신호·정확도 모두 날짜로 갈리지 않음을 확인했지만(4팔 평균 차 0.9pp, 부호 엇갈림),
#   호스팅 모델이 그 사이 갱신됐는지는 우리가 확인할 수 없다.
#   그래서 **같은 주에 돌린 것끼리만** 비교하는 표를 따로 낸다.
#     RAG  = 3·4회차 (2026-08-11)
#     위키 = 1·2회차 (2026-08-12)
#   1·2회차(8/05)는 버리지 않고 「참고」로 남긴다 — 회차 흔들림의 크기를 보여주는 값이다.
import collections
import json
import pathlib
import re
import statistics as st

ROOT = pathlib.Path("/Users/woosung/project/agy-project/nexus-core")
P = ROOT / "exports" / "regression"
OUT = ROOT / "exports" / "golden45_2026-08-11" / "_compare2.json"
NAME = {"sva": "서비스방향 A", "svb": "서비스방향 B",
        "j03": "03_여정동반자", "e6": "E_부모동행v6"}
LEAK = re.compile(r"\[\[\s*src\s*:|\[(?:reg|glo|gong)-\d+\]")


def block(arm, suf, reps):
    """지정한 회차만 뽑아 집계한다. reps=None 이면 전부."""
    ansd = json.loads((P / f"_answers_{arm}{suf}.json").read_text(encoding="utf-8"))
    res = [x for x in ansd["results"] if reps is None or x.get("rep", 1) in reps]
    if not res:
        return None
    amap = collections.defaultdict(dict)
    for x in res:
        amap[x.get("rep", 1)][str(x.get("cid") or x.get("gid"))] = x["answer"]
    rows = [r for r in json.loads((P / f"_l3_{arm}{suf}.json").read_text(encoding="utf-8"))["rows"]
            if reps is None or r["rep"] in reps]
    n = len(rows)
    c = collections.Counter(r["verdict"] for r in rows)
    crit = [r for r in rows if r["severity"] == "Critical"]
    # 마커 노출로 Critical 이 된 건은 따로 센다 — 위키 팔에만 있는 결함이라
    # 이걸 빼야 「지식 실패」끼리 비교된다.
    keep = [r for r in crit
            if not (r["type"] == "누출" or LEAK.search(amap[r["rep"]].get(r["qkey"], "")))]
    q = json.loads((P / "questions.json").read_text(encoding="utf-8"))["items"]
    cid = {i["cid"] for i in q if i.get("cid")}
    acc = lambda rs: round(100 * sum(1 for r in rs if r["verdict"] == "정확") / max(len(rs), 1), 1)
    ms = sorted([(x.get("l1") or {}).get("gen_ms") for x in res if (x.get("l1") or {}).get("gen_ms")])
    return {
        "n": n, "reps": sorted({r["rep"] for r in rows}),
        "acc": round(100 * c["정확"] / n, 1),
        "safe": round(100 * (c["정확"] + c["안전응대"]) / n, 1),
        "hal": round(100 * sum(1 for r in rows if r["hallucination"]) / n, 1),
        "crit": len(crit), "critkeep": len(keep),
        "acc45": acc([r for r in rows if r["qkey"] not in cid]),
        "accC": acc([r for r in rows if r["qkey"] in cid]),
        "v": {k: c.get(k, 0) for k in ("정확", "안전응대", "부분", "오류")},
        "leak": sum(1 for x in res if LEAK.search(x["answer"])),
        "art": sum(1 for x in res if re.search(r"제\s*\d+\s*조", x["answer"])),
        "empty": sum(1 for x in res if (x.get("l1") or {}).get("grounding_chunks") == 0),
        "cited": sum(1 for x in res if x.get("n_citations", 0) > 0),
        "med": round(st.median(ms) / 1000, 1) if ms else None,
        "per_rep": {r: round(100 * sum(1 for x in rows if x["rep"] == r and x["verdict"] == "정확")
                             / max(sum(1 for x in rows if x["rep"] == r), 1), 1)
                    for r in sorted({x["rep"] for x in rows})},
    }


def main():
    out = {"arms": {}}
    for a, nm in NAME.items():
        out["arms"][a] = {
            "name": nm,
            "rag_old": block(a, "_45", {1, 2}),    # 8/05 — 참고
            "rag_new": block(a, "_45", {3, 4}),    # 8/11 — 비교 대상
            "rag_all": block(a, "_45", None),      # 4회 전체
            "wiki": block(a, "_lex", None),        # 8/12
        }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print("― 같은 주에 돌린 것끼리: RAG 3·4회차(8/11) ↔ 위키(8/12) ―")
    hdr = f"{'팔':<13}{'구성':<16}{'회차':>6}{'호출':>5}{'정확':>7}{'안전포함':>8}{'할루시':>7}{'Crit':>5}{'마커제외':>7}{'45문항':>7}{'함정10':>7}"
    print(hdr)
    for a, nm in NAME.items():
        d = out["arms"][a]
        for key, label in (("rag_new", "RAG 3·4회"), ("wiki", "위키 1·2회"), ("rag_old", "(참고) RAG 1·2회")):
            b = d[key]
            if not b:
                continue
            print(f"{nm:<13}{label:<16}{str(b['reps']):>6}{b['n']:>5}{b['acc']:>6.1f}%{b['safe']:>7.1f}%"
                  f"{b['hal']:>6.1f}%{b['crit']:>5}{b['critkeep']:>7}{b['acc45']:>6.1f}%{b['accC']:>6.1f}%")
        print()
    print(f"저장 → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
