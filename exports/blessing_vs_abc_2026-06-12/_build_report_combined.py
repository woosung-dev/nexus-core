# 블레싱 나 v1 vs v2 vs A/B/C 통합 보고서 — 프롬프트 개선(v1→v2) 효과를 이중 평가로 검증
import html
import json
from datetime import date
from pathlib import Path

DIR = Path("/Users/woosung/project/agy-project/nexus-core/exports/blessing_vs_abc_2026-06-12")
OUT = Path("/Users/woosung/Downloads") / f"블레싱_나_v1v2_vs_ABC_통합_{date.today()}.html"
USERS = ["조화연", "신은비", "김소영"]
AGENT_OF = {"조화연": "redteam-johwayeon", "신은비": "redteam-shineunbi", "김소영": "redteam-kimsoyoung"}
WIN_TO_LETTER = {"통합": "A", "원리": "B", "정밀": "C"}


def esc(s):
    return html.escape(str(s if s is not None else ""))


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


# 데이터 로드 — v1/v2 데이터셋, 평가
ds_v1 = {u: json.load(open(DIR / f"dataset_{u}.json")) for u in USERS}
ds_v2 = {u: json.load(open(DIR / f"dataset_{u}_v2.json")) for u in USERS}


def eval_index(agent_path, codex_prefix):
    araw = load(agent_path) or []
    a_by_user = {e["user"]: {r["qid"]: r for r in e["eval"]["results"]} for e in araw if e and e.get("eval")}
    a_sum = {e["user"]: e["eval"]["summary"] for e in araw if e and e.get("eval")}
    c_by_user, c_sum = {}, {}
    for u in USERS:
        ce = load(DIR / f"{codex_prefix}{u}.json")
        if ce:
            c_by_user[u] = {r["qid"]: r for r in ce.get("results", [])}
            c_sum[u] = ce.get("summary", {})
    return a_by_user, a_sum, c_by_user, c_sum


a1, a1s, c1, c1s = eval_index(DIR / "agent_eval.json", "codex_eval_")
a2, a2s, c2, c2s = eval_index(DIR / "agent_eval_v2.json", "codex_eval_v2_")


def vs_pill(v):
    m = {"win": ("우세", "pwin"), "tie": ("비슷", "ptie"), "lose": ("열세", "plose")}
    t, c = m.get(v, ("-", "ptie"))
    return f'<span class="pill {c}">{t}</span>'


def best_pill(b):
    cls = "pbless" if b == "블레싱" else ("pbad" if b == "모두부적절" else "pabc")
    return f'<span class="pill {cls}">{esc(b)}</span>'


def sc_html(sc):
    if not sc:
        return '<span class="muted">-</span>'
    out = []
    for k, lab in [("A", "A"), ("B", "B"), ("C", "C"), ("blessing", "블레싱")]:
        v = sc.get(k, "-")
        hi = "shi" if isinstance(v, int) and v >= 4 else ("slo" if isinstance(v, int) and v <= 2 else "")
        out.append(f'<span class="sc {hi}"><b>{lab}</b> {v}</span>')
    return " ".join(out)


def eval_block(ev, label):
    if not ev:
        return f'<div class="evb"><div class="evh">{label}</div><div class="muted">평가 없음</div></div>'
    iss = "".join(f"<li>{esc(i)}</li>" for i in (ev.get("blessing_issues") or [])) or '<li class="muted">없음</li>'
    return (f'<div class="evb"><div class="evh">{label} · best {best_pill(ev.get("best"))} · {vs_pill(ev.get("blessing_vs_tester"))}</div>'
            f'<div class="scl">{sc_html(ev.get("scores"))}</div>'
            f'<div class="cmt">{esc(ev.get("comment"))}</div>'
            f'<div class="isl"><b>지적</b><ul>{iss}</ul></div></div>')


def bscore(ev):
    return ev.get("scores", {}).get("blessing") if ev else None


# 사용자 섹션
sections, agg_rows = [], []
for u in USERS:
    items_v1 = {it["qid"]: it for it in ds_v1[u]["items"]}
    items_v2 = {it["qid"]: it for it in ds_v2[u]["items"]}

    def srow(label, s):
        return (f'<tr><td>{label}</td><td>{s.get("blessing_best_count","-")}</td>'
                f'<td>{s.get("blessing_win_count","-")}</td><td>{s.get("blessing_lose_count","-")}</td></tr>')
    agg_rows.append(f"""<div class="ucard">
      <div class="ut">{esc(u)} <span class="uag">{esc(AGENT_OF[u])}</span></div>
      <table class="agg"><tr><th>평가/버전</th><th>best</th><th>우세</th><th>열세</th></tr>
        {srow("페르소나 v1", a1s.get(u,{}))}{srow("페르소나 <b>v2</b>", a2s.get(u,{}))}
        {srow("codex v1", c1s.get(u,{}))}{srow("codex <b>v2</b>", c2s.get(u,{}))}
      </table>
      <div class="verd"><b>페르소나 v2 결론</b> {esc(a2s.get(u,{}).get("verdict"))}</div>
      <div class="verd"><b>codex v2 결론</b> {esc(c2s.get(u,{}).get("verdict"))}</div>
    </div>""")

    rows = []
    for qid in items_v1:
        it1, it2 = items_v1[qid], items_v2.get(qid, {})
        ae1, ce1 = a1.get(u, {}).get(qid), c1.get(u, {}).get(qid)
        ae2, ce2 = a2.get(u, {}).get(qid), c2.get(u, {}).get(qid)
        tester = WIN_TO_LETTER.get(it1.get("tester_win"), it1.get("tester_choice"))
        # v1→v2 블레싱 점수 변화(두 평가자 평균)
        def avg(*xs):
            xs = [x for x in xs if isinstance(x, int)]
            return sum(xs) / len(xs) if xs else None
        b1, b2 = avg(bscore(ae1), bscore(ce1)), avg(bscore(ae2), bscore(ce2))
        delta = ""
        if b1 is not None and b2 is not None:
            d = b2 - b1
            cls = "dup" if d > 0.4 else ("ddn" if d < -0.4 else "dmid")
            arrow = "▲" if d > 0.4 else ("▼" if d < -0.4 else "＝")
            delta = f'<span class="delta {cls}">{arrow} {b1:.1f}→{b2:.1f}</span>'
        c_v1 = it1.get("blessing_citations") or []
        c_v2 = it2.get("blessing_citations") or []
        rows.append(f"""<details class="q">
        <summary>
          <span class="qid">{esc(qid)}</span><span class="qt">{esc(it1.get('qtype'))}</span>
          <span class="qq">{esc(it1['q'][:62])}</span>
          <span class="qmeta">테스터→<b>{esc(tester)}</b> {delta}</span>
        </summary>
        <div class="qbody">
          <div class="qfull"><b>질문</b> {esc(it1['q'])}</div>
          <div class="ans"><div class="al">A · 통합</div><div class="at">{esc(it1.get('ansA_통합'))}</div></div>
          <div class="ans"><div class="al">B · 원리</div><div class="at">{esc(it1.get('ansB_원리'))}</div></div>
          <div class="ans"><div class="al">C · 정밀</div><div class="at">{esc(it1.get('ansC_정밀'))}</div></div>
          <div class="ans blessv1"><div class="al">블레싱 v1 (이전) <span class="cite">인용: {esc(', '.join(dict.fromkeys(c_v1)) or '없음')}</span></div><div class="at">{esc(it1.get('blessing_answer'))}</div></div>
          <div class="ans blessv2"><div class="al">★ 블레싱 v2 (신규 프롬프트) <span class="cite">인용: {esc(', '.join(dict.fromkeys(c_v2)) or '없음')}</span></div><div class="at">{esc(it2.get('blessing_answer'))}</div></div>
          <div class="tf"><b>테스터({esc(u)}) 원선택</b> {esc(tester)} · <b>당시 피드백</b> {esc(it1.get('tester_feedback'))}</div>
          <div class="vlabel">v1 평가</div>
          <div class="evgrid">{eval_block(ae1,'페르소나')}{eval_block(ce1,'codex')}</div>
          <div class="vlabel v2l">v2 평가 (신규 프롬프트)</div>
          <div class="evgrid">{eval_block(ae2,'페르소나')}{eval_block(ce2,'codex')}</div>
        </div>
      </details>""")
    sections.append(f'<section class="usec" data-user="{esc(u)}"><h2>{esc(u)} — 30문항</h2>{"".join(rows)}</section>')


def tot(sums, k):
    vs = [s.get(k, 0) for s in sums.values() if isinstance(s.get(k), int)]
    return sum(vs) if vs else 0


def card(title, a_sum, c_sum):
    return (f'<div class="vcard"><div class="vt">{title}</div>'
            f'<div class="vr">페르소나 — best <b>{tot(a_sum,"blessing_best_count")}</b>/90 · 우세 {tot(a_sum,"blessing_win_count")} · 열세 {tot(a_sum,"blessing_lose_count")}</div>'
            f'<div class="vr">codex — best <b>{tot(c_sum,"blessing_best_count")}</b>/90 · 우세 {tot(c_sum,"blessing_win_count")} · 열세 {tot(c_sum,"blessing_lose_count")}</div></div>')


# v1→v2 전체 델타
def delta_line():
    pa = tot(a2s, "blessing_best_count") - tot(a1s, "blessing_best_count")
    pc = tot(c2s, "blessing_best_count") - tot(c1s, "blessing_best_count")
    sign = lambda x: f"+{x}" if x > 0 else str(x)
    return f'페르소나 best {sign(pa)} · codex best {sign(pc)} (v1→v2)'


HTML = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>블레싱 나 v1 vs v2 vs A/B/C 통합 — {date.today()}</title>
<style>
:root{{--ink:#1A2233;--sub:#5A6678;--line:#E5E9F0;--bg:#F6F8FB;--card:#fff;--accent:#9333EA;--v2:#0D9488;--ok:#16A34A;--warn:#D97706;--bad:#DC2626;}}
*{{box-sizing:border-box;}}body{{margin:0;font-family:-apple-system,'Pretendard','Apple SD Gothic Neo',sans-serif;background:var(--bg);color:var(--ink);line-height:1.6;}}
.wrap{{max-width:1100px;margin:0 auto;padding:36px 22px 90px;}}
header{{border-bottom:3px solid var(--accent);padding-bottom:16px;}}
.eyebrow{{color:var(--accent);font-weight:700;font-size:13px;letter-spacing:.06em;}}
h1{{margin:6px 0 4px;font-size:25px;}}h2{{font-size:18px;margin:30px 0 12px;border-left:4px solid var(--accent);padding-left:10px;}}
.meta{{color:var(--sub);font-size:13.5px;}}
.deltabar{{margin:16px 0;padding:14px 18px;border-radius:12px;background:#ECFDF5;border:1px solid #A7F3D0;font-size:15px;font-weight:700;color:#065F46;}}
.vcards{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:14px 0;}}
.vcard{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;}}
.vcard .vt{{font-weight:800;font-size:15px;margin-bottom:8px;}}.vcard .vr{{font-size:13px;color:#2A3344;}}
.ucards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px;}}
.ucard{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;}}
.ut{{font-weight:800;font-size:16px;margin-bottom:8px;}}.uag{{font-size:11px;color:var(--sub);font-weight:500;}}
table.agg{{width:100%;border-collapse:collapse;font-size:13px;margin-bottom:8px;}}
table.agg th,table.agg td{{text-align:left;padding:5px 7px;border-bottom:1px solid var(--line);}}
table.agg th{{color:var(--sub);font-size:11.5px;}}
.verd{{font-size:12px;color:var(--sub);margin-top:5px;}}.verd b{{color:var(--ink);}}
.filter{{margin:18px 0 6px;}}.filter button{{padding:7px 14px;border:1px solid var(--line);background:#fff;border-radius:9px;font-size:13px;cursor:pointer;margin-right:6px;}}
.filter button.on{{background:var(--accent);color:#fff;border-color:var(--accent);}}
details.q{{background:var(--card);border:1px solid var(--line);border-radius:12px;margin-bottom:9px;overflow:hidden;}}
details.q summary{{cursor:pointer;padding:11px 14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:13.5px;list-style:none;}}
details.q summary::-webkit-details-marker{{display:none;}}
.qid{{font-weight:800;color:var(--accent);font-size:12px;}}.qt{{font-size:11px;color:var(--sub);background:#F1F3F8;padding:1px 7px;border-radius:999px;}}
.qq{{flex:1 1 240px;}}.qmeta{{font-size:11.5px;color:var(--sub);}}
.delta{{font-weight:800;padding:1px 8px;border-radius:999px;margin-left:6px;font-size:11.5px;}}
.delta.dup{{background:#DCFCE7;color:#166534;}}.delta.ddn{{background:#FEE2E2;color:#991B1B;}}.delta.dmid{{background:#F1F3F8;color:#475569;}}
.qbody{{padding:6px 16px 16px;border-top:1px solid var(--line);}}
.qfull{{font-size:13.5px;margin:10px 0;}}
.ans{{margin:8px 0;border:1px solid var(--line);border-radius:9px;overflow:hidden;}}
.ans .al{{background:#F1F3F8;padding:5px 10px;font-size:12px;font-weight:700;}}
.ans.blessv1 .al{{background:#EEF2FF;color:#3730A3;}}
.ans.blessv2 .al{{background:#CCFBF1;color:#0F766E;}}
.ans .at{{padding:9px 12px;font-size:13px;white-space:pre-wrap;color:#2A3344;}}
.cite{{font-weight:500;color:var(--sub);font-size:11px;margin-left:6px;}}
.tf{{font-size:12.5px;background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;padding:8px 11px;margin:10px 0;}}
.vlabel{{font-weight:800;font-size:12.5px;margin:12px 0 4px;color:var(--accent);}}.vlabel.v2l{{color:var(--v2);}}
.evgrid{{display:grid;grid-template-columns:1fr 1fr;gap:10px;}}
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
@media(max-width:680px){{.evgrid,.vcards{{grid-template-columns:1fr;}}}}
</style></head><body><div class="wrap">
<header>
  <div class="eyebrow">REDTEAM · 블레싱 나 프롬프트 v1 → v2 개선 검증</div>
  <h1>블레싱 나 v1 vs v2 vs A·B·C 통합</h1>
  <div class="meta">조화연·신은비·김소영 각 30문항(총 90) · 블레싱 나 프롬프트 v1(6,730자)·v2(9,933자) 동일 질문 재질의 · 페르소나 에이전트 + codex 이중 평가 · {date.today()}</div>
</header>
<div class="deltabar">📈 v1 → v2 변화 — {delta_line()} · 문항별 ▲/▼는 두 평가자 평균 블레싱 점수 변화</div>
<div class="vcards">{card("블레싱 v1 (이전)", a1s, c1s)}{card("블레싱 v2 (신규 프롬프트)", a2s, c2s)}</div>
<h2>사용자별 v1 vs v2 집계</h2>
<div class="ucards">{"".join(agg_rows)}</div>
<div class="filter"><button class="on" data-f="all">전체</button>
  <button data-f="조화연">조화연</button><button data-f="신은비">신은비</button><button data-f="김소영">김소영</button></div>
{"".join(sections)}
<div class="note"><b>방법</b> · A/B/C = 2주차 레드팀 3봇(통합/원리/정밀) 고정 답변. 블레싱 v1·v2 = 같은 봇(id=3)을 프롬프트만 v1→v2로 바꿔 동일 90문항에 운영동일 파라미터로 재질의한 답변. 평가는 페르소나 레드팀 에이전트(Claude)와 codex(독립 LLM)가 동일 루브릭·도메인 정답기준으로 v1·v2 각각 독립 수행. 문항 헤더의 ▲/▼는 두 평가자 평균 블레싱 점수의 v1→v2 변화.</div>
</div>
<script>
const btns=document.querySelectorAll('.filter button');
btns.forEach(b=>b.onclick=()=>{{btns.forEach(x=>x.classList.remove('on'));b.classList.add('on');
const f=b.dataset.f;document.querySelectorAll('.usec').forEach(s=>{{s.style.display=(f==='all'||s.dataset.user===f)?'':'none';}});}});
</script>
</body></html>"""

OUT.write_text(HTML, encoding="utf-8")
print(f"통합 보고서 저장: {OUT}")
print("v1→v2:", delta_line())
