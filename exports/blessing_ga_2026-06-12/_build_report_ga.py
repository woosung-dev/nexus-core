# 블레싱 가 vs A/B/C 비교 보고서 — 페르소나 에이전트 + codex 이중 평가를 단일 HTML로
import html
import json
from datetime import date
from pathlib import Path

DIR = Path("/Users/woosung/project/agy-project/nexus-core/exports/blessing_ga_2026-06-12")
OUT = Path("/Users/woosung/Downloads") / f"블레싱_가_vs_ABC_레드팀비교_{date.today()}.html"
USERS = ["미야자키시호", "김소영", "조화연"]
AGENT_OF = {"미야자키시호": "redteam-miyazakishiho", "김소영": "redteam-kimsoyoung", "조화연": "redteam-johwayeon"}
WIN_TO_LETTER = {"통합": "A", "원리": "B", "정밀": "C"}


def esc(s):
    return html.escape(str(s or ""))


def load_eval(path):
    try:
        return json.load(open(path))
    except Exception:
        return None


# 데이터 로드
datasets = {u: json.load(open(DIR / f"dataset_{u}.json")) for u in USERS}

# 에이전트 평가: agent_eval.json = [{user, agent, eval}] (eval 가 스키마 객체)
agent_raw = load_eval(DIR / "agent_eval.json") or []
agent_eval = {}
for e in agent_raw:
    if e and e.get("eval"):
        agent_eval[e["user"]] = {r["qid"]: r for r in e["eval"].get("results", [])}
agent_summary = {e["user"]: e["eval"].get("summary", {}) for e in agent_raw if e and e.get("eval")}

# codex 평가: codex_eval_{user}.json
codex_eval, codex_summary = {}, {}
for u in USERS:
    ce = load_eval(DIR / f"codex_eval_{u}.json")
    if ce:
        codex_eval[u] = {r["qid"]: r for r in ce.get("results", [])}
        codex_summary[u] = ce.get("summary", {})


def vs_pill(v):
    m = {"win": ("블레싱 우세", "pwin"), "tie": ("비슷", "ptie"), "lose": ("기존 우세", "plose")}
    t, c = m.get(v, ("-", "ptie"))
    return f'<span class="pill {c}">{t}</span>'


def best_pill(b):
    cls = "pbless" if b == "블레싱" else ("pbad" if b == "모두부적절" else "pabc")
    return f'<span class="pill {cls}">{esc(b)}</span>'


def scores_html(sc):
    if not sc:
        return '<span class="muted">-</span>'
    cells = []
    for k, lab in [("A", "A"), ("B", "B"), ("C", "C"), ("blessing", "블레싱")]:
        v = sc.get(k, "-")
        hi = "shi" if (isinstance(v, int) and v >= 4) else ("slo" if (isinstance(v, int) and v <= 2) else "")
        cells.append(f'<span class="sc {hi}"><b>{lab}</b> {v}</span>')
    return " ".join(cells)


def eval_block(ev, label):
    if not ev:
        return f'<div class="evb"><div class="evh">{label}</div><div class="muted">평가 없음</div></div>'
    issues = ev.get("blessing_issues") or []
    iss = "".join(f"<li>{esc(i)}</li>" for i in issues) or '<li class="muted">없음</li>'
    return f"""<div class="evb">
      <div class="evh">{label} · best {best_pill(ev.get('best'))} · {vs_pill(ev.get('blessing_vs_tester'))}</div>
      <div class="scl">{scores_html(ev.get('scores'))}</div>
      <div class="cmt">{esc(ev.get('comment'))}</div>
      <div class="isl"><b>블레싱 지적</b><ul>{iss}</ul></div>
    </div>"""


# 사용자 섹션 렌더
sections = []
agg_cards = []
for u in USERS:
    items = datasets[u]["items"]
    asum = agent_summary.get(u, {})
    csum = codex_summary.get(u, {})

    # 집계 카드
    def num(d, k):
        return d.get(k, "-")
    agg_cards.append(f"""<div class="ucard">
      <div class="ut">{esc(u)} <span class="uag">{esc(AGENT_OF[u])}</span></div>
      <table class="agg">
        <tr><th></th><th>에이전트</th><th>codex</th></tr>
        <tr><td>블레싱 최우수</td><td>{num(asum,'blessing_best_count')}/30</td><td>{num(csum,'blessing_best_count')}/30</td></tr>
        <tr><td>기존 선택 대비 우세</td><td>{num(asum,'blessing_win_count')}</td><td>{num(csum,'blessing_win_count')}</td></tr>
        <tr><td>기존 선택이 우세</td><td>{num(asum,'blessing_lose_count')}</td><td>{num(csum,'blessing_lose_count')}</td></tr>
      </table>
      <div class="verd"><b>에이전트 결론</b> {esc(asum.get('verdict'))}</div>
      <div class="verd"><b>codex 결론</b> {esc(csum.get('verdict'))}</div>
    </div>""")

    rows = []
    for it in items:
        qid = it["qid"]
        ae = agent_eval.get(u, {}).get(qid)
        ce = codex_eval.get(u, {}).get(qid)
        tester_letter = WIN_TO_LETTER.get(it.get("tester_win"), it.get("tester_choice"))
        cites = it.get("blessing_citations") or []
        cite_str = ", ".join(dict.fromkeys(cites)) if cites else "없음"
        # 요약 헤더
        ab = best_pill(ae["best"]) if ae else ""
        cb = best_pill(ce["best"]) if ce else ""
        rows.append(f"""<details class="q">
        <summary>
          <span class="qid">{esc(qid)}</span>
          <span class="qt">{esc(it.get('qtype'))}</span>
          <span class="qq">{esc(it['q'][:70])}</span>
          <span class="qmeta">테스터→<b>{esc(tester_letter)}</b> · 에이전트 {ab} · codex {cb}</span>
        </summary>
        <div class="qbody">
          <div class="qfull"><b>질문</b> {esc(it['q'])}</div>
          <div class="ans"><div class="al">A · 통합</div><div class="at">{esc(it.get('ansA_통합'))}</div></div>
          <div class="ans"><div class="al">B · 원리</div><div class="at">{esc(it.get('ansB_원리'))}</div></div>
          <div class="ans"><div class="al">C · 정밀</div><div class="at">{esc(it.get('ansC_정밀'))}</div></div>
          <div class="ans bless"><div class="al">★ 블레싱 가 (신규) <span class="cite">인용: {esc(cite_str)}</span></div><div class="at">{esc(it.get('blessing_answer'))}</div></div>
          <div class="tf"><b>테스터 원선택</b> {esc(tester_letter)} · <b>당시 피드백</b> {esc(it.get('tester_feedback'))}</div>
          <div class="evgrid">{eval_block(ae,'페르소나 에이전트')}{eval_block(ce,'codex')}</div>
        </div>
      </details>""")
    sections.append(f'<section class="usec" data-user="{esc(u)}"><h2>{esc(u)} — 30문항</h2>{"".join(rows)}</section>')

# 전체 집계
def total(summaries, k):
    vals = [s.get(k, 0) for s in summaries.values() if isinstance(s.get(k), int)]
    return sum(vals) if vals else "-"

a_best = total(agent_summary, "blessing_best_count")
a_win = total(agent_summary, "blessing_win_count")
a_lose = total(agent_summary, "blessing_lose_count")
c_best = total(codex_summary, "blessing_best_count")
c_win = total(codex_summary, "blessing_win_count")
c_lose = total(codex_summary, "blessing_lose_count")

HTML = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>블레싱 가 vs A/B/C — 레드팀 비교 ({date.today()})</title>
<style>
:root{{--ink:#1A2233;--sub:#5A6678;--line:#E5E9F0;--bg:#F6F8FB;--card:#fff;--accent:#9333EA;--ok:#16A34A;--warn:#D97706;--bad:#DC2626;}}
*{{box-sizing:border-box;}}body{{margin:0;font-family:-apple-system,'Pretendard','Apple SD Gothic Neo',sans-serif;background:var(--bg);color:var(--ink);line-height:1.6;}}
.wrap{{max-width:1080px;margin:0 auto;padding:36px 22px 90px;}}
header{{border-bottom:3px solid var(--accent);padding-bottom:16px;}}
.eyebrow{{color:var(--accent);font-weight:700;font-size:13px;letter-spacing:.06em;}}
h1{{margin:6px 0 4px;font-size:26px;}}h2{{font-size:19px;margin:34px 0 12px;border-left:4px solid var(--accent);padding-left:10px;}}
.meta{{color:var(--sub);font-size:13.5px;}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:20px 0;}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:13px;padding:14px 16px;}}
.card .big{{font-size:24px;font-weight:800;}}.card .lab{{font-size:12px;color:var(--sub);}}
.card .sub2{{font-size:12px;color:var(--sub);margin-top:3px;}}
.ucards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;margin:14px 0 8px;}}
.ucard{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;}}
.ut{{font-weight:800;font-size:16px;margin-bottom:8px;}}.uag{{font-size:11px;color:var(--sub);font-weight:500;}}
table.agg{{width:100%;border-collapse:collapse;font-size:13px;margin-bottom:8px;}}
table.agg th,table.agg td{{text-align:left;padding:5px 6px;border-bottom:1px solid var(--line);}}
table.agg th{{color:var(--sub);font-size:11.5px;}}
.verd{{font-size:12.5px;color:var(--sub);margin-top:5px;}}.verd b{{color:var(--ink);}}
.filter{{margin:18px 0 6px;}}.filter button{{padding:7px 14px;border:1px solid var(--line);background:#fff;border-radius:9px;font-size:13px;cursor:pointer;margin-right:6px;}}
.filter button.on{{background:var(--accent);color:#fff;border-color:var(--accent);}}
details.q{{background:var(--card);border:1px solid var(--line);border-radius:12px;margin-bottom:9px;overflow:hidden;}}
details.q summary{{cursor:pointer;padding:11px 14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:13.5px;list-style:none;}}
details.q summary::-webkit-details-marker{{display:none;}}
.qid{{font-weight:800;color:var(--accent);font-size:12px;flex:0 0 auto;}}
.qt{{font-size:11px;color:var(--sub);background:#F1F3F8;padding:1px 7px;border-radius:999px;}}
.qq{{flex:1 1 280px;color:var(--ink);}}
.qmeta{{font-size:11.5px;color:var(--sub);}}
.qbody{{padding:6px 16px 16px;border-top:1px solid var(--line);}}
.qfull{{font-size:13.5px;margin:10px 0;}}
.ans{{margin:8px 0;border:1px solid var(--line);border-radius:9px;overflow:hidden;}}
.ans .al{{background:#F1F3F8;padding:5px 10px;font-size:12px;font-weight:700;}}
.ans.bless .al{{background:#F3E8FF;color:#6B21A8;}}
.ans .at{{padding:9px 12px;font-size:13px;white-space:pre-wrap;color:#2A3344;}}
.cite{{font-weight:500;color:var(--sub);font-size:11px;margin-left:6px;}}
.tf{{font-size:12.5px;background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;padding:8px 11px;margin:10px 0;}}
.evgrid{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px;}}
.evb{{border:1px solid var(--line);border-radius:9px;padding:10px 12px;background:#FCFDFF;}}
.evh{{font-size:12.5px;font-weight:700;margin-bottom:6px;}}
.scl{{margin:4px 0;}}.sc{{display:inline-block;font-size:11.5px;padding:1px 7px;border-radius:6px;background:#F1F3F8;margin-right:4px;}}
.sc.shi{{background:#DCFCE7;color:#166534;}}.sc.slo{{background:#FEE2E2;color:#991B1B;}}
.cmt{{font-size:12.5px;color:#2A3344;margin:5px 0;}}
.isl{{font-size:12px;margin-top:4px;}}.isl ul{{margin:3px 0 0;padding-left:18px;}}.isl li{{color:#991B1B;}}
.pill{{display:inline-block;padding:1px 8px;border-radius:999px;font-size:11px;font-weight:700;}}
.pwin{{background:#DCFCE7;color:#166534;}}.ptie{{background:#F1F3F8;color:#475569;}}.plose{{background:#FEE2E2;color:#991B1B;}}
.pbless{{background:#F3E8FF;color:#6B21A8;}}.pabc{{background:#E0E7FF;color:#3730A3;}}.pbad{{background:#FEE2E2;color:#991B1B;}}
.muted{{color:#9AA5B5;}}
.note{{font-size:12.5px;color:var(--sub);background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-top:16px;}}
@media(max-width:680px){{.evgrid{{grid-template-columns:1fr;}}}}
</style></head><body><div class="wrap">
<header>
  <div class="eyebrow">REDTEAM · 신규봇 비교 검증</div>
  <h1>블레싱 가 vs A(통합)·B(원리)·C(정밀)</h1>
  <div class="meta">조화연·신은비·김소영 2주차 레드팀 질문 각 30문항(총 90) · 신규 봇 "블레싱 가"(bot id=5, gemini-3.1-flash-lite) 재질의 · 페르소나 에이전트 + codex 이중 평가 · {date.today()}</div>
</header>
<div class="cards">
  <div class="card"><div class="big">90</div><div class="lab">비교 질문</div></div>
  <div class="card"><div class="big">{a_best} / {c_best}</div><div class="lab">블레싱 최우수 (에이전트/codex)</div><div class="sub2">90문항 중</div></div>
  <div class="card"><div class="big">{a_win} / {c_win}</div><div class="lab">기존선택 대비 우세</div><div class="sub2">에이전트 / codex</div></div>
  <div class="card"><div class="big">{a_lose} / {c_lose}</div><div class="lab">기존선택이 우세</div><div class="sub2">에이전트 / codex</div></div>
</div>
<h2>사용자별 집계</h2>
<div class="ucards">{"".join(agg_cards)}</div>
<div class="filter">
  <button class="on" data-f="all">전체</button>
  <button data-f="조화연">조화연</button>
  <button data-f="신은비">신은비</button>
  <button data-f="김소영">김소영</button>
</div>
{"".join(sections)}
<div class="note"><b>방법</b> · A/B/C = 2주차 레드팀에서 테스터가 본 3개 봇(통합/원리/정밀) 답변(고정). 블레싱 가 = 신규 봇(bot id=5)을 동일 질문에 운영동일 파라미터(generate_with_rag, max_tokens=2048)로 재질의한 새 답변. 평가는 (1) 각 테스터의 페르소나 레드팀 에이전트(Claude)와 (2) codex(독립 LLM)가 동일 루브릭·도메인 정답기준으로 독립 수행. blessing_vs_tester 는 테스터가 당시 고른 답변 대비 블레싱의 우열.</div>
</div>
<script>
const btns=document.querySelectorAll('.filter button');
btns.forEach(b=>b.onclick=()=>{{
  btns.forEach(x=>x.classList.remove('on'));b.classList.add('on');
  const f=b.dataset.f;
  document.querySelectorAll('.usec').forEach(s=>{{s.style.display=(f==='all'||s.dataset.user===f)?'':'none';}});
}});
</script>
</body></html>"""

OUT.write_text(HTML, encoding="utf-8")
print(f"보고서 저장: {OUT}")
print(f"전체: 블레싱 최우수 에이전트 {a_best}/codex {c_best}, 우세 {a_win}/{c_win}, 열세 {a_lose}/{c_lose}")
