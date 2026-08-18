# 관측표 생성 — _dump2.json · _branches.json · _match.json → REPORT.md
#
# 숫자를 손으로 옮기지 않는다. 보고서의 모든 수는 이 스크립트가 원 데이터에서 뽑는다.
import json
from pathlib import Path

DIR = Path(__file__).parent
ANSWER_ARMS = ("P", "M1")
CHUNK_ARMS = ("NP", "NM1")

dump = json.loads((DIR / "_dump2.json").read_text(encoding="utf-8"))
branches = json.loads((DIR / "_branches.json").read_text(encoding="utf-8"))["questions"]
matches = json.loads((DIR / "_match.json").read_text(encoding="utf-8"))["questions"]
labels = {it["qid"]: it for it in
          json.loads((DIR / "_questions_pyeongseong.json").read_text(encoding="utf-8"))["items"]}

recs = [r for r in dump["results"] if r.get("ok")]
judged = [b["qid"] for b in branches]
BR = {b["qid"]: b for b in branches}
MT = {m["qid"]: m for m in matches}
L = []


def w(s=""):
    L.append(s)


def pages(r):
    return {c.get("page_number") for c in r["grounding"]["chunks"] if c.get("page_number")}


def rows(qid, arm, src=None):
    return sorted([r for r in (src or recs) if r["qid"] == qid and r["arm"] == arm],
                  key=lambda x: x["rep"])


w("# 관측표 — 편성축 reps 5 (2026-08-05)")
w()
w(f"원 데이터: `_dump2.json` ({len(recs)}호출) · `_branches.json`(1단) · `_match.json`(2단)")
w(f"봇 {dump['bot']['id']} · 모델 `{dump['bot']['model']}` · top_k {dump['rag_top_k']} · "
  f"temperature {dump['rag_temperature']} · 용어집 `{Path(dump['glossary']).name}` "
  f"{dump['glossary_terms']}개")
w()
w("**판정 대상은 4팔 × 5회가 모두 찬 9문항이다.** 나머지 3문항은 일일 한도로 미완 — §5 참조.")
w()

w("## 1. 검색 — p.21(편성 비교표) 회수")
w()
w("페르소나 팔은 grounding 보고를 억제하므로(AGENTS.md §3-3) 검색 관측은 중립 팔로만 한다.")
w()
w("| 문항 | NP(원질문) | NM1(어휘확장) | M1 확장 |")
w("|---|---|---|---|")
tot = {a: 0 for a in CHUNK_ARMS}
den = 0
for qid in judged:
    cells = []
    for a in CHUNK_ARMS:
        rs = rows(qid, a)
        hit = sum(1 for r in rs if 21 in pages(r))
        tot[a] += hit
        cells.append(f"{hit}/{len(rs)}")
    den += len(rows(qid, "NP"))
    exp = rows(qid, "M1")[0]["expanded"]
    w(f"| {qid} | {cells[0]} | {cells[1]} | {'O' if exp else 'X'} |")
w(f"| **합계** | **{tot['NP']}/{den}** | **{tot['NM1']}/{den}** | |")
w()

w("## 2. 팔별 회수·인용 평균")
w()
w("| 팔 | 평균 청크 | 청크 0회 | 평균 인용 | 평균 답변 길이 |")
w("|---|---|---|---|---|")
for a in ("P", "NP", "M1", "NM1"):
    rs = [r for r in recs if r["arm"] == a and r["qid"] in judged]
    n = len(rs)
    w(f"| {a} | {sum(r['grounding']['n_chunks'] for r in rs)/n:.1f} | "
      f"{sum(1 for r in rs if r['grounding']['n_chunks']==0)}/{n} | "
      f"{sum(r['n_citations'] for r in rs)/n:.1f} | "
      f"{sum(len(r['answer'] or '') for r in rs)/n:.0f}자 |")
w()

w("## 3. 분기 수 · 미근거 조건 (1단 — 선행과 같은 자)")
w()
w("| 문항 | P 분기 5회 | M1 분기 5회 | P 미근거 | M1 미근거 |")
w("|---|---|---|---|---|")


def arm_br(qid, arm):
    rs = sorted([x for x in BR[qid]["results"] if x["arm"] == arm], key=lambda x: x["rep"])
    n = [x["n_branches"] for x in rs]
    brs = [b for x in rs for b in (x.get("branches") or [])]
    ung = [b for b in brs if b.get("grounded") is False]
    return n, len(brs), len(ung)


agg = {a: [0.0, 0, 0] for a in ANSWER_ARMS}
for qid in judged:
    c = {a: arm_br(qid, a) for a in ANSWER_ARMS}
    for a in ANSWER_ARMS:
        agg[a][0] += sum(c[a][0]) / max(len(c[a][0]), 1)
        agg[a][1] += c[a][1]
        agg[a][2] += c[a][2]
    w(f"| {qid} | {c['P'][0]} | {c['M1'][0]} | {c['P'][2]} | {c['M1'][2]} |")
n = len(judged)
w(f"| **평균/합계** | **{agg['P'][0]/n:.1f}** | **{agg['M1'][0]/n:.1f}** | "
  f"{agg['P'][2]}/{agg['P'][1]} | {agg['M1'][2]}/{agg['M1'][1]} |")
w()
w("평균 분기는 **문항 구성에 좌우된다.** P-100 처럼 요건 나열형 문항은 한 답변에서 3~7 분기가")
w("나와 평균을 끌어올린다. 이 지표만으로 개입을 판정하면 안 된다 — 그래서 4절을 따로 둔다.")
w()

w("## 4. 정답 분기 적중 (2단 — 신규)")
w()
w("분기 *수*가 아니라 사람이 조문으로 정해 둔 케이스를 덮었는가를 본다.")
w()
w("| 문항 | 정답 케이스 | P 적중 | M1 적중 | P 위반 | M1 위반 |")
w("|---|---|---|---|---|---|")
tot2 = {a: [0, 0, 0, 0, 0] for a in ANSWER_ARMS}     # 적중·기대·위반·부분·과잉
for qid in judged:
    lab = labels[qid]
    nexp = len(lab["expected_branches"])
    cells = {}
    for a in ANSWER_ARMS:
        rs = [x for x in MT[qid]["results"] if x["arm"] == a]
        hit = sum(len(x.get("covered") or []) for x in rs)
        vio = sum(len(x.get("violated") or []) for x in rs)
        part = sum(len(x.get("partial") or []) for x in rs)
        spur = sum(len(x.get("spurious") or []) for x in rs)
        d = nexp * len(rs)
        cells[a] = (hit, d, vio)
        tot2[a][0] += hit
        tot2[a][1] += d
        tot2[a][2] += vio
        tot2[a][3] += part
        tot2[a][4] += spur
    w(f"| {qid} | {nexp} | {cells['P'][0]}/{cells['P'][1]} | "
      f"{cells['M1'][0]}/{cells['M1'][1]} | {cells['P'][2]} | {cells['M1'][2]} |")
w(f"| **합계** | | **{tot2['P'][0]}/{tot2['P'][1]} "
  f"({tot2['P'][0]/tot2['P'][1]:.0%})** | **{tot2['M1'][0]}/{tot2['M1'][1]} "
  f"({tot2['M1'][0]/tot2['M1'][1]:.0%})** | {tot2['P'][2]} | {tot2['M1'][2]} |")
w()
w(f"부분충족 — P {tot2['P'][3]} · M1 {tot2['M1'][3]}  |  "
  f"과잉분기 — P {tot2['P'][4]} · M1 {tot2['M1'][4]}")
w()

w("## 5. 반복 간 일관성 (§6 판정표)")
w()
w("| 문항 | 팔 | 분기 수 5회 | 최빈값 | 판정 |")
w("|---|---|---|---|---|")
n_ok = n_split = 0
for qid in judged:
    for a in ANSWER_ARMS:
        nb, _, _ = arm_br(qid, a)
        top = max(set(nb), key=nb.count)
        r = nb.count(top) / len(nb)
        v = "일관" if r >= 0.8 else "**갈림**"
        n_ok += r >= 0.8
        n_split += r < 0.8
        w(f"| {qid} | {a} | {nb} | {top}: {nb.count(top)}/{len(nb)} | {v} |")
w()
w(f"일관 {n_ok}/{n_ok+n_split} · 갈림 {n_split}/{n_ok+n_split}")
w()

# R-219 특수 — M1 쿼리 == P 쿼리인 문항은 동일 조건 10회로 합칠 수 있다
w("### R-219 — 동일 조건 10회")
w()
same = rows("R-219", "P")[0]["q"] == rows("R-219", "M1")[0]["q"]
nb_p, _, _ = arm_br("R-219", "P")
nb_m, _, _ = arm_br("R-219", "M1")
pooled = nb_p + nb_m
top = max(set(pooled), key=pooled.count)
w(f"R-219 은 M1 어휘매칭이 0건이라 **M1 쿼리가 P 쿼리와 바이트 단위로 같다**"
  f"(실측 일치: {same}). 즉 P 5회 + M1 5회 = **같은 조건 10회**다.")
w()
w(f"- P  {nb_p}")
w(f"- M1 {nb_m}")
w(f"- 합쳐서 {pooled} → 최빈값 {top}: **{pooled.count(top)}/10**")
w()

(DIR / "REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print(f"→ {DIR/'REPORT.md'} ({len(L)}줄)")
