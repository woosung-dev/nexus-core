# 레드팀 v2 집계/요약 JSON 으로 봇 A/B/C 승률 비교 + 필터 HTML 보고서 생성
import json
from datetime import date

BASE = "/Users/woosung/project/agy-project/nexus-core/exports"
data = json.load(open(f"{BASE}/_redteam_v2_data.json"))
summary = json.load(open(f"{BASE}/_redteam_v2_summary.json"))
agg = data["agg"]
OUT = f"{BASE}/redteam_feedback_report_봇비교_2026-06-03_to_06-08.html"

BOTS = ["통합", "원리", "정밀"]
BOTCOL = {"통합": "#2F6FED", "원리": "#16A34A", "정밀": "#EA580C"}

# 클라이언트용 레코드 (g = 집계그룹: 통합/원리/정밀/복수/무효)
records = [{
    "d": r["date"], "u": r["user"], "t": r["qtype"], "q": r["q"],
    "a": [r["ansA"], r["ansB"], r["ansC"]],
    "g": r["win"] if r["win"] else r["choice"],
    "c": r["choice"],
    "fb": r["feedback"],
} for r in data["records"]]

DATA = {
    "bots": BOTS,
    "testers": agg["testers"],
    "qtypes": agg["qtypes"],
    "total": agg["total"],
    "records": records,
    # 봇 강·약점 요약: 전체(__ALL__) + 테스터별 (클라이언트에서 테스터 필터에 맞춰 렌더)
    "botSummary": {"__ALL__": summary.get("bots", {}), **summary.get("byTester", {})},
}

# 공통 개선 주제 카드
theme_cards = ""
for i, t in enumerate(sorted(summary.get("themes", []), key=lambda x: -x.get("count", 0))):
    quotes = "".join(f'<li>"{q}"</li>' for q in t.get("quotes", [])[:2])
    theme_cards += f"""<div class="theme">
      <div class="theme-head"><span class="rank">{i+1}</span><h3>{t['title']}</h3><span class="cnt">{t.get('count','?')}건</span></div>
      <p class="theme-desc">{t.get('desc','')}</p>
      <ul class="quotes">{quotes}</ul>
    </div>"""

leader = max(BOTS, key=lambda b: agg["win"][b])
insight = (f"{summary.get('overall','')} 유효 선택 {agg['valid_total']}건 기준 "
           f"<b>통합 {agg['win']['통합']}({agg['win_pct']['통합']}%)</b>, "
           f"<b>원리 {agg['win']['원리']}({agg['win_pct']['원리']}%)</b>, "
           f"<b>정밀 {agg['win']['정밀']}({agg['win_pct']['정밀']}%)</b> 순으로, "
           f"<b>{leader}</b>가 가장 선호되었습니다. (복수선택 {agg['multi']}건·무효 {agg['invalid']}건 제외)")

meta = (f"테스트 기간 2026-06-03 ~ 06-08 · 비교 {agg['total']}건 · "
        f"테스터 {len(agg['testers'])}명 · 봇 통합(A)/원리(B)/정밀(C) · 생성일 {date.today()}")

TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>레드팀 2주차 봇 비교 분석 보고서 — Nexus 축복 상담 AI</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root { --ink:#1A2233; --sub:#5A6678; --line:#E5E9F0; --bg:#F6F8FB; --card:#fff; --accent:#9333EA; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:-apple-system,'Pretendard','Apple SD Gothic Neo',Segoe UI,Roboto,sans-serif;
    background:var(--bg); color:var(--ink); line-height:1.6; -webkit-font-smoothing:antialiased; }
  .wrap { max-width:1120px; margin:0 auto; padding:40px 24px 80px; }
  header.rpt { border-bottom:3px solid var(--accent); padding-bottom:20px; }
  header.rpt .eyebrow { color:var(--accent); font-weight:700; font-size:13px; letter-spacing:.08em; }
  header.rpt h1 { margin:6px 0 4px; font-size:28px; font-weight:800; }
  header.rpt .meta { color:var(--sub); font-size:14px; }
  .filterbar { display:flex; gap:14px; flex-wrap:wrap; align-items:center; margin:22px 0 4px;
    background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px 18px; }
  .filterbar label { font-size:13px; font-weight:700; color:var(--sub); margin-right:6px; }
  .filterbar select { font-size:14px; padding:7px 12px; border:1px solid var(--line); border-radius:8px;
    background:#fff; color:var(--ink); font-family:inherit; min-width:150px; }
  .filterbar .reset { margin-left:auto; font-size:13px; color:var(--accent); cursor:pointer; font-weight:700;
    border:1px solid #EBDDFB; background:#FAF5FF; padding:7px 14px; border-radius:8px; }
  .cards { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin:18px 0 8px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px 20px; }
  .card .label { color:var(--sub); font-size:13px; font-weight:600; }
  .card .value { font-size:30px; font-weight:800; margin-top:4px; }
  .card .value small { font-size:14px; font-weight:600; color:var(--sub); }
  .card.b통합 { border-top:4px solid #2F6FED; } .card.b원리 { border-top:4px solid #16A34A; } .card.b정밀 { border-top:4px solid #EA580C; }
  .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
  .panel { background:var(--card); border:1px solid var(--line); border-radius:16px; padding:22px 24px; margin-bottom:20px; }
  .panel h2 { margin:0 0 4px; font-size:17px; font-weight:800; }
  .panel .desc { color:var(--sub); font-size:13px; margin-bottom:16px; }
  .chart-box { position:relative; height:300px; }
  .chart-box.tall { height:360px; }
  .insight { background:linear-gradient(180deg,#FAF5FF,#fff); border:1px solid #EBDDFB; border-radius:16px; padding:22px 24px; margin:14px 0 20px; }
  .insight h2 { margin:0 0 10px; font-size:17px; }
  .insight p { margin:0; font-size:14px; }
  .botgrid { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; }
  .botcard { border:1px solid var(--line); border-radius:14px; padding:16px 18px; background:#fff; }
  .botcard-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; }
  .botcard-head h3 { margin:0; font-size:18px; font-weight:800; }
  .winbadge { color:#fff; font-size:12.5px; font-weight:800; padding:3px 10px; border-radius:20px; }
  .pc { margin-top:8px; } .pc-t { font-size:13px; font-weight:800; margin-bottom:2px; }
  .pc-t.pros { color:#16A34A; } .pc-t.cons { color:#DC2626; }
  .pc ul { margin:0 0 4px; padding-left:18px; } .pc li { font-size:12.8px; color:#475569; margin:3px 0; }
  .themes { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
  .theme { border:1px solid var(--line); border-radius:14px; padding:16px 18px; background:#fff; }
  .theme-head { display:flex; align-items:center; gap:10px; }
  .theme-head h3 { margin:0; font-size:15px; font-weight:800; flex:1; }
  .rank { width:24px; height:24px; border-radius:50%; background:var(--accent); color:#fff; font-size:13px; font-weight:800; display:flex; align-items:center; justify-content:center; }
  .cnt { font-size:12px; font-weight:700; color:var(--accent); background:#F3E8FF; padding:2px 9px; border-radius:20px; }
  .theme-desc { font-size:13px; color:var(--sub); margin:8px 0; }
  .quotes { margin:0; padding-left:16px; } .quotes li { font-size:12.5px; color:#475569; margin:4px 0; }
  table { width:100%; border-collapse:collapse; font-size:13.5px; }
  th,td { text-align:left; padding:9px 10px; border-bottom:1px solid var(--line); vertical-align:top; }
  th { color:var(--sub); font-weight:700; font-size:12px; }
  .winpill { font-size:11.5px; font-weight:800; color:#fff; padding:2px 9px; border-radius:20px; white-space:nowrap; }
  .trow { cursor:pointer; } .trow:hover { background:#FAFAFE; }
  .qcell { max-width:520px; }
  .detail td { background:#FAFAFD; }
  .ans { margin:8px 0; padding:10px 12px; border-radius:10px; border:1px solid var(--line); background:#fff; font-size:12.8px; white-space:pre-wrap; }
  .ans .ans-h { font-weight:800; font-size:12px; margin-bottom:4px; }
  .ans.win { border-width:2px; }
  .fbline { font-size:12.8px; color:#334155; margin-top:8px; padding:8px 10px; background:#FFF7ED; border:1px solid #FED7AA; border-radius:8px; white-space:pre-wrap; }
  .tablewrap { max-height:680px; overflow:auto; }
  .muted { color:var(--sub); }
  footer { color:var(--sub); font-size:12px; text-align:center; margin-top:30px; }
  @media (max-width:760px) { .cards{grid-template-columns:repeat(2,1fr);} .grid2,.themes,.botgrid{grid-template-columns:1fr;} }
  @media print { body{background:#fff;} .wrap{max-width:none;} .panel,.card,.insight,.theme,.botcard{break-inside:avoid;} .filterbar{display:none;} }
</style>
</head>
<body>
<div class="wrap">
  <header class="rpt">
    <div class="eyebrow">NEXUS · 레드팀 2주차 봇 비교 (A=통합 / B=원리 / C=정밀)</div>
    <h1>레드팀 봇 비교 분석 보고서</h1>
    <div class="meta">__META__</div>
  </header>

  <div class="filterbar">
    <div><label>테스터</label><select id="tsel"></select></div>
    <div><label>질문 유형</label><select id="qsel"></select></div>
    <span class="reset" id="reset">필터 초기화</span>
  </div>

  <div class="cards" id="kpi"></div>

  <div class="insight">
    <h2>핵심 요약</h2>
    <p>__INSIGHT__</p>
  </div>

  <div class="grid2">
    <div class="panel"><h2>봇별 선호(승률)</h2><div class="desc">테스터가 고른 '가장 좋은 응답' 분포 · 복수/무효 포함</div><div class="chart-box"><canvas id="winDoughnut"></canvas></div></div>
    <div class="panel"><h2>질문 유형별 봇 선호</h2><div class="desc">유효 선택 기준 누적</div><div class="chart-box tall"><canvas id="qtypeStack"></canvas></div></div>
  </div>
  <div class="grid2">
    <div class="panel"><h2>테스터별 봇 선호</h2><div class="desc">유효 선택 기준 누적</div><div class="chart-box tall"><canvas id="testerStack"></canvas></div></div>
    <div class="panel"><h2>일자별 비교 건수</h2><div class="desc">제출 타임스탬프 기준</div><div class="chart-box"><canvas id="dailyLine"></canvas></div></div>
  </div>

  <div class="panel">
    <h2>봇별 강·약점 (자유 피드백 요약) <span class="muted" id="botgridLabel" style="font-size:13px;font-weight:600;"></span></h2>
    <div class="desc">테스터 서술형 의견을 AI로 봇별 정리 · 위 <b>테스터</b> 필터를 고르면 해당 테스터 의견만 표시됩니다 (질문유형 필터와 무관)</div>
    <div class="botgrid" id="botgrid"></div>
  </div>

  <div class="panel">
    <h2>공통 개선 주제</h2>
    <div class="desc">봇 종류와 무관하게 반복 제기된 의견 (언급 빈도순)</div>
    <div class="themes">__THEMECARDS__</div>
  </div>

  <div class="panel">
    <h2>개별 비교 상세 <span class="muted" id="rowcount" style="font-size:13px;font-weight:600;"></span></h2>
    <div class="desc">행을 클릭하면 3봇 응답 전문과 피드백을 볼 수 있습니다. (선택봇은 테두리 강조)</div>
    <div class="tablewrap">
    <table>
      <thead><tr><th>날짜</th><th>테스터</th><th>질문 유형</th><th class="qcell">질문</th><th>선택</th></tr></thead>
      <tbody id="tbody"></tbody>
    </table>
    </div>
  </div>

  <footer>본 보고서는 레드팀 2주차 설문(Google Forms) __TOTAL__건을 기반으로 자동 생성되었으며, 자유서술 피드백 요약은 OpenAI 모델로 수행되었습니다. 봇 응답은 통합(A)·원리(B)·정밀(C) 3종 블라인드 비교입니다.</footer>
</div>
<script>
const DATA = __DATA__;
const BOTS = DATA.bots;
const BC = {통합:'#2F6FED', 원리:'#16A34A', 정밀:'#EA580C'};
const GC = {복수:'#94A3B8', 무효:'#CBD5E1'};
Chart.defaults.font.family="-apple-system,Pretendard,'Apple SD Gothic Neo',sans-serif";
Chart.defaults.color="#5A6678";
const tsel=document.getElementById('tsel'), qsel=document.getElementById('qsel');
const ALL='__ALL__';
function opt(v,label){const o=document.createElement('option');o.value=v;o.textContent=label;return o;}
tsel.appendChild(opt(ALL,'전체 테스터'));
DATA.testers.forEach(t=>tsel.appendChild(opt(t,t)));
qsel.appendChild(opt(ALL,'전체 유형'));
DATA.qtypes.forEach(q=>qsel.appendChild(opt(q,q)));

let charts={};
function mk(id,cfg){if(charts[id])charts[id].destroy();charts[id]=new Chart(document.getElementById(id),cfg);}
function esc(s){return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

function filtered(){
  const t=tsel.value,q=qsel.value;
  return DATA.records.filter(r=>(t===ALL||r.u===t)&&(q===ALL||r.t===q));
}
function winCount(rows){const c={통합:0,원리:0,정밀:0,복수:0,무효:0};rows.forEach(r=>{if(c[r.g]!==undefined)c[r.g]++;else c['무효']++;});return c;}

function renderKPI(rows){
  const c=winCount(rows);const valid=c.통합+c.원리+c.정밀;
  const pct=b=>valid?Math.round(c[b]/valid*100):0;
  const kpi=document.getElementById('kpi');
  kpi.innerHTML=
    `<div class="card"><div class="label">총 비교</div><div class="value">${rows.length}<small> 건</small></div></div>`+
    BOTS.map(b=>`<div class="card b${b}"><div class="label">${b}(${b==='통합'?'A':b==='원리'?'B':'C'}) 선호</div><div class="value">${pct(b)}<small>% (${c[b]}승)</small></div></div>`).join('');
}
function renderCharts(rows){
  const c=winCount(rows);
  mk('winDoughnut',{type:'doughnut',
    data:{labels:['통합','원리','정밀','복수','무효'],datasets:[{data:[c.통합,c.원리,c.정밀,c.복수,c.무효],
      backgroundColor:[BC.통합,BC.원리,BC.정밀,GC.복수,GC.무효],borderWidth:2,borderColor:'#fff'}]},
    options:{plugins:{legend:{position:'right',labels:{boxWidth:12,padding:8,font:{size:12}}}},cutout:'55%'}});

  function stack(rows,keyFn){
    const keys=[...new Set(rows.map(keyFn))];
    const counts={};keys.forEach(k=>counts[k]={통합:0,원리:0,정밀:0});
    rows.forEach(r=>{if(counts[keyFn(r)]&&counts[keyFn(r)][r.g]!==undefined)counts[keyFn(r)][r.g]++;});
    keys.sort((a,b)=>{const sa=counts[a].통합+counts[a].원리+counts[a].정밀,sb=counts[b].통합+counts[b].원리+counts[b].정밀;return sb-sa;});
    return {keys,ds:BOTS.map(b=>({label:b,data:keys.map(k=>counts[k][b]),backgroundColor:BC[b],borderRadius:3}))};
  }
  const sq=stack(rows,r=>r.t);
  mk('qtypeStack',{type:'bar',data:{labels:sq.keys,datasets:sq.ds},
    options:{indexAxis:'y',plugins:{legend:{position:'bottom',labels:{boxWidth:12,font:{size:11}}}},
      scales:{x:{stacked:true,beginAtZero:true,grid:{color:'#EEF1F6'}},y:{stacked:true,grid:{display:false},ticks:{font:{size:11}}}}}});
  const st=stack(rows,r=>r.u);
  mk('testerStack',{type:'bar',data:{labels:st.keys,datasets:st.ds},
    options:{indexAxis:'y',plugins:{legend:{position:'bottom',labels:{boxWidth:12,font:{size:11}}}},
      scales:{x:{stacked:true,beginAtZero:true,grid:{color:'#EEF1F6'}},y:{stacked:true,grid:{display:false},ticks:{font:{size:11}}}}}});

  const dd={};rows.forEach(r=>{if(r.d)dd[r.d]=(dd[r.d]||0)+1;});
  const dl=Object.keys(dd).sort();
  mk('dailyLine',{type:'line',data:{labels:dl,datasets:[{data:dl.map(k=>dd[k]),borderColor:'#9333EA',
    backgroundColor:'rgba(147,51,234,.12)',fill:true,tension:.35,pointRadius:4,pointBackgroundColor:'#9333EA'}]},
    options:{plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,grid:{color:'#EEF1F6'}},x:{grid:{display:false}}}}});
}
function pill(g){const col=BC[g]||GC[g]||'#CBD5E1';const txt=g==='통합'?'통합 A':g==='원리'?'원리 B':g==='정밀'?'정밀 C':g;return `<span class="winpill" style="background:${col}">${txt}</span>`;}
function renderTable(rows){
  document.getElementById('rowcount').textContent=`(${rows.length}건)`;
  const tb=document.getElementById('tbody');
  tb.innerHTML=rows.map((r,i)=>{
    const names=['통합 A','원리 B','정밀 C'];
    const detail=names.map((n,j)=>{
      const isWin=(j===0&&r.g==='통합')||(j===1&&r.g==='원리')||(j===2&&r.g==='정밀');
      const col=[BC.통합,BC.원리,BC.정밀][j];
      return `<div class="ans${isWin?' win':''}" style="${isWin?'border-color:'+col:''}"><div class="ans-h" style="color:${col}">${n}${isWin?' ✅ 선택됨':''}</div>${esc(r.a[j])}</div>`;
    }).join('');
    const fb=r.fb?`<div class="fbline"><b>피드백</b> ${esc(r.fb)}</div>`:'';
    return `<tr class="trow" onclick="document.getElementById('d${i}').style.display=document.getElementById('d${i}').style.display==='table-row'?'none':'table-row'">
      <td class="muted">${r.d||''}</td><td>${esc(r.u)}</td><td>${esc(r.t)}</td><td class="qcell">${esc(r.q)}</td><td>${pill(r.g)}</td></tr>
      <tr class="detail" id="d${i}" style="display:none"><td colspan="5">${detail}${fb}</td></tr>`;
  }).join('');
}
const BS=DATA.botSummary;
function renderBotCards(){
  const t=tsel.value;
  const summ=BS[t]||BS['__ALL__'];
  const trows=(t===ALL)?DATA.records:DATA.records.filter(r=>r.u===t);
  const wc=winCount(trows);const valid=wc.통합+wc.원리+wc.정밀;
  const li=arr=>(arr&&arr.length)?arr.map(x=>`<li>${esc(x)}</li>`).join(''):'<li class="muted">언급 없음</li>';
  document.getElementById('botgrid').innerHTML=BOTS.map(b=>{
    const info=(summ&&summ[b])||{pros:[],cons:[]};
    const pct=valid?Math.round(wc[b]/valid*100):0;
    return `<div class="botcard" style="border-top:4px solid ${BC[b]}">
      <div class="botcard-head"><h3>${b}</h3><span class="winbadge" style="background:${BC[b]}">${wc[b]}승 · ${pct}%</span></div>
      <div class="pc"><div class="pc-t pros">👍 좋았던 점</div><ul>${li(info.pros)}</ul></div>
      <div class="pc"><div class="pc-t cons">👎 아쉬운 점</div><ul>${li(info.cons)}</ul></div>
    </div>`;
  }).join('');
  const lbl=document.getElementById('botgridLabel');
  if(lbl)lbl.textContent=(t===ALL)?'· 전체 테스터 종합':`· 테스터 '${t}'`;
}
function apply(){const rows=filtered();renderKPI(rows);renderCharts(rows);renderTable(rows);renderBotCards();}
tsel.onchange=apply;qsel.onchange=apply;
document.getElementById('reset').onclick=()=>{tsel.value=ALL;qsel.value=ALL;apply();};
apply();
</script>
</body>
</html>"""

html = (TEMPLATE
        .replace("__META__", meta)
        .replace("__INSIGHT__", insight)
        .replace("__THEMECARDS__", theme_cards)
        .replace("__TOTAL__", str(agg["total"]))
        .replace("__DATA__", json.dumps(DATA, ensure_ascii=False)))

open(OUT, "w").write(html)
print("보고서 저장:", OUT)
print(f"승수 통합 {agg['win']['통합']} / 원리 {agg['win']['원리']} / 정밀 {agg['win']['정밀']} (유효 {agg['valid_total']})")
