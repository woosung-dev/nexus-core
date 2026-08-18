# 봇3종 분류 레코드 JSON 으로 봇·사용자 필터 + 차트 대화 분석 HTML 보고서 생성
import json
from datetime import date

BASE = "/Users/woosung/project/agy-project/nexus-core/exports"
d = json.load(open(f"{BASE}/_chat_v2_records.json"))
OUT = f"{BASE}/nexus_chat_report_봇별_2026-05-31_to_06-08.html"

PALETTE = [
    "#2F6FED", "#16A34A", "#DC2626", "#9333EA", "#0891B2", "#EA580C",
    "#65A30D", "#DB2777", "#4F46E5", "#0D9488", "#CA8A04", "#64748B", "#94A3B8",
]
CAT_ORDER = d["categories"] + ["미분류"]
cat_colors = {c: PALETTE[i % len(PALETTE)] for i, c in enumerate(CAT_ORDER)}

# 분류기가 목록 밖 라벨을 낸 경우 가장 가까운 정규 카테고리로 보정 (12개 체계 유지)
CATSET = set(d["categories"])
REMAP = {"부부관계": "가정출발·혼인생활", "교류·소통": "매칭·교류(B4U)"}


def fix_cat(c):
    if c in CATSET or c == "미분류":
        return c
    return REMAP.get(c, "기타·인사")

DATA = {
    "window": d["window"],
    "bots": d["bots"],
    "categories": CAT_ORDER,
    "perspectives": d["perspectives"],
    "catColors": cat_colors,
    "users": d["users"],
    "records": [{
        "bot": r["bot"], "user": r["user"], "sid": r["sid"], "date": r["date"],
        "q": r["q"], "fb": r["fb"], "c": fix_cat(r["category"]), "p": r["perspectives"],
    } for r in d["records"]],
}

meta = (f"분석 기간 {d['window'][0]} ~ {d['window'][1]} · 실서버(Neon) 운영 DB · "
        f"테스트 계정 제외 · 봇 통합/원리/정밀 3종 · 생성일 {date.today()}")

TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nexus 축복 상담 챗봇 — 봇별 대화 분석 보고서</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root { --ink:#1A2233; --sub:#5A6678; --line:#E5E9F0; --bg:#F6F8FB; --card:#fff; --accent:#2F6FED; }
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
    border:1px solid #DCE6FB; background:#F0F5FF; padding:7px 14px; border-radius:8px; }
  .cards { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin:18px 0 8px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px 20px; }
  .card .label { color:var(--sub); font-size:13px; font-weight:600; }
  .card .value { font-size:30px; font-weight:800; margin-top:4px; }
  .card .value small { font-size:14px; font-weight:600; color:var(--sub); }
  .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
  .panel { background:var(--card); border:1px solid var(--line); border-radius:16px; padding:22px 24px; margin-bottom:20px; }
  .panel h2 { margin:0 0 4px; font-size:17px; font-weight:800; }
  .panel .desc { color:var(--sub); font-size:13px; margin-bottom:16px; }
  .chart-box { position:relative; height:300px; }
  .chart-box.tall { height:360px; }
  table { width:100%; border-collapse:collapse; font-size:13.5px; }
  th,td { text-align:left; padding:9px 10px; border-bottom:1px solid var(--line); vertical-align:top; }
  th { color:var(--sub); font-weight:700; font-size:12px; }
  td.num,th.num { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
  td.ex { color:var(--sub); font-size:12.5px; }
  .dot { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:7px; vertical-align:middle; }
  .insight { background:linear-gradient(180deg,#F0F5FF,#fff); border:1px solid #DCE6FB; border-radius:16px; padding:22px 24px; margin:14px 0 20px; }
  .insight h2 { margin:0 0 10px; font-size:17px; }
  .insight p { margin:0; font-size:14px; }
  .muted { color:var(--sub); }
  footer { color:var(--sub); font-size:12px; text-align:center; margin-top:30px; }
  @media (max-width:760px) { .cards{grid-template-columns:repeat(2,1fr);} .grid2{grid-template-columns:1fr;} }
  @media print { body{background:#fff;} .panel,.card,.insight{break-inside:avoid;} .filterbar{display:none;} }
</style>
</head>
<body>
<div class="wrap">
  <header class="rpt">
    <div class="eyebrow">NEXUS · 축복 상담 AI 대화 분석 (봇 3종)</div>
    <h1>봇별 주간 대화 분석 보고서</h1>
    <div class="meta">__META__</div>
  </header>

  <div class="filterbar">
    <div><label>봇</label><select id="bsel"></select></div>
    <div><label>사용자</label><select id="usel"></select></div>
    <span class="reset" id="reset">필터 초기화</span>
  </div>

  <div class="cards" id="kpi"></div>

  <div class="insight">
    <h2>핵심 요약</h2>
    <p id="insightText"></p>
  </div>

  <div class="grid2">
    <div class="panel"><h2>봇별 사용량 비교</h2><div class="desc">세션 · 질문 수 (사용자 필터 반영, 봇 필터 무관)</div><div class="chart-box"><canvas id="botBar"></canvas></div></div>
    <div class="panel"><h2>질문 카테고리 분포</h2><div class="desc">사용자 질문을 12개 주제로 분류</div><div class="chart-box"><canvas id="catDoughnut"></canvas></div></div>
  </div>
  <div class="grid2">
    <div class="panel"><h2>카테고리별 질문 수</h2><div class="desc">많이 들어온 순서</div><div class="chart-box tall"><canvas id="catBar"></canvas></div></div>
    <div class="panel"><h2>AI 답변 관점 분포</h2><div class="desc">한 답변에 복수 관점 가능 (중복 집계)</div><div class="chart-box"><canvas id="persBar"></canvas></div></div>
  </div>
  <div class="panel"><h2>일자별 질문 추이</h2><div class="desc">KST 기준</div><div class="chart-box"><canvas id="dailyLine"></canvas></div></div>

  <div class="panel">
    <h2>카테고리별 상세 + 대표 질문 <span class="muted" id="rowcount" style="font-size:13px;font-weight:600;"></span></h2>
    <div class="desc">비중과 함께 실제 들어온 질문 예시</div>
    <table>
      <thead><tr><th>카테고리</th><th class="num">건수</th><th class="num">비중</th><th>대표 질문 예시</th></tr></thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>

  <footer>본 보고서는 Neon 운영 DB의 대화 로그를 기반으로 자동 생성되었으며, 질문/답변 분류는 Gemini 모델로 수행되었습니다.</footer>
</div>
<script>
const DATA = __DATA__;
const CATCOL = DATA.catColors;
Chart.defaults.font.family="-apple-system,Pretendard,'Apple SD Gothic Neo',sans-serif";
Chart.defaults.color="#5A6678";
const bsel=document.getElementById('bsel'), usel=document.getElementById('usel');
const ALL='__ALL__';
function opt(v,l){const o=document.createElement('option');o.value=v;o.textContent=l;return o;}
bsel.appendChild(opt(ALL,'전체 봇'));
DATA.bots.forEach(b=>bsel.appendChild(opt(b,b)));
usel.appendChild(opt(ALL,'전체 사용자'));
DATA.users.forEach(u=>usel.appendChild(opt(u,`${u} (${DATA.records.filter(r=>r.user===u).length}건)`)));

let charts={};
function mk(id,cfg){if(charts[id])charts[id].destroy();charts[id]=new Chart(document.getElementById(id),cfg);}
function esc(s){return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function uniq(arr){return [...new Set(arr)];}

function byUser(){const u=usel.value;return DATA.records.filter(r=>u===ALL||r.user===u);}
function filtered(){const b=bsel.value;return byUser().filter(r=>b===ALL||r.bot===b);}

function renderKPI(rows){
  const sess=uniq(rows.map(r=>r.sid)).length;
  const users=uniq(rows.map(r=>r.user)).length;
  let up=0,down=0;rows.forEach(r=>{if(r.fb==='up')up++;else if(r.fb==='down')down++;});
  const rate=(up+down)?Math.round(up/(up+down)*100):0;
  document.getElementById('kpi').innerHTML=
    `<div class="card"><div class="label">총 대화 세션</div><div class="value">${sess}<small> 건</small></div></div>`+
    `<div class="card"><div class="label">사용자 질문</div><div class="value">${rows.length}<small> 건</small></div></div>`+
    `<div class="card"><div class="label">참여 사용자</div><div class="value">${users}<small> 명</small></div></div>`+
    `<div class="card"><div class="label">긍정 피드백률</div><div class="value">${rate}<small>% (${up}↑/${down}↓)</small></div></div>`;
}
function catCounts(rows){const c={};DATA.categories.forEach(k=>c[k]=0);rows.forEach(r=>{c[r.c]=(c[r.c]||0)+1;});return c;}
function renderInsight(rows){
  const c=catCounts(rows);const tot=rows.length||1;
  const top=Object.entries(c).filter(x=>x[1]>0).sort((a,b)=>b[1]-a[1]).slice(0,3);
  const top3=top.map(([k,v])=>`<b>${k}</b>(${Math.round(v/tot*100)}%)`).join(', ');
  const pc={};DATA.perspectives.forEach(k=>pc[k]=0);rows.forEach(r=>(r.p||[]).forEach(p=>pc[p]=(pc[p]||0)+1));
  const topP=Object.entries(pc).sort((a,b)=>b[1]-a[1])[0];
  const b=bsel.value===ALL?'전체 봇':`'${bsel.value}' 봇`;
  document.getElementById('insightText').innerHTML=
    `${b} 기준, 가장 많이 들어온 질문 유형은 ${top3} 순입니다. `+
    `AI 답변에서 가장 자주 나타난 관점은 <b>${topP?topP[0]:'-'}</b>입니다. `+
    `봇별 사용량은 상단 막대 차트에서, 사용자별 분포는 사용자 필터로 확인하세요.`;
}
function renderCharts(rows){
  // 봇별 사용량 (사용자 필터만 반영)
  const ru=byUser();
  const sessByBot=DATA.bots.map(b=>uniq(ru.filter(r=>r.bot===b).map(r=>r.sid)).length);
  const qByBot=DATA.bots.map(b=>ru.filter(r=>r.bot===b).length);
  mk('botBar',{type:'bar',data:{labels:DATA.bots,datasets:[
      {label:'세션',data:sessByBot,backgroundColor:'#94A3B8',borderRadius:5},
      {label:'질문',data:qByBot,backgroundColor:'#2F6FED',borderRadius:5}]},
    options:{plugins:{legend:{position:'bottom',labels:{boxWidth:12}}},scales:{y:{beginAtZero:true,grid:{color:'#EEF1F6'}},x:{grid:{display:false}}}}});

  const c=catCounts(rows);
  const ce=Object.entries(c).filter(x=>x[1]>0);
  mk('catDoughnut',{type:'doughnut',data:{labels:ce.map(x=>x[0]),datasets:[{data:ce.map(x=>x[1]),
    backgroundColor:ce.map(x=>CATCOL[x[0]]||'#94A3B8'),borderWidth:2,borderColor:'#fff'}]},
    options:{plugins:{legend:{position:'right',labels:{boxWidth:12,padding:8,font:{size:11}}}},cutout:'55%'}});

  const cs=ce.slice().sort((a,b)=>b[1]-a[1]);
  mk('catBar',{type:'bar',data:{labels:cs.map(x=>x[0]),datasets:[{data:cs.map(x=>x[1]),
    backgroundColor:cs.map(x=>CATCOL[x[0]]||'#94A3B8'),borderRadius:5}]},
    options:{indexAxis:'y',plugins:{legend:{display:false}},scales:{x:{beginAtZero:true,grid:{color:'#EEF1F6'}},y:{grid:{display:false},ticks:{font:{size:11}}}}}});

  const pc={};DATA.perspectives.forEach(k=>pc[k]=0);rows.forEach(r=>(r.p||[]).forEach(p=>pc[p]=(pc[p]||0)+1));
  const pe=Object.entries(pc).filter(x=>x[1]>0).sort((a,b)=>b[1]-a[1]);
  mk('persBar',{type:'bar',data:{labels:pe.map(x=>x[0]),datasets:[{data:pe.map(x=>x[1]),backgroundColor:'#2F6FED',borderRadius:5}]},
    options:{indexAxis:'y',plugins:{legend:{display:false}},scales:{x:{beginAtZero:true,grid:{color:'#EEF1F6'}},y:{grid:{display:false}}}}});

  const dd={};rows.forEach(r=>{if(r.date)dd[r.date]=(dd[r.date]||0)+1;});
  const dl=Object.keys(dd).sort();
  mk('dailyLine',{type:'line',data:{labels:dl,datasets:[{data:dl.map(k=>dd[k]),borderColor:'#16A34A',
    backgroundColor:'rgba(22,163,74,.12)',fill:true,tension:.35,pointRadius:4,pointBackgroundColor:'#16A34A'}]},
    options:{plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,grid:{color:'#EEF1F6'}},x:{grid:{display:false}}}}});
}
function renderTable(rows){
  document.getElementById('rowcount').textContent=`(질문 ${rows.length}건)`;
  const c=catCounts(rows);const tot=rows.length||1;
  const ex={};rows.forEach(r=>{(ex[r.c]=ex[r.c]||[]);if(ex[r.c].length<3&&r.q)ex[r.c].push(r.q.slice(0,60));});
  const cs=Object.entries(c).filter(x=>x[1]>0).sort((a,b)=>b[1]-a[1]);
  document.getElementById('tbody').innerHTML=cs.map(([k,v])=>
    `<tr><td><span class="dot" style="background:${CATCOL[k]||'#94A3B8'}"></span>${esc(k)}</td>`+
    `<td class="num">${v}</td><td class="num">${(v/tot*100).toFixed(1)}%</td>`+
    `<td class="ex">${(ex[k]||[]).map(esc).join(' / ')||'-'}</td></tr>`).join('');
}
function apply(){const rows=filtered();renderKPI(rows);renderInsight(rows);renderCharts(rows);renderTable(rows);}
bsel.onchange=apply;usel.onchange=apply;
document.getElementById('reset').onclick=()=>{bsel.value=ALL;usel.value=ALL;apply();};
apply();
</script>
</body>
</html>"""

html = (TEMPLATE
        .replace("__META__", meta)
        .replace("__DATA__", json.dumps(DATA, ensure_ascii=False)))
open(OUT, "w").write(html)
print("보고서 저장:", OUT)
print(f"레코드 {len(DATA['records'])}건 / 사용자 {len(DATA['users'])}명 / 봇 {DATA['bots']}")
