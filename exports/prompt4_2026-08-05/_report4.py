# 4팔 비교 리포트 — REPORT.md 생성. API 호출 0, 읽기 전용.
#
# 지표 축은 7/29(03_여정동반자·E_부모동행v6) · 8/03(서비스방향 A·B) 리포트와 맞춘다.
# 그래야 세트가 45개로 바뀌어도 세로 비교의 실마리가 남는다.
import json
from pathlib import Path

DIR = Path(__file__).parent
REG = Path("/Users/woosung/project/agy-project/nexus-core/exports/regression")
OUT = DIR / "REPORT.md"

ARMS = [("j03_45", "03_여정동반자"), ("e6_45", "E_부모동행v6"),
        ("svb_45", "서비스방향 B"), ("sva_45", "서비스방향 A")]


def jload(p):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def pct(n, d):
    return f"{100.0*n/d:.0f}%" if d else "—"


def collect(tag):
    a = jload(REG / f"_answers_{tag}.json")
    if a is None:
        return None
    ok = [r for r in a["results"] if not r["answer"].startswith("[ERROR]")]
    meas = [r for r in ok if r.get("l1")]
    d = {
        "answers": a, "n": len(a["results"]), "err": len(a["results"]) - len(ok),
        "cited": sum(1 for r in meas if r.get("n_citations", 0) > 0),
        "empty": sum(1 for r in meas if (r["l1"] or {}).get("grounding_chunks") == 0),
        "measured": len(meas),
        "len": sum(r["l1"]["answer_len"] for r in meas) / max(len(meas), 1),
        "ms": sum(r["l1"]["gen_ms"] for r in meas) / max(len(meas), 1),
        "l2": jload(REG / f"_l2_{tag}.json"),
        "l3": jload(REG / f"_l3_{tag}.json"),
        "anchor": jload(DIR / f"_anchor_{tag}.json"),
    }
    if d["anchor"]:
        rows = d["anchor"]["rows"]
        d["arows"] = rows
        d["hit"] = sum(len(r["anchors_hit"] or []) for r in rows)
        d["tot"] = sum(r["n_anchors"] for r in rows)
        d["fit"] = sum(1 for r in rows if r["status_fit"] == "적합")
        d["over"] = sum(1 for r in rows if r["status_fit"] == "과잉")
        d["under"] = sum(1 for r in rows if r["status_fit"] == "미달")
        d["hal"] = sum(1 for r in rows if r["hallucination"] is True)
        d["defl"] = sum(1 for r in rows if r["safe_deflection"] is True)
        d["acrit"] = sum(1 for r in rows if r["severity"] == "Critical")
        d["an"] = len(rows)
    return d


def row(label, fn, data):
    return "| " + label + " | " + " | ".join(fn(data[t]) if data.get(t) else "—"
                                             for t, _ in ARMS) + " |"


def main():
    qs = {str(i.get("cid") or i.get("no")): i
          for i in jload(REG / "questions.json")["items"]}
    data = {t: collect(t) for t, _ in ARMS}
    have = [t for t, _ in ARMS if data.get(t)]
    if not have:
        raise SystemExit("실행 결과가 없다")

    L = []
    add = L.append
    add("# 프롬프트 4종 비교 — 45문항 + 불변제약 10 (2026-08-05)\n")

    # ── 실행 증빙
    add("## 실행 증빙\n")
    add("| 항목 | " + " | ".join(n for _, n in ARMS) + " |")
    add("|---|" + "---|" * len(ARMS))
    for label, fn in [
        ("프롬프트 파일", lambda d: Path(d["answers"]["bot"]["prompt_source"]).name),
        ("프롬프트 길이", lambda d: f"{d['answers']['bot']['prompt_len']:,}자"),
        ("봇", lambda d: f"{d['answers']['bot']['name']} (id {d['answers']['bot']['id']})"),
        ("모델", lambda d: f"`{d['answers']['bot']['model']}`"),
        ("호출", lambda d: f"{d['n']} (오류 {d['err']})"),
    ]:
        add(row(label, fn, data))
    add("\nRAG: 봇 11 문서 2건 — 규정집 v20 + 대사전 v4 (둘 다 `STATE_ACTIVE`, sha256 원본 일치).")
    add(f"회차 {data[have[0]]['answers'].get('reps', 1)}회 · 온도 0.3 · top_k 12 "
        "(`generate_with_rag` 운영 경로 그대로, `bots.system_prompt` 무변경).\n")

    # ── 핵심 지표
    add("## 핵심 지표\n")
    add("| 지표 | " + " | ".join(n for _, n in ARMS) + " |")
    add("|---|" + "---:|" * len(ARMS))
    for label, fn in [
        ("검색 반영 (chunks>0)", lambda d: f"{d['measured']-d['empty']}/{d['measured']} ({pct(d['measured']-d['empty'], d['measured'])})"),
        ("인용 표시", lambda d: f"{d['cited']}/{d['measured']} ({pct(d['cited'], d['measured'])})"),
        ("**앵커 충족률**", lambda d: f"**{d['hit']}/{d['tot']} ({pct(d['hit'], d['tot'])})**" if d.get("anchor") else "—"),
        ("**근거상태 적합**", lambda d: f"**{d['fit']}/{d['an']} ({pct(d['fit'], d['an'])})**" if d.get("anchor") else "—"),
        ("  └ 과잉(근거없는데 단정)", lambda d: str(d["over"]) if d.get("anchor") else "—"),
        ("  └ 미달(근거있는데 회피)", lambda d: str(d["under"]) if d.get("anchor") else "—"),
        ("할루시네이션 (45문항)", lambda d: f"{d['hal']}/{d['an']} ({pct(d['hal'], d['an'])})" if d.get("anchor") else "—"),
        ("안전 응대(정보 미제공)", lambda d: f"{d['defl']}/{d['an']}" if d.get("anchor") else "—"),
        ("Critical — 앵커 판정", lambda d: str(d["acrit"]) if d.get("anchor") else "—"),
        ("Critical — L2 기계판정", lambda d: str(d["l2"]["critical_fails"]) if d.get("l2") else "—"),
        ("정확도 — C01~C10", lambda d: f"{d['l3']['accuracy_pct']:.0f}%" if d.get("l3") and d["l3"].get("accuracy_pct") is not None else "—"),
        ("할루시율 — C01~C10", lambda d: f"{d['l3']['hallucination_pct']:.0f}%" if d.get("l3") and d["l3"].get("hallucination_pct") is not None else "—"),
        ("Critical — C01~C10", lambda d: str(d["l3"]["critical"]) if d.get("l3") else "—"),
        ("평균 응답 길이", lambda d: f"{d['len']:.0f}자"),
        ("평균 생성 시간", lambda d: f"{d['ms']:,.0f}ms"),
    ]:
        add(row(label, fn, data))
    add("")

    # ── 규정집 근거 상태별 분해
    add("## 규정집 근거 상태별 앵커 충족률\n")
    add("관리자가 xlsx `답변키워드_45개` 에 붙인 라벨로 나눈다.\n")
    add("| 근거 상태 | 문항 | " + " | ".join(n for _, n in ARMS) + " |")
    add("|---|---:|" + "---:|" * len(ARMS))
    for st in ("직접 근거 있음", "부분 근거", "직접 답변 근거 없음"):
        nq = sum(1 for i in qs.values() if i.get("evidence_status") == st)
        cells = []
        for t, _ in ARMS:
            d = data.get(t)
            if not d or not d.get("anchor"):
                cells.append("—"); continue
            rs = [r for r in d["arows"] if r["evidence_status"] == st]
            h = sum(len(r["anchors_hit"] or []) for r in rs)
            tt = sum(r["n_anchors"] for r in rs)
            f = sum(1 for r in rs if r["status_fit"] == "적합")
            cells.append(f"앵커 {pct(h, tt)} · 적합 {pct(f, len(rs))}")
        add(f"| {st} | {nq} | " + " | ".join(cells) + " |")
    add("")

    # ── 카테고리별
    add("## 카테고리별 앵커 충족률\n")
    cats = sorted({i["cat"] for i in qs.values() if i.get("bucket") != "C"})
    add("| 카테고리 | 문항 | " + " | ".join(n for _, n in ARMS) + " |")
    add("|---|---:|" + "---:|" * len(ARMS))
    for c in cats:
        nq = sum(1 for i in qs.values() if i.get("cat") == c)
        cells = []
        for t, _ in ARMS:
            d = data.get(t)
            if not d or not d.get("anchor"):
                cells.append("—"); continue
            rs = [r for r in d["arows"] if r["cat"] == c]
            h = sum(len(r["anchors_hit"] or []) for r in rs)
            tt = sum(r["n_anchors"] for r in rs)
            cells.append(pct(h, tt))
        add(f"| {c} | {nq} | " + " | ".join(cells) + " |")
    add("")

    # ── 문항별 매트릭스
    add("## 문항별 앵커 충족 (2회 평균)\n")
    add("`적/과/미` = 근거상태 적합·과잉·미달 · `H` = 할루시 · `!` = Critical\n")
    add("| # | 근거 | 위험 | 질문 | " + " | ".join(n for _, n in ARMS) + " |")
    add("|---:|---|---|---|" + "---|" * len(ARMS))
    nums = sorted((int(k) for k, i in qs.items() if i.get("bucket") != "C"))
    for no in nums:
        it = qs[str(no)]
        cells = []
        for t, _ in ARMS:
            d = data.get(t)
            if not d or not d.get("anchor"):
                cells.append("—"); continue
            rs = [r for r in d["arows"] if r["no"] == no]
            if not rs:
                cells.append("—"); continue
            h = sum(len(r["anchors_hit"] or []) for r in rs)
            tt = sum(r["n_anchors"] for r in rs)
            fits = {"적합": "적", "과잉": "과", "미달": "미"}
            f = "".join(sorted({fits.get(r["status_fit"], "?") for r in rs}))
            mark = ("H" if any(r["hallucination"] for r in rs) else "") + \
                   ("!" if any(r["severity"] == "Critical" for r in rs) else "")
            cells.append(f"{pct(h, tt)} {f}{mark}")
        st = {"직접 근거 있음": "직접", "부분 근거": "부분", "직접 답변 근거 없음": "**없음**"}
        add(f"| {no} | {st.get(it['evidence_status'], '?')} | {it['risk']} | "
            f"{it['q'][:38]} | " + " | ".join(cells) + " |")
    add("")

    # ── 불변제약
    add("## 불변제약 C01~C10 (L3 · 골든 보유)\n")
    add("| 문항 | 게이트 | " + " | ".join(n for _, n in ARMS) + " |")
    add("|---|---|" + "---|" * len(ARMS))
    for i in range(1, 11):
        cid = f"C{i:02d}"
        it = qs.get(cid, {})
        cells = []
        for t, _ in ARMS:
            d = data.get(t)
            if not d or not d.get("l3"):
                cells.append("—"); continue
            rs = [r for r in d["l3"]["rows"] if r["qkey"] == cid]
            if not rs:
                cells.append("—"); continue
            v = "/".join(sorted({r["verdict"] for r in rs}))
            sev = sorted({r["severity"] for r in rs if r["severity"] != "없음"})
            cells.append(v + (f" ({sev[0]})" if sev else ""))
        add(f"| `{cid}` {it.get('cat','')[5:]} | {it.get('gate','')} | " + " | ".join(cells) + " |")
    add("")

    # ── 불안정
    add("## 회차 간 판정이 갈린 문항\n")
    add("잡음 바닥이 20pp 라 1회 결과로는 개입 효과를 못 가른다. 2회 중 1회만 적중한 것들이다.\n")
    any_un = False
    for t, name in ARMS:
        d = data.get(t)
        if not d or not d.get("anchor"):
            continue
        per = {}
        for r in d["arows"]:
            per.setdefault(r["no"], []).append(r)
        un = [no for no, rs in per.items() if len(rs) > 1
              and len({r["status_fit"] for r in rs}) > 1]
        if un:
            any_un = True
            add(f"- **{name}** — {len(un)}문항: {sorted(un)}")
    if not any_un:
        add("- (없음 또는 1회 실행)")
    add("")

    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"→ {OUT}  ({len(L)}줄)")


if __name__ == "__main__":
    main()
