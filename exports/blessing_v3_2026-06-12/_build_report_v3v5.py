# 블레싱 나·가 v3 vs v5(+A/B/C) 비교 — 보수적 패치 전후를 이중 평가로
import html, json
from datetime import date
from pathlib import Path

V3 = Path("/Users/woosung/project/agy-project/nexus-core/exports/blessing_v3_2026-06-12")
DL = Path("/Users/woosung/Downloads")
WL = {"통합": "A", "원리": "B", "정밀": "C"}
BOTS = [
    ("나", ["조화연", "신은비", "김소영"], {"조화연":"redteam-johwayeon","신은비":"redteam-shineunbi","김소영":"redteam-kimsoyoung"}),
    ("가", ["미야자키시호", "김소영", "조화연"], {"미야자키시호":"redteam-miyazakishiho","김소영":"redteam-kimsoyoung","조화연":"redteam-johwayeon"}),
]
VERS = ["v3", "v5"]; VN = {"v3":"v3 (구조수정)","v5":"v5 (보수·앵커+가드레일)"}


def esc(s): return html.escape(str(s if s is not None else ""))
def load(p):
    try: return json.load(open(p))
    except Exception: return None
def vs_pill(v):
    m={"win":("우세","pwin"),"tie":("비슷","ptie"),"lose":("열세","plose")}; t,c=m.get(v,("-","ptie")); return f'<span class="pill {c}">{t}</span>'
def best_pill(b):
    cls="pbless" if b=="블레싱" else ("pbad" if b=="모두부적절" else "pabc"); return f'<span class="pill {cls}">{esc(b)}</span>'
def sc_html(sc):
    if not sc: return '<span class="muted">-</span>'
    out=[]
    for k,lab in [("A","A"),("B","B"),("C","C"),("blessing","블레싱")]:
        v=sc.get(k,"-"); hi="shi" if isinstance(v,int) and v>=4 else ("slo" if isinstance(v,int) and v<=2 else "")
        out.append(f'<span class="sc {hi}"><b>{lab}</b> {v}</span>')
    return " ".join(out)
def eval_block(ev,label):
    if not ev: return f'<div class="evb"><div class="evh">{label}</div><div class="muted">평가 없음</div></div>'
    iss="".join(f"<li>{esc(i)}</li>" for i in (ev.get("blessing_issues") or [])) or '<li class="muted">없음</li>'
    return (f'<div class="evb"><div class="evh">{label} · best {best_pill(ev.get("best"))} · {vs_pill(ev.get("blessing_vs_tester"))}</div>'
            f'<div class="scl">{sc_html(ev.get("scores"))}</div><div class="cmt">{esc(ev.get("comment"))}</div>'
            f'<div class="isl"><b>지적</b><ul>{iss}</ul></div></div>')
def bscore(ev): return (ev or {}).get("scores",{}).get("blessing")

CSS = """:root{--ink:#1A2233;--sub:#5A6678;--line:#E5E9F0;--bg:#F6F8FB;--card:#fff;--accent:#9333EA;--v5:#0D9488;}
*{box-sizing:border-box;}body{margin:0;font-family:-apple-system,'Pretendard','Apple SD Gothic Neo',sans-serif;background:var(--bg);color:var(--ink);line-height:1.6;}
.wrap{max-width:1100px;margin:0 auto;padding:36px 22px 90px;}header{border-bottom:3px solid var(--accent);padding-bottom:16px;}.eyebrow{color:var(--accent);font-weight:700;font-size:13px;}
h1{margin:6px 0 4px;font-size:25px;}h2{font-size:18px;margin:30px 0 12px;border-left:4px solid var(--accent);padding-left:10px;}.meta{color:var(--sub);font-size:13.5px;}
.deltabar{margin:16px 0;padding:14px 18px;border-radius:12px;background:#ECFDF5;border:1px solid #A7F3D0;font-size:15px;font-weight:700;color:#065F46;}
.vcards{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:14px 0;}.vcard{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;}.vcard .vt{font-weight:800;margin-bottom:8px;}.vcard .vr{font-size:13px;}
.ucards{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;}.ucard{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;}.ut{font-weight:800;margin-bottom:8px;}.uag{font-size:11px;color:var(--sub);font-weight:500;}
table.agg{width:100%;border-collapse:collapse;font-size:12.5px;}table.agg th,table.agg td{text-align:left;padding:4px 6px;border-bottom:1px solid var(--line);}table.agg th{color:var(--sub);font-size:11px;}
.filter{margin:18px 0 6px;}.filter button{padding:7px 14px;border:1px solid var(--line);background:#fff;border-radius:9px;font-size:13px;cursor:pointer;margin-right:6px;}.filter button.on{background:var(--accent);color:#fff;border-color:var(--accent);}
details.q{background:var(--card);border:1px solid var(--line);border-radius:12px;margin-bottom:9px;overflow:hidden;}details.q summary{cursor:pointer;padding:11px 14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:13.5px;list-style:none;}details.q summary::-webkit-details-marker{display:none;}
.qid{font-weight:800;color:var(--accent);font-size:12px;}.qt{font-size:11px;color:var(--sub);background:#F1F3F8;padding:1px 7px;border-radius:999px;}.qq{flex:1 1 220px;}.qmeta{font-size:11.5px;color:var(--sub);}
.delta{font-weight:800;padding:1px 8px;border-radius:999px;margin-left:6px;font-size:11px;}.delta.dup{background:#DCFCE7;color:#166534;}.delta.ddn{background:#FEE2E2;color:#991B1B;}.delta.dmid{background:#F1F3F8;color:#475569;}
.qbody{padding:6px 16px 16px;border-top:1px solid var(--line);}.qfull{font-size:13.5px;margin:10px 0;}
.ans{margin:8px 0;border:1px solid var(--line);border-radius:9px;overflow:hidden;}.ans .al{background:#F1F3F8;padding:5px 10px;font-size:12px;font-weight:700;}.ans.blv1 .al{background:#FEF3C7;color:#92400E;}.ans.blv3 .al{background:#CCFBF1;color:#0F766E;}.ans .at{padding:9px 12px;font-size:13px;white-space:pre-wrap;color:#2A3344;}.cite{font-weight:500;color:var(--sub);font-size:11px;margin-left:6px;}
.tf{font-size:12.5px;background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;padding:8px 11px;margin:10px 0;}
.vlabel{font-weight:800;font-size:12.5px;margin:12px 0 4px;color:var(--accent);}.vlabel.v5l{color:var(--v5);}
.evgrid{display:grid;grid-template-columns:1fr 1fr;gap:10px;}.evb{border:1px solid var(--line);border-radius:9px;padding:10px 12px;background:#FCFDFF;}.evh{font-size:12.5px;font-weight:700;margin-bottom:6px;}
.scl{margin:4px 0;}.sc{display:inline-block;font-size:11.5px;padding:1px 7px;border-radius:6px;background:#F1F3F8;margin-right:4px;}.sc.shi{background:#DCFCE7;color:#166534;}.sc.slo{background:#FEE2E2;color:#991B1B;}
.cmt{font-size:12.5px;color:#2A3344;margin:5px 0;}.isl{font-size:12px;margin-top:4px;}.isl ul{margin:3px 0 0;padding-left:18px;}.isl li{color:#991B1B;}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:11px;font-weight:700;}.pwin{background:#DCFCE7;color:#166534;}.ptie{background:#F1F3F8;color:#475569;}.plose{background:#FEE2E2;color:#991B1B;}.pbless{background:#F3E8FF;color:#6B21A8;}.pabc{background:#E0E7FF;color:#3730A3;}.pbad{background:#FEE2E2;color:#991B1B;}.muted{color:#9AA5B5;}
.note{font-size:12.5px;color:var(--sub);background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-top:16px;}@media(max-width:680px){.evgrid,.vcards{grid-template-columns:1fr;}}"""


def build(bot, users, agent_of):
    ds = {ver: {u: {it["qid"]: it for it in json.load(open(V3/f"dataset_{bot}_{u}_{ver}.json"))["items"]} for u in users} for ver in VERS}
    A = {}; C = {}
    for ver in VERS:
        araw = load(V3/f"agent_eval_{bot}_{ver}.json") or []
        A[ver] = {e["user"]: {r["qid"]: r for r in e["eval"]["results"]} for e in araw if e and e.get("eval")}
        C[ver] = {u: {r["qid"]: r for r in (load(V3/f"codex_{bot}_{u}_{ver}.json") or {"results":[]})["results"]} for u in users}

    def tally(ver, kind):
        src = A[ver] if kind=="A" else C[ver]; best=win=lose=0
        for u in users:
            for r in src.get(u,{}).values():
                if r["best"]=="블레싱": best+=1
                if r["blessing_vs_tester"]=="win": win+=1
                if r["blessing_vs_tester"]=="lose": lose+=1
        return best,win,lose
    agg={ver:{"A":tally(ver,"A"),"C":tally(ver,"C")} for ver in VERS}
    def vcard(ver):
        a,c=agg[ver]["A"],agg[ver]["C"]
        return (f'<div class="vcard"><div class="vt">{VN[ver]}</div>'
                f'<div class="vr">페르소나 — best <b>{a[0]}</b>/90 · 우세 {a[1]} · 열세 {a[2]}</div>'
                f'<div class="vr">codex — best <b>{c[0]}</b>/90 · 우세 {c[1]} · 열세 {c[2]}</div></div>')

    sections, ucards = [], []
    for u in users:
        def ucount(ver,kind):
            src=A[ver] if kind=="A" else C[ver]; rs=src.get(u,{}).values()
            return (sum(1 for r in rs if r["best"]=="블레싱"),sum(1 for r in rs if r["blessing_vs_tester"]=="win"),sum(1 for r in rs if r["blessing_vs_tester"]=="lose"))
        rows_agg=""
        for kind,kn in [("A","페르소나"),("C","codex")]:
            for ver in VERS:
                b,w,l=ucount(ver,kind); rows_agg+=f'<tr><td>{kn} {ver}</td><td>{b}</td><td>{w}</td><td>{l}</td></tr>'
        ucards.append(f'<div class="ucard"><div class="ut">{esc(u)} <span class="uag">{esc(agent_of[u])}</span></div><table class="agg"><tr><th>평가/버전</th><th>best</th><th>우세</th><th>열세</th></tr>{rows_agg}</table></div>')
        rows=[]
        for qid,it3 in ds["v3"][u].items():
            it5=ds["v5"][u].get(qid,{}); tester=WL.get(it3.get("tester_win"),it3.get("tester_choice"))
            def avg(ver):
                xs=[bscore(A[ver].get(u,{}).get(qid)),bscore(C[ver].get(u,{}).get(qid))]; xs=[x for x in xs if isinstance(x,int)]
                return sum(xs)/len(xs) if xs else None
            a3,a5=avg("v3"),avg("v5"); d=(a5 or 0)-(a3 or 0)
            cls="dup" if d>0.4 else ("ddn" if d<-0.4 else "dmid"); arrow="▲" if d>0.4 else ("▼" if d<-0.4 else "＝")
            trend=(f"{a3:.1f}→{a5:.1f}" if a3 is not None and a5 is not None else "-")
            def ansrow(it,lab,c2):
                cites=it.get("blessing_citations") or []
                return f'<div class="ans {c2}"><div class="al">{lab} <span class="cite">인용:{esc(", ".join(dict.fromkeys(cites)) or "없음")}</span></div><div class="at">{esc(it.get("blessing_answer"))}</div></div>'
            ev_rows=""
            for ver in VERS:
                ae=A[ver].get(u,{}).get(qid); ce=C[ver].get(u,{}).get(qid)
                vcls="v5l" if ver=="v5" else ""
                ev_rows+=f'<div class="vlabel {vcls}">{VN[ver]} 평가</div><div class="evgrid">{eval_block(ae,"페르소나")}{eval_block(ce,"codex")}</div>'
            rows.append(f"""<details class="q"><summary><span class="qid">{esc(qid)}</span><span class="qt">{esc(it3.get('qtype'))}</span>
            <span class="qq">{esc(it3['q'][:58])}</span><span class="qmeta">테스터→<b>{esc(tester)}</b> <span class="delta {cls}">{arrow} {trend}</span></span></summary>
            <div class="qbody"><div class="qfull"><b>질문</b> {esc(it3['q'])}</div>
              <div class="ans"><div class="al">A · 통합</div><div class="at">{esc(it3.get('ansA_통합'))}</div></div>
              <div class="ans"><div class="al">B · 원리</div><div class="at">{esc(it3.get('ansB_원리'))}</div></div>
              <div class="ans"><div class="al">C · 정밀</div><div class="at">{esc(it3.get('ansC_정밀'))}</div></div>
              {ansrow(it3,"블레싱 v3","blv1")}{ansrow(it5,"★ 블레싱 v5 (보수)","blv3")}
              <div class="tf"><b>테스터({esc(u)}) 원선택</b> {esc(tester)} · <b>피드백</b> {esc(it3.get('tester_feedback'))}</div>{ev_rows}</div></details>""")
        sections.append(f'<section class="usec" data-user="{esc(u)}"><h2>{esc(u)} — 30문항</h2>{"".join(rows)}</section>')

    sign=lambda x: f"+{x}" if x>0 else str(x)
    delta=f"v3→v5: 페르소나 best {sign(agg['v5']['A'][0]-agg['v3']['A'][0])} · codex best {sign(agg['v5']['C'][0]-agg['v3']['C'][0])} · 열세 페르소나 {sign(agg['v5']['A'][2]-agg['v3']['A'][2])}/codex {sign(agg['v5']['C'][2]-agg['v3']['C'][2])}"
    OUT=DL/f"블레싱_{bot}_v3v5_vs_ABC_{date.today()}.html"
    HTML=f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>블레싱 {bot} v3 vs v5 — {date.today()}</title><style>{CSS}</style></head><body><div class="wrap">
<header><div class="eyebrow">REDTEAM · 블레싱 {bot} 보수적 v5 검증</div><h1>블레싱 {bot} v3 vs v5 vs A·B·C</h1>
<div class="meta">{'·'.join(users)} 각 30문항(90) · v3→v5(보수: 확정앵커 정밀화+안전 가드레일 5종) · 페르소나+codex 이중평가 · {date.today()}</div></header>
<div class="deltabar">📈 {delta} · 문항 화살표는 두 평가자 평균 블레싱 점수 v3→v5</div>
<div class="vcards">{vcard("v3")}{vcard("v5")}</div>
<h2>사용자별 v3 vs v5 집계</h2><div class="ucards">{"".join(ucards)}</div>
<div class="filter"><button class="on" data-f="all">전체</button>{"".join(f'<button data-f="{esc(u)}">{esc(u)}</button>' for u in users)}</div>
{"".join(sections)}
<div class="note"><b>방법</b> · v5=v3에 보수적 변경(확정공문 앵커 정밀화 3건 + 선확인 게이트·위기채널 오부착 금지·가해피해 낙인완화·세대편성 되묻기·혼자아님 닫음). PENDING 공문은 단정 안 함. 평가는 페르소나+codex 독립.</div>
</div><script>const b=document.querySelectorAll('.filter button');b.forEach(x=>x.onclick=()=>{{b.forEach(y=>y.classList.remove('on'));x.classList.add('on');const f=x.dataset.f;document.querySelectorAll('.usec').forEach(s=>{{s.style.display=(f==='all'||s.dataset.user===f)?'':'none';}});}});</script>
</body></html>"""
    OUT.write_text(HTML,encoding="utf-8")
    print(f"[{bot}] {OUT}")
    for ver in VERS: print(f"   {ver}: 페르소나 best {agg[ver]['A'][0]}/codex {agg[ver]['C'][0]} · 열세 {agg[ver]['A'][2]}/{agg[ver]['C'][2]}")
    print("  ", delta)

for bot, users, agent_of in BOTS:
    build(bot, users, agent_of)
