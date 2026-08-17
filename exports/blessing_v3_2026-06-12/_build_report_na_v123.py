# 블레싱 나 v1·v2·v3 vs A/B/C 통합 — 프롬프트 3세대 개선 추이를 이중 평가로
import html, json
from datetime import date
from pathlib import Path

NA = Path("/Users/woosung/project/agy-project/nexus-core/exports/blessing_vs_abc_2026-06-12")
V3 = Path("/Users/woosung/project/agy-project/nexus-core/exports/blessing_v3_2026-06-12")
OUT = Path("/Users/woosung/Downloads") / f"블레싱_나_v1v2v3_vs_ABC_{date.today()}.html"
USERS = ["조화연", "신은비", "김소영"]
AGENT_OF = {"조화연": "redteam-johwayeon", "신은비": "redteam-shineunbi", "김소영": "redteam-kimsoyoung"}
WL = {"통합": "A", "원리": "B", "정밀": "C"}


def esc(s): return html.escape(str(s if s is not None else ""))
def load(p):
    try: return json.load(open(p))
    except Exception: return None

# datasets
ds = {
  "v1": {u: json.load(open(NA/f"dataset_{u}.json")) for u in USERS},
  "v2": {u: json.load(open(NA/f"dataset_{u}_v2.json")) for u in USERS},
  "v3": {u: json.load(open(V3/f"dataset_나_{u}_v3.json")) for u in USERS},
}

def aidx(p):
    raw = load(p) or []
    return ({e["user"]: {r["qid"]: r for r in e["eval"]["results"]} for e in raw if e and e.get("eval")},
            {e["user"]: e["eval"]["summary"] for e in raw if e and e.get("eval")})
def cidx(folder, prefix, suffix=""):
    by, sm = {}, {}
    for u in USERS:
        ce = load(folder/f"{prefix}{u}{suffix}.json")
        if ce: by[u] = {r["qid"]: r for r in ce.get("results", [])}; sm[u] = ce.get("summary", {})
    return by, sm

A = {"v1": aidx(NA/"agent_eval.json"), "v2": aidx(NA/"agent_eval_v2.json"), "v3": aidx(V3/"agent_eval_나_v3.json")}
C = {"v1": cidx(NA, "codex_eval_"), "v2": cidx(NA, "codex_eval_v2_"), "v3": cidx(V3, "codex_나_", "_v3")}
VERS = ["v1", "v2", "v3"]

def vs_pill(v):
    m = {"win": ("우세", "pwin"), "tie": ("비슷", "ptie"), "lose": ("열세", "plose")}; t, c = m.get(v, ("-", "ptie"))
    return f'<span class="pill {c}">{t}</span>'
def best_pill(b):
    cls = "pbless" if b == "블레싱" else ("pbad" if b == "모두부적절" else "pabc")
    return f'<span class="pill {cls}">{esc(b)}</span>'
def sc_html(sc):
    if not sc: return '<span class="muted">-</span>'
    out = []
    for k, lab in [("A","A"),("B","B"),("C","C"),("blessing","블레싱")]:
        v = sc.get(k, "-"); hi = "shi" if isinstance(v,int) and v>=4 else ("slo" if isinstance(v,int) and v<=2 else "")
        out.append(f'<span class="sc {hi}"><b>{lab}</b> {v}</span>')
    return " ".join(out)
def eval_block(ev, label):
    if not ev: return f'<div class="evb"><div class="evh">{label}</div><div class="muted">평가 없음</div></div>'
    iss = "".join(f"<li>{esc(i)}</li>" for i in (ev.get("blessing_issues") or [])) or '<li class="muted">없음</li>'
    return (f'<div class="evb"><div class="evh">{label} · best {best_pill(ev.get("best"))} · {vs_pill(ev.get("blessing_vs_tester"))}</div>'
            f'<div class="scl">{sc_html(ev.get("scores"))}</div><div class="cmt">{esc(ev.get("comment"))}</div>'
            f'<div class="isl"><b>지적</b><ul>{iss}</ul></div></div>')
def bscore(ev): return (ev or {}).get("scores", {}).get("blessing")

# 집계
def tally(ver, mp_kind):
    # mp_kind: 'A'(persona) or 'C'(codex)
    src = A[ver][0] if mp_kind == "A" else C[ver][0]
    best = win = lose = 0
    for u in USERS:
        for r in src.get(u, {}).values():
            if r["best"] == "블레싱": best += 1
            if r["blessing_vs_tester"] == "win": win += 1
            if r["blessing_vs_tester"] == "lose": lose += 1
    return best, win, lose

agg = {ver: {"A": tally(ver, "A"), "C": tally(ver, "C")} for ver in VERS}

def vcard(ver, title):
    a, c = agg[ver]["A"], agg[ver]["C"]
    return (f'<div class="vcard"><div class="vt">{title}</div>'
            f'<div class="vr">페르소나 — best <b>{a[0]}</b>/90 · 우세 {a[1]} · 열세 {a[2]}</div>'
            f'<div class="vr">codex — best <b>{c[0]}</b>/90 · 우세 {c[1]} · 열세 {c[2]}</div></div>')

# 사용자 섹션
sections, ucards = [], []
for u in USERS:
    items = {it["qid"]: it for it in ds["v1"][u]["items"]}
    v2it = {it["qid"]: it for it in ds["v2"][u]["items"]}
    v3it = {it["qid"]: it for it in ds["v3"][u]["items"]}
    def urow(lbl, ver, kind):
        src = A[ver][1] if kind=="A" else C[ver][1]
        s = src.get(u, {})
        return f'<tr><td>{lbl}</td><td>{s.get("blessing_best_count","-")}</td><td>{s.get("blessing_win_count","-")}</td><td>{s.get("blessing_lose_count","-")}</td></tr>'
    # 결과레벨 사용자별
    def ucount(ver, kind):
        src = A[ver][0] if kind=="A" else C[ver][0]
        rs = src.get(u, {}).values()
        return (sum(1 for r in rs if r["best"]=="블레싱"), sum(1 for r in rs if r["blessing_vs_tester"]=="win"), sum(1 for r in rs if r["blessing_vs_tester"]=="lose"))
    rows_agg = ""
    for kind, kn in [("A","페르소나"),("C","codex")]:
        for ver in VERS:
            b,w,l = ucount(ver, kind)
            rows_agg += f'<tr><td>{kn} {ver}</td><td>{b}</td><td>{w}</td><td>{l}</td></tr>'
    ucards.append(f'<div class="ucard"><div class="ut">{esc(u)} <span class="uag">{esc(AGENT_OF[u])}</span></div>'
                  f'<table class="agg"><tr><th>평가/버전</th><th>best</th><th>우세</th><th>열세</th></tr>{rows_agg}</table></div>')

    rows = []
    for qid, it1 in items.items():
        it2, it3 = v2it.get(qid, {}), v3it.get(qid, {})
        tester = WL.get(it1.get("tester_win"), it1.get("tester_choice"))
        # 버전별 평균 블레싱 점수(페르소나+codex)
        def avg(ver):
            xs = [bscore(A[ver][0].get(u,{}).get(qid)), bscore(C[ver][0].get(u,{}).get(qid))]
            xs = [x for x in xs if isinstance(x,int)]
            return sum(xs)/len(xs) if xs else None
        trend = " → ".join(f"{avg(v):.1f}" if avg(v) is not None else "-" for v in VERS)
        d13 = (avg("v3") or 0) - (avg("v1") or 0)
        cls = "dup" if d13>0.4 else ("ddn" if d13<-0.4 else "dmid")
        arrow = "▲" if d13>0.4 else ("▼" if d13<-0.4 else "＝")
        def ansrow(it, lab, cls2):
            cites = it.get("blessing_citations") or []
            return f'<div class="ans {cls2}"><div class="al">{lab} <span class="cite">인용:{esc(", ".join(dict.fromkeys(cites)) or "없음")}</span></div><div class="at">{esc(it.get("blessing_answer"))}</div></div>'
        ev_rows = ""
        for ver, vn in [("v1","v1"),("v2","v2"),("v3","v3 (신규)")]:
            ae = A[ver][0].get(u,{}).get(qid); ce = C[ver][0].get(u,{}).get(qid)
            vcls = "v3l" if ver=="v3" else ""
            ev_rows += f'<div class="vlabel {vcls}">{vn} 평가</div><div class="evgrid">{eval_block(ae,"페르소나")}{eval_block(ce,"codex")}</div>'
        rows.append(f"""<details class="q">
        <summary><span class="qid">{esc(qid)}</span><span class="qt">{esc(it1.get('qtype'))}</span>
        <span class="qq">{esc(it1['q'][:58])}</span>
        <span class="qmeta">테스터→<b>{esc(tester)}</b> <span class="delta {cls}">{arrow} {trend}</span></span></summary>
        <div class="qbody">
          <div class="qfull"><b>질문</b> {esc(it1['q'])}</div>
          <div class="ans"><div class="al">A · 통합</div><div class="at">{esc(it1.get('ansA_통합'))}</div></div>
          <div class="ans"><div class="al">B · 원리</div><div class="at">{esc(it1.get('ansB_원리'))}</div></div>
          <div class="ans"><div class="al">C · 정밀</div><div class="at">{esc(it1.get('ansC_정밀'))}</div></div>
          {ansrow(it1,"블레싱 v1","blv1")}{ansrow(it2,"블레싱 v2","blv2")}{ansrow(it3,"★ 블레싱 v3 (신규)","blv3")}
          <div class="tf"><b>테스터({esc(u)}) 원선택</b> {esc(tester)} · <b>피드백</b> {esc(it1.get('tester_feedback'))}</div>
          {ev_rows}
        </div></details>""")
    sections.append(f'<section class="usec" data-user="{esc(u)}"><h2>{esc(u)} — 30문항</h2>{"".join(rows)}</section>')

def deltaline():
    sign = lambda x: f"+{x}" if x>0 else str(x)
    pa = agg["v3"]["A"][0]-agg["v1"]["A"][0]; ca = agg["v3"]["C"][0]-agg["v1"]["C"][0]
    pa2 = agg["v3"]["A"][0]-agg["v2"]["A"][0]; ca2 = agg["v3"]["C"][0]-agg["v2"]["C"][0]
    return f"v1→v3: 페르소나 best {sign(pa)} · codex best {sign(ca)}  |  v2→v3: 페르소나 {sign(pa2)} · codex {sign(ca2)}"

HTML = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>블레싱 나 v1·v2·v3 vs A/B/C — {date.today()}</title><style>
:root{{--ink:#1A2233;--sub:#5A6678;--line:#E5E9F0;--bg:#F6F8FB;--card:#fff;--accent:#9333EA;--v3:#0D9488;--bad:#DC2626;}}
*{{box-sizing:border-box;}}body{{margin:0;font-family:-apple-system,'Pretendard','Apple SD Gothic Neo',sans-serif;background:var(--bg);color:var(--ink);line-height:1.6;}}
.wrap{{max-width:1120px;margin:0 auto;padding:36px 22px 90px;}}
header{{border-bottom:3px solid var(--accent);padding-bottom:16px;}}.eyebrow{{color:var(--accent);font-weight:700;font-size:13px;}}
h1{{margin:6px 0 4px;font-size:25px;}}h2{{font-size:18px;margin:30px 0 12px;border-left:4px solid var(--accent);padding-left:10px;}}.meta{{color:var(--sub);font-size:13.5px;}}
.deltabar{{margin:16px 0;padding:14px 18px;border-radius:12px;background:#ECFDF5;border:1px solid #A7F3D0;font-size:15px;font-weight:700;color:#065F46;}}
.vcards{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:14px 0;}}
.vcard{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;}}.vcard .vt{{font-weight:800;margin-bottom:8px;}}.vcard .vr{{font-size:13px;color:#2A3344;}}
.ucards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;}}.ucard{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;}}
.ut{{font-weight:800;margin-bottom:8px;}}.uag{{font-size:11px;color:var(--sub);font-weight:500;}}
table.agg{{width:100%;border-collapse:collapse;font-size:12.5px;}}table.agg th,table.agg td{{text-align:left;padding:4px 6px;border-bottom:1px solid var(--line);}}table.agg th{{color:var(--sub);font-size:11px;}}
.filter{{margin:18px 0 6px;}}.filter button{{padding:7px 14px;border:1px solid var(--line);background:#fff;border-radius:9px;font-size:13px;cursor:pointer;margin-right:6px;}}.filter button.on{{background:var(--accent);color:#fff;border-color:var(--accent);}}
details.q{{background:var(--card);border:1px solid var(--line);border-radius:12px;margin-bottom:9px;overflow:hidden;}}
details.q summary{{cursor:pointer;padding:11px 14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:13.5px;list-style:none;}}details.q summary::-webkit-details-marker{{display:none;}}
.qid{{font-weight:800;color:var(--accent);font-size:12px;}}.qt{{font-size:11px;color:var(--sub);background:#F1F3F8;padding:1px 7px;border-radius:999px;}}.qq{{flex:1 1 220px;}}.qmeta{{font-size:11.5px;color:var(--sub);}}
.delta{{font-weight:800;padding:1px 8px;border-radius:999px;margin-left:6px;font-size:11px;}}.delta.dup{{background:#DCFCE7;color:#166534;}}.delta.ddn{{background:#FEE2E2;color:#991B1B;}}.delta.dmid{{background:#F1F3F8;color:#475569;}}
.qbody{{padding:6px 16px 16px;border-top:1px solid var(--line);}}.qfull{{font-size:13.5px;margin:10px 0;}}
.ans{{margin:8px 0;border:1px solid var(--line);border-radius:9px;overflow:hidden;}}.ans .al{{background:#F1F3F8;padding:5px 10px;font-size:12px;font-weight:700;}}
.ans.blv1 .al{{background:#EEF2FF;color:#3730A3;}}.ans.blv2 .al{{background:#FEF3C7;color:#92400E;}}.ans.blv3 .al{{background:#CCFBF1;color:#0F766E;}}
.ans .at{{padding:9px 12px;font-size:13px;white-space:pre-wrap;color:#2A3344;}}.cite{{font-weight:500;color:var(--sub);font-size:11px;margin-left:6px;}}
.tf{{font-size:12.5px;background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;padding:8px 11px;margin:10px 0;}}
.vlabel{{font-weight:800;font-size:12.5px;margin:12px 0 4px;color:var(--accent);}}.vlabel.v3l{{color:var(--v3);}}
.evgrid{{display:grid;grid-template-columns:1fr 1fr;gap:10px;}}.evb{{border:1px solid var(--line);border-radius:9px;padding:10px 12px;background:#FCFDFF;}}.evh{{font-size:12.5px;font-weight:700;margin-bottom:6px;}}
.scl{{margin:4px 0;}}.sc{{display:inline-block;font-size:11.5px;padding:1px 7px;border-radius:6px;background:#F1F3F8;margin-right:4px;}}.sc.shi{{background:#DCFCE7;color:#166534;}}.sc.slo{{background:#FEE2E2;color:#991B1B;}}
.cmt{{font-size:12.5px;color:#2A3344;margin:5px 0;}}.isl{{font-size:12px;margin-top:4px;}}.isl ul{{margin:3px 0 0;padding-left:18px;}}.isl li{{color:#991B1B;}}
.pill{{display:inline-block;padding:1px 8px;border-radius:999px;font-size:11px;font-weight:700;}}.pwin{{background:#DCFCE7;color:#166534;}}.ptie{{background:#F1F3F8;color:#475569;}}.plose{{background:#FEE2E2;color:#991B1B;}}.pbless{{background:#F3E8FF;color:#6B21A8;}}.pabc{{background:#E0E7FF;color:#3730A3;}}.pbad{{background:#FEE2E2;color:#991B1B;}}.muted{{color:#9AA5B5;}}
.note{{font-size:12.5px;color:var(--sub);background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-top:16px;}}@media(max-width:680px){{.evgrid,.vcards{{grid-template-columns:1fr;}}}}
</style></head><body><div class="wrap">
<header><div class="eyebrow">REDTEAM · 블레싱 나 프롬프트 3세대(v1→v2→v3) 추이</div>
<h1>블레싱 나 v1·v2·v3 vs A·B·C</h1>
<div class="meta">조화연·신은비·김소영 각 30문항(90) · 같은 봇(id=3) 프롬프트 v1→v2→v3 재질의 · 페르소나+codex 이중 평가 · {date.today()}</div></header>
<div class="deltabar">📈 {deltaline()} · 문항 헤더 화살표는 두 평가자 평균 블레싱 점수 v1→v3 변화</div>
<div class="vcards">{vcard("v1","v1 (여정·직접)")}{vcard("v2","v2 (안전보강)")}{vcard("v3","v3 (구조수정·신규)")}</div>
<h2>사용자별 v1/v2/v3 집계</h2><div class="ucards">{"".join(ucards)}</div>
<div class="filter"><button class="on" data-f="all">전체</button><button data-f="조화연">조화연</button><button data-f="신은비">신은비</button><button data-f="김소영">김소영</button></div>
{"".join(sections)}
<div class="note"><b>방법</b> · A/B/C=2주차 3봇 고정. 블레싱 v1/v2/v3=같은 봇(id=3) 프롬프트만 바꿔 동일 90문항 재질의. v3=v2에 구조수정 5종(분류·선확인·과잉보류·변동공백·세이프티) 적용. 평가는 페르소나 에이전트+codex 독립 수행. 화살표=두 평가자 평균 블레싱 점수 v1→v3.</div>
</div><script>const b=document.querySelectorAll('.filter button');b.forEach(x=>x.onclick=()=>{{b.forEach(y=>y.classList.remove('on'));x.classList.add('on');const f=x.dataset.f;document.querySelectorAll('.usec').forEach(s=>{{s.style.display=(f==='all'||s.dataset.user===f)?'':'none';}});}});</script>
</body></html>"""
OUT.write_text(HTML, encoding="utf-8")
print(f"저장: {OUT}")
for ver in VERS: print(f"  {ver}: 페르소나 best {agg[ver]['A'][0]}/codex {agg[ver]['C'][0]}")
print(" ", deltaline())
