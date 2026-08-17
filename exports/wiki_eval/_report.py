# answers.json → HTML 리포트. API 호출 0.
#
# 세 팔을 나란히 놓는다. 합치지 않는다 — 합치면 어느 쪽 덕에 맞았는지 못 가린다.
# 위키 팔에는 1단이 고른 페이지를 같이 실어, 틀렸을 때 검색 탓인지 생성 탓인지 가른다.
import html
import json
import statistics as st
from pathlib import Path

DIR = Path(__file__).parent
OUT = DIR / "report.html"

ARMS = [
    ("rag", "팔 A · RAG", "Gemini file_search 가 스토어(PDF 2건)에서 검색"),
    ("wiki", "팔 B · 위키→원문", "하이브리드로 페이지를 고르고 그 페이지의 원문 전부를 주입(최대 24건)"),
    ("wiki_budget", "팔 B′ · 예산", "같은 검색기, 원문은 RRF 유닛 순위 상위 예산분만(3,000자·최대 8건)"),
    ("wiki_first", "팔 C · 위키 우선", "카파시 원안 — 위키 페이지 본문으로 답한다"),
    ("hybrid", "팔 F · A+BM25", "file_search 를 그대로 돌리되 BM25 원문을 함께 준다 — 대체가 아니라 보완"),
    ("union_ac", "A+C 사후결합", "새 호출 없이 팔 A 와 팔 C 의 답을 이어 붙인 것 — 결합의 추정 상한"),
    ("union_ab2", "A+B′ 사후결합", "새 호출 없이 팔 A 와 팔 B′ 의 답을 이어 붙인 것 — 결합의 추정 상한"),
    ("arb_ac", "G′ A+C 중재", "A 와 C 의 답을 세 번째 호출로 정리 — 이어 붙이기가 아니라 충돌 해소 (중재자 codex)"),
    ("full", "팔 D · 통째", "원문 250건 전체(≈73k 토큰)를 검색 없이 주입 — 상한선 측정용"),
]


def esc(s) -> str:
    return html.escape(str(s or ""))


def bar(pct: int | None, best: int | None) -> str:
    if pct is None:
        return ""
    cls = "win" if best is not None and pct == best and pct > 0 else "tie"
    return f'<div class=bar><i class="{cls}" style="width:{pct}%"></i><b>{pct}%</b></div>'


def arm_cell(row: dict, key: str, best: int | None) -> str:
    a = row.get(key)
    if not a:
        return "<td class=empty>—</td>"
    err = f'<p class=err>{esc(a["error"])}</p>' if a.get("error") else ""
    cites = "".join(
        f'<li>{esc((c.get("title") or "")[:70])}</li>' for c in (a.get("citations") or [])[:8]
    )
    n_cite = len(a.get("citations") or [])
    stage1 = ""
    if a.get("stage1"):
        chips = " ".join(
            f'<span class=chip>{esc(p["slug"])} <em>{p["score"]}</em></span>' for p in a["stage1"]
        )
        stage1 = f'<div class=s1><span class=lbl>1단 융합</span>{chips}</div>'
        # 하이브리드가 실제로 순위를 바꿨는지 — dense 만 / BM25 만 썼을 때의 1~3위를 같이 놓는다.
        for key, name in (("page_dense", "dense"), ("page_bm25", "BM25")):
            rows = (a.get("retrieval") or {}).get(key) or []
            if rows:
                sub = " ".join(
                    f'<span class="chip alt">{esc(s)} <em>{v}</em></span>' for s, v in rows[:3]
                )
                stage1 += f'<div class=s1><span class=lbl>{name}</span>{sub}</div>'
    miss = [d["kw"] for d in (a.get("kw_detail") or []) if d["frac"] < 0.5]
    missed = (
        f'<div class=miss><span class=lbl>못 맞힌 키워드</span>{esc(", ".join(miss))}</div>'
        if miss else ""
    )
    return (
        f"<td>{bar(a.get('kw_pct'), best)}"
        f'<div class=meta>{a.get("elapsed_s")}초 · {len(a["answer"])}자 · 인용 {n_cite}건 · '
        f'통문자 {a.get("kw_exact", 0)}/{a.get("kw_total", 0)}</div>'
        f"{err}{stage1}"
        f'<div class=ans>{esc(a["answer"])[:1600] or "<i>빈 응답</i>"}</div>'
        f"{missed}"
        f"<details><summary>인용 {n_cite}건</summary><ol>{cites}</ol></details></td>"
    )


def deferral_html(live: list[tuple[str, str, str]]) -> str:
    """③ 유보 정확도. grades.json 과 corpus_evidence.json 이 둘 다 있어야 낸다.

    ①(키워드)과 ②(내용)는 "맞혔는가"만 잰다. 이 판은 틀린 답보다 유보가 나은 판이라
    "없는 걸 없다고 말했는가"를 따로 세지 않으면 위키의 값어치를 통째로 놓친다.
    """
    gpath, epath = DIR / "grades.json", DIR / "corpus_evidence.json"
    if not (gpath.exists() and epath.exists()):
        return ""
    graded = json.loads(gpath.read_text(encoding="utf-8"))
    ev = {k: v for k, v in json.loads(epath.read_text(encoding="utf-8")).items()
          if not k.startswith("_")}
    n_out = sum(1 for v in ev.values() if v["label"] == "out")
    n_in = len(ev) - n_out

    body = []
    for key, title, _ in live:
        good_def = over_def = good_ans = harm_ans = 0
        for g in graded:
            label = ev.get(str(g["n"]), {}).get("label")
            if label is None:
                continue
            grade = g["grades"].get(key, {})
            if grade.get("refusal"):
                if label == "out":
                    good_def += 1
                else:
                    over_def += 1
            elif grade.get("harm", 0) < 0:
                harm_ans += 1
            elif label == "in":
                good_ans += 1
        body.append(
            f"<tr><th>{esc(title)}</th>"
            f"<td class=win>{good_def} / {n_out}</td><td>{over_def} / {n_in}</td>"
            f"<td>{good_ans}</td><td class=bad>{harm_ans}</td></tr>"
        )

    return f"""<div class=defer><h3>③ 유보 정확도 <span>코퍼스 근거 있음 {n_in}건 · 없음 {n_out}건 ·
 정답지 시트 ① 「확인되지 않습니다 + 담당자 연결만 해도 정답인가」 = 45/45 "예"</span></h3>
<table class=mini><thead><tr><th></th><th>정당 유보<br><i>근거 없는데 유보</i></th>
<th>과잉 유보<br><i>근거 있는데 유보</i></th><th>정당 확답</th><th>유해 확답</th></tr></thead>
<tbody>{''.join(body)}</tbody></table>
<p class=note>관리자 기준 병기: golden 10건은 <b>전부 확답형</b>이다. 그 기준으로만 재면 위 「정당 유보」도 감점이 된다.
근거 라벨과 판정 근거는 <code>corpus_evidence.json</code> 에 문항별로 남겼다.</p></div>"""


def main() -> None:
    all_rows = json.loads((DIR / "answers.json").read_text(encoding="utf-8"))
    live = [(k, t, d) for k, t, d in ARMS if any(k in r for r in all_rows)]

    def done(r: dict, key: str) -> bool:
        return key in r and not r[key].get("error") and bool(r[key].get("answer"))

    # **실패 셀은 평균에서 뺀다.** 429 로 죽은 셀은 kw_pct 가 0 이라, 그냥 평균 내면
    # 쿼터에 걸린 팔이 성능이 나쁜 것처럼 보인다. 팔끼리 비교하려면 같은 문항 위에서 재야 하므로
    # **모든 팔이 성공한 문항**만 쓴다.
    rows = [r for r in all_rows if all(done(r, k) for k, _, _ in live)]
    partial = len(rows) != len(all_rows)

    def avg(key: str, field: str = "kw_pct") -> float:
        v = [r[key][field] for r in rows if key in r and r[key].get(field) is not None]
        return st.mean(v) if v else 0.0

    base = avg("rag")
    kpis = []
    for key, title, _ in live:
        pct, secs, chars = avg(key), avg(key, "elapsed_s"), avg(key, "kw_pct")
        length = st.mean([len(r[key]["answer"]) for r in rows if key in r])
        delta = "" if key == "rag" else f'<span class=d>{pct - base:+.1f}pp</span>'
        kpis.append(
            f"<div class=kpi><b>{pct:.1f}%{delta}</b>"
            f"<span>{esc(title)}</span>"
            f"<span class=sub2>{secs:.1f}초 · 평균 {length:.0f}자</span></div>"
        )
        _ = chars

    # 문항별 최고점 팔이 몇 번 나왔는지
    tally = {k: 0 for k, _, _ in live}
    for r in rows:
        scores = {k: r[k]["kw_pct"] for k, _, _ in live if k in r and r[k].get("kw_pct") is not None}
        if scores:
            top = max(scores.values())
            for k, v in scores.items():
                if v == top:
                    tally[k] += 1

    best_key = max(live, key=lambda t: avg(t[0]))[0]
    best_pct = avg(best_key)
    verdict = (
        f"{dict((k, t) for k, t, _ in live)[best_key]} 우세 — "
        + (
            f"팔 A 대비 {best_pct - base:+.1f}pp, 판정선 20pp "
            + ("충족" if best_pct - base >= 20 else "미달")
            if best_key != "rag"
            else "위키 계열이 팔 A 를 넘지 못했다"
        )
    )
    # 자가 두 개다. 순위가 갈리면 그 사실 자체가 결과다 — 하나만 보고 판정하지 않는다.
    verdict += " · ①(키워드)만의 판정이다. ②·③은 아래 표를 함께 볼 것"

    cards = []
    for r in all_rows:
        scores = {k: r[k]["kw_pct"] for k, _, _ in live if k in r and r[k].get("kw_pct") is not None}
        best = max(scores.values()) if scores else None
        golden = (
            f'<div class=golden><span class=lbl>관리자 정답</span>{esc(r["golden"])}</div>'
            if r.get("golden") else ""
        )
        cards.append(f"""
<section>
  <header><span class=n>#{r['n']}</span>
    <div><h2>{esc(r['question'])}</h2>
      <p class=tags><span>위험 {esc(r.get('risk'))}</span><span>{esc(r.get('category'))}</span>
      <span>키워드 {len(r.get('keywords') or [])}개</span></p></div>
  </header>
  {golden}
  <table><thead><tr>{"".join(f"<th>{esc(t)}</th>" for _, t, _ in live)}</tr></thead>
  <tbody><tr>{"".join(arm_cell(r, k, best) for k, _, _ in live)}</tr></tbody></table>
</section>""")

    scope = (
        f"① 집계 대상 {len(rows)}/{len(all_rows)}문항 — 모든 팔이 성공한 문항만"
        + (" (나머지는 무료 티어 하루 상한으로 미완)" if partial else "")
    )
    legend = "".join(
        f"<li><b>{esc(t)}</b> — {esc(d)}</li>" for _, t, d in live
    )
    tally_txt = " · ".join(
        f"{dict((k, t) for k, t, _ in live)[k]} {v}건" for k, v in tally.items()
    )

    OUT.write_text(f"""<!doctype html><meta charset=utf-8>
<title>위키 vs RAG · 45문항 · 봇 11</title>
<style>
:root{{--bg:#fff;--fg:#18181b;--mut:#71717a;--line:#e4e4e7;--card:#fafafa;--win:#16a34a;--tie:#a1a1aa;--lose:#dc2626}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0c0c0e;--fg:#e8e8ea;--mut:#8b8b93;--line:#27272a;--card:#141416;
 --win:#4ade80;--tie:#52525b;--lose:#f87171}}}}
*{{box-sizing:border-box}}
body{{background:var(--bg);color:var(--fg);font:14px/1.65 -apple-system,'Pretendard',sans-serif;
 margin:0 auto;padding:0 18px 80px;max-width:1500px}}
h1{{font-size:24px;margin:32px 0 4px}}
.sub{{color:var(--mut);font-size:13px;margin:0 0 20px}}
.summary{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:0 0 12px}}
.kpi{{border:1px solid var(--line);border-radius:10px;padding:14px 16px;background:var(--card)}}
.kpi b{{display:block;font-size:26px;line-height:1.2}}
.kpi .d{{font-size:13px;color:var(--mut);margin-left:8px;font-weight:600}}
.kpi span{{color:var(--mut);font-size:12px;display:block}}
.kpi .sub2{{font-size:11px;margin-top:2px}}
.verdict{{border:1px solid var(--line);border-left:4px solid var(--tie);border-radius:10px;
 padding:14px 18px;margin:0 0 12px;background:var(--card);font-weight:600}}
.legend{{border:1px solid var(--line);border-radius:10px;padding:12px 18px 12px 34px;margin:0 0 30px;
 background:var(--card);font-size:12px;color:var(--mut)}}
.legend li{{margin:2px 0}} .legend b{{color:var(--fg)}}
section{{border:1px solid var(--line);border-radius:12px;margin:0 0 22px;background:var(--card);overflow:hidden}}
section>header{{display:flex;gap:12px;padding:14px 18px;border-bottom:1px solid var(--line)}}
.n{{flex:none;width:30px;height:24px;border-radius:12px;background:var(--fg);color:var(--bg);
 display:grid;place-items:center;font-size:12px;font-weight:700}}
h2{{font-size:15px;margin:0;font-weight:600}}
.tags{{margin:3px 0 0;display:flex;gap:6px;flex-wrap:wrap}}
.tags span{{font-size:11px;color:var(--mut);border:1px solid var(--line);border-radius:20px;padding:0 8px}}
.golden{{padding:10px 18px;border-bottom:1px solid var(--line);font-size:13px}}
.lbl{{display:inline-block;font-size:11px;color:var(--mut);margin-right:8px;font-weight:600}}
table{{width:100%;border-collapse:collapse;table-layout:fixed}}
th{{text-align:left;font-size:12px;color:var(--mut);padding:8px 16px;border-bottom:1px solid var(--line);font-weight:600}}
td{{vertical-align:top;padding:12px 16px;border-right:1px solid var(--line)}}
td:last-child,th:last-child{{border-right:0}}
.bar{{display:flex;align-items:center;gap:8px;margin-bottom:4px}}
.bar i{{height:8px;border-radius:4px;background:var(--tie);min-width:2px}}
.bar i.win{{background:var(--win)}}
.bar b{{font-size:13px;flex:none}}
.meta{{color:var(--mut);font-size:11px;margin-bottom:8px}}
.ans{{white-space:pre-wrap;font-size:13px;max-height:300px;overflow:auto;
 border-left:2px solid var(--line);padding-left:10px}}
.s1{{margin:0 0 8px}}
.chip{{display:inline-block;font-size:11px;border:1px solid var(--line);border-radius:20px;padding:1px 8px;margin:2px 3px 2px 0}}
.chip em{{color:var(--mut);font-style:normal}}
.chip.alt{{opacity:.62}}
.defer{{border:1px solid var(--line);border-radius:10px;padding:14px 18px;margin:0 0 12px;background:var(--card)}}
.defer h3{{font-size:14px;margin:0 0 10px}}
.defer h3 span{{font-weight:400;color:var(--mut);font-size:11px;display:block;margin-top:2px}}
table.mini{{width:auto;min-width:520px;border-collapse:collapse;table-layout:auto}}
table.mini th,table.mini td{{border:0;border-bottom:1px solid var(--line);padding:5px 14px 5px 0;
 font-size:13px;text-align:right;vertical-align:middle}}
table.mini thead th{{font-size:11px;color:var(--mut);font-weight:600}}
table.mini thead th i{{font-style:normal;font-weight:400;font-size:10px}}
table.mini tbody th{{text-align:left;font-weight:600;font-size:13px;color:var(--fg)}}
table.mini td.win{{color:var(--win);font-weight:700}}
table.mini td.bad{{color:var(--lose);font-weight:700}}
.note{{font-size:11px;color:var(--mut);margin:10px 0 0}}
.note code{{font-size:11px}}
.miss{{margin-top:8px;font-size:11px;color:var(--mut)}}
details{{margin-top:8px}} summary{{font-size:12px;color:var(--mut);cursor:pointer}}
ol{{margin:6px 0 0;padding-left:20px;font-size:11px;color:var(--mut)}}
.err{{color:var(--lose);font-size:12px}}
.empty{{color:var(--mut)}}
@media(max-width:900px){{table,thead,tbody,tr,th,td{{display:block;width:auto}}td{{border-right:0;border-bottom:1px solid var(--line)}}}}
</style>
<h1>위키 vs RAG — 45문항</h1>
<p class=sub>봇 11 「테스트 봇 D-1 ver2」 · gemini-3.5-flash-lite · 온도 0.3 ·
같은 system_prompt·근거지시·max_tokens · <b>다른 것은 근거를 무엇으로 주느냐 하나</b> ·
채점은 관리자 키워드 토큰 부분점수 · <b>{esc(scope)}</b></p>
<div class=summary>{"".join(kpis)}</div>
<div class=verdict>판정: {esc(verdict)}<br><span style="font-weight:400;color:var(--mut);font-size:13px">
문항별 최고점: {esc(tally_txt)}</span></div>
{deferral_html(live)}
<ul class=legend>{legend}</ul>
{"".join(cards)}
""", encoding="utf-8")

    print(f"→ {OUT}")
    for key, title, _ in live:
        print(f"  {title:16} {avg(key):5.1f}%  ({avg(key) - base:+5.1f}pp)  "
              f"{avg(key, 'elapsed_s'):4.1f}초  평균 "
              f"{st.mean([len(r[key]['answer']) for r in rows if key in r]):.0f}자")
    print(f"  문항별 최고점: {tally_txt}")


if __name__ == "__main__":
    main()
