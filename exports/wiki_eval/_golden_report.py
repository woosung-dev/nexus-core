# 정답 10건 × 8개 답변 방식 → 채점 비교 HTML. API 호출 0.
#
# `_report.py`(45문항 · 키워드 자)와 다른 것을 본다. 여기는 **관리자 정답이 있는 10건**만,
# 대신 codex 내용 채점을 **세 회차 모두** 실어 판정이 얼마나 흔들리는지 문항 단위로 보인다.
#
# 사용: uv run python ../exports/wiki_eval/_golden_report.py
import html
import json
from pathlib import Path

DIR = Path(__file__).parent
OUT = DIR / "golden_report.html"

# 채점 회차. 같은 답을 세 번 쟀고 점수가 움직였다 — 그 사실 자체가 이 문서의 결론 중 하나다.
RUNS = [
    ("5팔①", "grades_5arm.json", "A·B·B′·C·F"),
    ("7팔", "grades.json", "위 5팔 + 사후결합 2종"),
    ("융합", "grades_fusion.json", "A·C·F·A+C 사후결합·G′ 중재"),
]

ARMS = [
    ("rag", "A", "RAG", "Gemini file_search 가 스토어(PDF 2건)에서 검색한다. 현재 라이브 경로."),
    ("wiki", "B", "위키→원문", "BM25 멀티스케일로 페이지를 고르고 그 페이지의 원문 전부를 넣는다(최대 24건)."),
    ("wiki_budget", "B′", "예산", "같은 검색기. 원문은 순위 상위 예산분만(3,000자·최대 8건·최소 4건)."),
    ("wiki_first", "C", "위키 본문", "카파시 원안. 위키 페이지 본문으로 답한다. 원문은 따로 넣지 않는다."),
    ("hybrid", "F", "A + BM25 원문", "file_search 를 그대로 돌리되 BM25 원문을 앞선 턴으로 함께 준다."),
    ("union_ac", "A+C", "사후결합", "새 호출 없이 A 와 C 의 답을 그대로 이어 붙인 것."),
    ("union_ab2", "A+B′", "사후결합", "새 호출 없이 A 와 B′ 의 답을 그대로 이어 붙인 것."),
    ("arb_ac", "G′", "A+C 중재", "A 와 C 의 답을 세 번째 호출이 읽고 충돌을 정리한다. 중재자는 codex."),
]
LABEL = {k: f"{code} {name}" for k, code, name, _ in ARMS}


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def load():
    rows = [r for r in json.loads((DIR / "answers.json").read_text(encoding="utf-8")) if r.get("golden")]
    grades = {}
    for tag, fname, _ in RUNS:
        p = DIR / fname
        grades[tag] = {x["n"]: x["grades"] for x in json.loads(p.read_text(encoding="utf-8"))} if p.exists() else {}
    ev = {k: v for k, v in json.loads((DIR / "corpus_evidence.json").read_text(encoding="utf-8")).items()
          if not k.startswith("_")}
    return rows, grades, ev


def primary(grades, n, key):
    """대표 점수 — 가장 최근 회차부터 찾는다. 함께 실린 다른 회차는 옆에 나란히 둔다."""
    for tag, _, _ in reversed(RUNS):
        g = grades[tag].get(n, {}).get(key)
        if g and isinstance(g.get("total"), (int, float)):
            return tag, g
    return None, None


def tone(total):
    if total is None:
        return "na"
    if total < 0:
        return "bad"
    if total >= 4:
        return "top"
    if total >= 2:
        return "ok"
    return "low"


def score_strip(grades, n, key):
    """세 회차 점수를 나란히. 같은 답인데 값이 다르면 그게 보여야 한다."""
    out = []
    for tag, _, _ in RUNS:
        g = grades[tag].get(n, {}).get(key)
        if not g or not isinstance(g.get("total"), (int, float)):
            continue
        t = g["total"]
        flags = ""
        if g.get("refusal"):
            flags = "<i class=fl-defer>유보</i>"
        elif g.get("harm", 0) < 0:
            flags = "<i class=fl-harm>유해</i>"
        out.append(
            f'<span class="sc {tone(t)}"><b>{t:+d}</b><em>{esc(tag)}</em>{flags}</span>'
        )
    return "".join(out) or '<span class="sc na"><b>—</b><em>미채점</em></span>'


def matrix(rows, grades, ev):
    head = "".join(f"<th><span>{esc(LABEL[k])}</span></th>" for k, _, _, _ in ARMS)
    body = []
    for r in rows:
        n = r["n"]
        lab = ev.get(str(n), {}).get("label")
        cells = []
        for k, _, _, _ in ARMS:
            _, g = primary(grades, n, k)
            t = g.get("total") if g else None
            mark = "✕" if (g and g.get("harm", 0) < 0) else ("○" if (g and g.get("refusal")) else "")
            cells.append(f'<td class="{tone(t)}">{"—" if t is None else f"{t:+d}"}'
                         f'{f"<i>{mark}</i>" if mark else ""}</td>')
        body.append(
            f'<tr><th class=qn><a href="#q{n}">#{n}</a></th>'
            f'<td class="ev {esc(lab)}">{"근거 없음" if lab == "out" else "있음"}</td>'
            f"{''.join(cells)}</tr>"
        )
    return f"""<div class=scroller><table class=matrix>
<thead><tr><th class=qn>문항</th><th class=ev>코퍼스 근거</th>{head}</tr></thead>
<tbody>{''.join(body)}</tbody></table></div>"""


def stability(grades):
    """같은 답 · 다른 회차 · 다른 점수. 이 표가 다른 모든 수치의 읽는 법을 정한다."""
    body = []
    for k, _, _, _ in ARMS:
        vals = []
        for tag, _, _ in RUNS:
            got = [g[k]["total"] for g in grades[tag].values()
                   if k in g and isinstance(g[k].get("total"), (int, float))]
            vals.append(sum(got) / len(got) if got else None)
        real = [v for v in vals if v is not None]
        if len(real) < 1:
            continue
        span = max(real) - min(real)
        cells = "".join(f"<td>{'—' if v is None else f'{v:.2f}'}</td>" for v in vals)
        body.append(f"<tr><th>{esc(LABEL[k])}</th>{cells}"
                    f'<td class="{"warn" if span >= 0.4 else ""}">{span:.2f}</td></tr>')
    head = "".join(f"<th>{esc(t)}</th>" for t, _, _ in RUNS)
    return f"""<div class=scroller><table class=stab>
<thead><tr><th>답변 방식</th>{head}<th>폭</th></tr></thead>
<tbody>{''.join(body)}</tbody></table></div>"""


def question_block(r, grades, ev):
    n = r["n"]
    meta = ev.get(str(n), {})
    lab = meta.get("label")
    cards = []
    for k, code, name, desc in ARMS:
        a = r.get(k)
        if not a:
            continue
        tag, g = primary(grades, n, k)
        why = esc(g.get("why", "")) if g else ""
        kw = a.get("kw_pct")
        cards.append(f"""<article class="arm {tone(g.get('total') if g else None)}">
  <header><h4><b>{esc(code)}</b> {esc(name)}</h4>
    <div class=strip>{score_strip(grades, n, k)}</div></header>
  <p class=stat>키워드 {kw if kw is not None else '—'}% · {len(a['answer'])}자 · {a.get('elapsed_s')}초</p>
  <div class=body>{esc(a['answer'])}</div>
  {f'<p class=why><span>채점 사유</span>{why}</p>' if why else ''}
</article>""")

    return f"""<section class=q id="q{n}">
  <header class=qhead>
    <div class=qtitle><span class=badge>#{n}</span>
      <h3>{esc(r['question'])}</h3></div>
    <p class=tags><span>위험 {esc(r.get('risk'))}</span><span>{esc(r.get('category'))}</span>
      <span class="ev {esc(lab)}">코퍼스 근거 {'없음' if lab == 'out' else '있음'}</span></p>
  </header>
  <div class=golden><span class=lbl>관리자 정답</span><p>{esc(r['golden'])}</p></div>
  {f'<p class=evwhy><span class=lbl>근거 판정</span>{esc(meta.get("why"))}</p>' if meta.get("why") else ''}
  <div class=arms>{''.join(cards)}</div>
</section>"""


CSS = """
:root{
  --paper:#f4f6f7; --card:#fff; --sunk:#eceff1;
  --ink:#15181c; --mid:#4d555e; --mute:#79828c; --line:#d9dee3;
  --accent:#2c4a72; --accent-soft:#e3eaf3;
  --good:#1a6f48; --good-bg:#e2f1e9;
  --bad:#a8332a; --bad-bg:#fae7e5;
  --defer:#8a6a17; --defer-bg:#f7eed6;
  --sans:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Segoe UI",Roboto,"Noto Sans KR",sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --paper:#0e1115; --card:#161a1f; --sunk:#1c2127;
  --ink:#e4e8ec; --mid:#aab3bd; --mute:#7d8791; --line:#282f37;
  --accent:#8fb0dd; --accent-soft:#1c2836;
  --good:#5cc48d; --good-bg:#12291f;
  --bad:#ef8177; --bad-bg:#2e1a18;
  --defer:#d7ae44; --defer-bg:#2b2312;
}}
:root[data-theme="dark"]{
  --paper:#0e1115; --card:#161a1f; --sunk:#1c2127;
  --ink:#e4e8ec; --mid:#aab3bd; --mute:#7d8791; --line:#282f37;
  --accent:#8fb0dd; --accent-soft:#1c2836;
  --good:#5cc48d; --good-bg:#12291f;
  --bad:#ef8177; --bad-bg:#2e1a18;
  --defer:#d7ae44; --defer-bg:#2b2312;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.7 var(--sans);
  -webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:0 22px 96px;display:flex;flex-direction:column;gap:30px}
.scroller{overflow-x:auto}

header.top{padding:46px 0 0;display:flex;flex-direction:column;gap:10px}
h1{margin:0;font-size:31px;line-height:1.22;letter-spacing:-.022em;font-weight:700;text-wrap:balance}
.kicker{font:600 11px/1 var(--mono);letter-spacing:.13em;text-transform:uppercase;color:var(--accent)}
.cond{margin:0;color:var(--mid);font-size:13.5px;max-width:68ch}
.cond code{font:500 12.5px/1 var(--mono);background:var(--sunk);padding:2px 5px;border-radius:4px}

.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:22px 24px;
  display:flex;flex-direction:column;gap:14px}
.panel h2{margin:0;font-size:16px;letter-spacing:-.012em}
.panel h2 span{display:block;font-weight:400;font-size:12.5px;color:var(--mute);margin-top:3px;
  letter-spacing:0}
.panel p{margin:0;color:var(--mid);font-size:13.5px;max-width:76ch}
.panel p b{color:var(--ink)}

.finding{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}
.finding div{background:var(--sunk);border-radius:9px;padding:13px 15px}
.finding b{display:block;font-size:13px;margin-bottom:3px}
.finding span{color:var(--mid);font-size:12.5px;line-height:1.6;display:block}

table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th,td{text-align:right;padding:7px 10px;font-size:13px;border-bottom:1px solid var(--line)}
thead th{font:600 11px/1.35 var(--mono);color:var(--mute);letter-spacing:.03em;
  text-transform:uppercase;vertical-align:bottom;white-space:nowrap}
tbody th{text-align:left;font-weight:600;white-space:nowrap}
.matrix td{font:600 13px/1 var(--mono);min-width:52px}
.matrix td i{font-style:normal;font-size:10px;margin-left:3px;opacity:.75}
.matrix th.qn{text-align:left;width:60px}
.matrix th.qn a{color:var(--accent);text-decoration:none;font:600 13px/1 var(--mono)}
.matrix th.qn a:hover{text-decoration:underline}
td.ev,th.ev{text-align:left;font-size:11.5px;color:var(--mute);white-space:nowrap}
td.ev.out{color:var(--defer);font-weight:600}
.stab td.warn{color:var(--bad);font-weight:700}

.top-cell,td.top{background:var(--good-bg);color:var(--good)}
td.ok{color:var(--ink)}
td.low{color:var(--mute)}
td.bad{background:var(--bad-bg);color:var(--bad)}
td.na{color:var(--line)}

section.q{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;
  scroll-margin-top:16px}
.qhead{padding:18px 22px 14px;border-bottom:1px solid var(--line);display:flex;
  flex-direction:column;gap:8px}
.qtitle{display:flex;gap:11px;align-items:baseline}
.badge{flex:none;font:700 11px/1 var(--mono);color:var(--accent);background:var(--accent-soft);
  padding:5px 8px;border-radius:5px}
.qhead h3{margin:0;font-size:16.5px;line-height:1.5;font-weight:650;letter-spacing:-.011em;
  text-wrap:balance}
.tags{margin:0;display:flex;gap:6px;flex-wrap:wrap}
.tags span{font-size:11px;color:var(--mute);border:1px solid var(--line);border-radius:99px;
  padding:1px 9px}
.tags span.ev.out{color:var(--defer);border-color:var(--defer);font-weight:600}

.golden{padding:15px 22px;background:var(--sunk);border-bottom:1px solid var(--line)}
.golden p{margin:5px 0 0;font-size:13.5px;line-height:1.72;white-space:pre-wrap;color:var(--ink)}
.lbl{font:600 10.5px/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--mute)}
.evwhy{margin:0;padding:11px 22px;border-bottom:1px solid var(--line);font-size:12.5px;
  color:var(--mid);display:flex;gap:10px;align-items:baseline}
.evwhy .lbl{flex:none}

.arms{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,330px),1fr));
  gap:1px;background:var(--line)}
article.arm{background:var(--card);padding:15px 20px 18px;display:flex;flex-direction:column;gap:8px}
article.arm.bad{background:linear-gradient(90deg,var(--bad-bg) 0 3px,var(--card) 3px)}
article.arm.top{background:linear-gradient(90deg,var(--good-bg) 0 3px,var(--card) 3px)}
.arm header{display:flex;flex-direction:column;gap:7px}
.arm h4{margin:0;font-size:13px;font-weight:600;color:var(--mid)}
.arm h4 b{font:700 13px/1 var(--mono);color:var(--ink);margin-right:5px}
.strip{display:flex;gap:5px;flex-wrap:wrap}
.sc{display:inline-flex;align-items:center;gap:5px;border:1px solid var(--line);border-radius:6px;
  padding:2px 7px;font-size:11px}
.sc b{font:700 12px/1 var(--mono)}
.sc em{font-style:normal;color:var(--mute);font-size:10.5px}
.sc i{font-style:normal;font-size:10px;font-weight:700;padding:0 4px;border-radius:3px}
.fl-harm{background:var(--bad-bg);color:var(--bad)}
.fl-defer{background:var(--defer-bg);color:var(--defer)}
.sc.top b{color:var(--good)} .sc.bad b{color:var(--bad)} .sc.low b{color:var(--mute)}
.stat{margin:0;font:500 11px/1 var(--mono);color:var(--mute)}
.arm .body{font-size:13px;line-height:1.72;white-space:pre-wrap;color:var(--ink);
  border-left:2px solid var(--line);padding-left:11px}
.why{margin:0;font-size:12px;line-height:1.62;color:var(--mid);background:var(--sunk);
  border-radius:7px;padding:9px 11px}
.why span{display:block;font:600 10px/1 var(--mono);letter-spacing:.09em;text-transform:uppercase;
  color:var(--mute);margin-bottom:3px}

.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:var(--mute)}
.legend b{color:var(--ink);font-weight:600}
footer{color:var(--mute);font-size:12.5px;line-height:1.75;border-top:1px solid var(--line);
  padding-top:18px}
footer code{font:500 12px/1 var(--mono)}
a{color:var(--accent)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:3px}
@media (max-width:720px){h1{font-size:25px}.wrap{padding:0 15px 64px}}
"""


def main() -> None:
    rows, grades, ev = load()
    legend = "".join(
        f"<span><b>{esc(code)}</b> {esc(name)} — {esc(desc)}</span>"
        for _, code, name, desc in ARMS
    )
    blocks = "".join(question_block(r, grades, ev) for r in rows)

    OUT.write_text(f"""<title>정답 10건 채점 비교 — 위키 vs RAG</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<style>{CSS}</style>
<div class=wrap>
<header class=top>
  <span class=kicker>봇 11 · 테스트 봇 D-1 ver2 · 2026-08-09</span>
  <h1>관리자 정답 10건에 8개 방식은 각각 뭐라고 답했나</h1>
  <p class=cond><code>gemini-3.5-flash-lite</code> · 온도 0.3 · max_tokens 2048 ·
  같은 system_prompt(1,341자) · 같은 근거 지시 문구. <b>다른 것은 근거를 무엇으로 주느냐 하나다.</b>
  내용 점수는 codex 눈가림 채점(갑/을/병… 라벨 + 문항별 순서 셔플), <code>fact+cover+harm</code> 로
  −2 ~ +4.</p>
</header>

<div class=panel>
  <h2>먼저 읽을 것 — 이 점수들은 서열로만 읽어야 한다<span>같은 답을 세 번 채점했더니 점수가 팔 사이 격차만큼 움직였다</span></h2>
  {stability(grades)}
  <p>codex 판정은 <b>비교식</b>이다. 함께 놓인 답이 달라지면 절대값이 흔들린다.
  <b>F 는 회차에 따라 A 를 넘기도 하고(2.50 vs 2.00) 밑돌기도 한다(1.90 vs 2.30).</b>
  격차와 잡음이 같은 크기라 <b>n=10 으로는 A·F·G′ 를 가를 수 없다.</b>
  회차를 넘어 안정적인 것만 결론으로 쓸 수 있다.</p>
  <div class=finding>
    <div><b>C 위키 본문은 항상 최하위권</b><span>세 회차 모두. 위키 본문만으로 답하는 배치는 기각된다.</span></div>
    <div><b>이어 붙이기는 항상 유해 최다</b><span>5건·6건. 오류가 합집합이 되고 한 답 안에서 앞뒤가 어긋난다.</span></div>
    <div><b>B·B′ 는 유해가 가장 적다</b><span>세 회차 모두 1건. 팔 A 는 3~4건. 어휘 검색이 틀린 사실을 덜 주입한다.</span></div>
    <div><b>진짜 병목은 정답지</b><span>관리자 회신이 10/45 다. 표본을 늘리기 전에는 이 격차들을 판정할 수 없다.</span></div>
  </div>
</div>

<div class=panel>
  <h2>문항 × 방식 총점<span>✕ 유해 안내 · ○ 유보(확인되지 않습니다 + 담당자 연결) · 대표 점수는 가장 최근 회차</span></h2>
  {matrix(rows, grades, ev)}
  <p>코퍼스 근거 = 정답의 근거가 규정집v20 + 대사전v4(원문 250건) 안에 있는가.
  10건 중 <b>#20 하나만 「없음」</b>이다 — 은사축복식 참석 시점과 임신 시점으로 자녀 세대를 가르는
  기준이 코퍼스 어디에도 없다. 정답지 시트 ① 「"확인되지 않습니다 + 담당자 연결"만 해도 정답인가」는
  <b>45/45 전부 "예"</b> 이고, 45문항 중 위험도 '상' 이 28건이다. 틀린 답보다 유보가 나은 판이다.</p>
  <div class=legend>{legend}</div>
</div>

{blocks}

<footer>
  생성 <code>exports/wiki_eval/_golden_report.py</code> ·
  원자료 <code>answers.json</code> · 채점 <code>grades_5arm.json</code> ·
  <code>grades.json</code> · <code>grades_fusion.json</code> ·
  근거 라벨 <code>corpus_evidence.json</code><br>
  45문항 키워드 자 비교는 <code>report.html</code>, 배경과 함정은
  <code>docs/architecture/handoff-wiki-retrieval-2026-08-08.md</code>.
</footer>
</div>
""", encoding="utf-8")
    print(f"→ {OUT}  ({len(rows)}문항 × {len(ARMS)}방식)")


if __name__ == "__main__":
    main()
