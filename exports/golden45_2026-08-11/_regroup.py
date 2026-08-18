# 채점 기준의 출처에 따라 문항을 갈라 집계한다.
#
# 왜: 55문항 평균은 **근거가 다른 둘을 섞은 값**이다.
#   45문항  — 관리자 회신(2026-08-06)이 정답. 외부 권위가 있다.
#   함정 10 — 우리가 만든 기준. 그중 일부는 관리자 판단이 필요한데 아직 못 받았다.
#
# 함정 10 을 다시 셋으로 가른다 (2026-08-12 사용자 승인).
#   ① 문서로 검증됨  C01 교제축복(코퍼스 0회) · C02 5대성물(0회, 4대성물 7회) · C03 천애축승(0회)
#                    → 「그 용어가 존재하는가」는 전수 검색으로 확인된 **문서 사실**이다.
#   ② 행동 규칙      C07 위기대응 · C09 프롬프트 유출 · C10 범위밖
#                    → 정답 지식이 필요 없다. 챗봇 운영 상식이다.
#   ③ 교단 판단 필요  C04 영육계축복 · C05 천일국매칭 폐지 · C06 가해자/피해자 · C08 동성결혼
#                    → **우리가 정했고 근거가 없다.** 특히 C06 은 관리자 #37·#40 답변
#                      (「구분을 한다」)과 정면으로 어긋난다 → 점수에서 뺀다.
#
# 헤드라인은 **45문항 정확도**다. 함정은 별도 지표로만 쓴다.
import collections
import json
import pathlib
import re
import statistics as st

ROOT = pathlib.Path("/Users/woosung/project/agy-project/nexus-core")
P = ROOT / "exports" / "regression"
OUT = ROOT / "exports" / "golden45_2026-08-11" / "_regroup.json"
NAME = {"sva": "서비스방향 A", "svb": "서비스방향 B",
        "j03": "03_여정동반자", "e6": "E_부모동행v6"}
LEAK = re.compile(r"\[\[\s*src\s*:|\[(?:reg|glo|gong)-\d+\]")

VERIFIED = {"C01", "C02", "C03", "C07", "C09", "C10"}   # 근거 확실
PENDING = {"C04", "C05", "C08"}                          # 관리자 확인 대기
EXCLUDED = {"C06"}                                       # 관리자 답변과 충돌 — 유보


def agg(rows, amap):
    n = len(rows)
    if not n:
        return None
    c = collections.Counter(r["verdict"] for r in rows)
    crit = [r for r in rows if r["severity"] == "Critical"]
    keep = [r for r in crit
            if not (r["type"] == "누출" or LEAK.search(amap.get((r["rep"], r["qkey"]), "")))]
    return {"n": n, "acc": round(100 * c["정확"] / n, 1),
            "safe": round(100 * (c["정확"] + c["안전응대"]) / n, 1),
            "hal": round(100 * sum(1 for r in rows if r["hallucination"]) / n, 1),
            "crit": len(crit), "critkeep": len(keep),
            "v": {k: c.get(k, 0) for k in ("정확", "안전응대", "부분", "오류")}}


def block(arm, suf, reps):
    ansd = json.loads((P / f"_answers_{arm}{suf}.json").read_text(encoding="utf-8"))
    res = [x for x in ansd["results"] if reps is None or x.get("rep", 1) in reps]
    amap = {(x.get("rep", 1), str(x.get("cid") or x.get("gid"))): x["answer"] for x in res}
    rows = [r for r in json.loads((P / f"_l3_{arm}{suf}.json").read_text(encoding="utf-8"))["rows"]
            if reps is None or r["rep"] in reps]
    q = json.loads((P / "questions.json").read_text(encoding="utf-8"))["items"]
    cid = {i["cid"] for i in q if i.get("cid")}
    ms = sorted([(x.get("l1") or {}).get("gen_ms") for x in res if (x.get("l1") or {}).get("gen_ms")])
    return {
        "q45": agg([r for r in rows if r["qkey"] not in cid], amap),          # ← 헤드라인
        "trap_ok": agg([r for r in rows if r["qkey"] in VERIFIED], amap),     # 근거 확실 6
        "trap_wait": agg([r for r in rows if r["qkey"] in PENDING], amap),    # 확인 대기 3
        "trap_c06": agg([r for r in rows if r["qkey"] in EXCLUDED], amap),    # 유보 1
        "all55": agg(rows, amap),                                             # 참고 — 옛 헤드라인
        "leak": sum(1 for x in res if LEAK.search(x["answer"])),
        "art": sum(1 for x in res if re.search(r"제\s*\d+\s*조", x["answer"])),
        "empty": sum(1 for x in res if (x.get("l1") or {}).get("grounding_chunks") == 0),
        "cited": sum(1 for x in res if x.get("n_citations", 0) > 0),
        "med": round(st.median(ms) / 1000, 1) if ms else None,
        "plen": ansd["bot"]["prompt_len"],
    }


def main():
    out = {"arms": {}, "groups": {"verified": sorted(VERIFIED),
                                  "pending": sorted(PENDING), "excluded": sorted(EXCLUDED)}}
    for a, nm in NAME.items():
        out["arms"][a] = {"name": nm,
                          "rag": block(a, "_45", {3, 4}),     # 08-11
                          "wiki": block(a, "_lex", None),     # 08-12 (1·2회)
                          "rag_old": block(a, "_45", {1, 2})}  # 08-05 참고
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print("헤드라인 = 45문항 정확도 (관리자 회신 기반) · 양쪽 2회 · 90호출")
    print(f"{'팔':<13}{'모드':<6}{'45문항':>8}{'안전포함':>8}{'할루시':>7}{'Crit':>5}{'마커제외':>7}"
          f"{'|함정6':>8}{'함정3':>7}{'C06':>7}{'|55전체':>8}")
    for a, nm in NAME.items():
        d = out["arms"][a]
        for k, lab in (("rag", "RAG"), ("wiki", "위키")):
            b = d[k]
            q, t1, t2, c6, al = b["q45"], b["trap_ok"], b["trap_wait"], b["trap_c06"], b["all55"]
            print(f"{nm:<13}{lab:<6}{q['acc']:>7.1f}%{q['safe']:>7.1f}%{q['hal']:>6.1f}%"
                  f"{q['crit']:>5}{q['critkeep']:>7}{t1['acc']:>7.1f}%{t2['acc']:>6.1f}%"
                  f"{c6['acc']:>6.1f}%{al['acc']:>7.1f}%")
        print()
    print(f"저장 → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
