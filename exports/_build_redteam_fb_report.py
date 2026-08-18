# 태깅된 레드팀 피드백 JSON으로 다차원 필터 + Chart.js 자체완결형 HTML 리포트 생성
import json
from datetime import date
from pathlib import Path

BASE = Path("/Users/woosung/project/agy-project/nexus-core/exports")
IN = BASE / "_redteam_fb_tagged.json"
RECORDS = BASE / "_redteam_fb_records.json"
OUT = BASE / f"redteam_feedback_분류리포트_1-3주차_{date.today()}.html"

AXES = ["사실·정보정확성", "표현·어투·톤", "내용충실성·누락", "안전·민감성",
        "출처·말씀자료근거", "UX·속도·버그", "목회적·정서적배려",
        "세대적용(1·2세)", "분류·용어정확성", "미분류"]
AXIS_COLOR = {
    "사실·정보정확성": "#DC2626", "표현·어투·톤": "#2563EB", "내용충실성·누락": "#D97706",
    "안전·민감성": "#9333EA", "출처·말씀자료근거": "#0891B2", "UX·속도·버그": "#64748B",
    "목회적·정서적배려": "#16A34A", "세대적용(1·2세)": "#DB2777", "분류·용어정확성": "#CA8A04",
    "미분류": "#94A3B8",
}
POLARITY = ["긍정", "부정", "혼합", "제안"]
POL_COLOR = {"긍정": "#16A34A", "부정": "#DC2626", "혼합": "#D97706", "제안": "#2563EB"}
SEVERITY = ["상", "중", "하"]
SEV_COLOR = {"상": "#DC2626", "중": "#D97706", "하": "#94A3B8"}


def main():
    tagged = json.loads(IN.read_text(encoding="utf-8"))
    # has_feedback=false 통계용으로 원본도 로드(현재는 전부 has_feedback)
    all_records = json.loads(RECORDS.read_text(encoding="utf-8"))
    n_total = len(all_records)
    n_tagged = len(tagged)

    # FAQ 자동응답 플래그를 원본 레코드에서 id로 병합(코덱스 재태깅 없이 결정적 매칭 결과 주입)
    faq_by_id = {r["id"]: r for r in all_records}
    for r in tagged:
        fr = faq_by_id.get(r["id"], {})
        r["faq_fired"] = fr.get("faq_fired", False)
        r["faq_bots"] = fr.get("faq_bots", [])
        r["faq_ids"] = fr.get("faq_ids", [])
    n_faq = sum(1 for r in tagged if r["faq_fired"])

    # 필터 어휘 수집
    weeks = sorted({r["week"] for r in tagged})
    categories = sorted({r["category"] for r in tagged})
    submitters = sorted({r["submitter"] for r in tagged})
    bots = []
    for r in tagged:
        for b in r["target"] + r["bots"]:
            if b not in bots:
                bots.append(b)
    risks = ["상", "중", "하", "없음"]

    # 클라이언트 레코드 (경량 키)
    recs = [{
        "id": r["id"], "w": r["week"], "cat": r["category"], "sub": r["submitter"],
        "risk": r.get("risk") or "없음", "rt": r.get("rating"),
        "bots": r["bots"], "ax": r["axes"], "pol": r["polarity"],
        "sev": r["severity"], "tg": r["target"], "sm": r["summary"],
        "q": r["question"], "fb": r["fb_full"],
        "faq": r["faq_fired"], "faqb": r["faq_bots"], "faqi": r["faq_ids"],
    } for r in tagged]

    DATA = {
        "recs": recs, "weeks": weeks, "categories": categories,
        "submitters": submitters, "bots": bots, "risks": risks,
        "AXES": AXES, "AXIS_COLOR": AXIS_COLOR,
        "POLARITY": POLARITY, "POL_COLOR": POL_COLOR,
        "SEVERITY": SEVERITY, "SEV_COLOR": SEV_COLOR,
    }

    meta = (f"레드팀 1·2·3주차 피드백 {n_total}건 · 태깅 {n_tagged}건 · "
            f"평가자 {len(submitters)}명 · FAQ 자동응답 발동 {n_faq}건 · "
            f"분류엔진 codex CLI · 생성일 {date.today()}")

    html = TEMPLATE.replace("__META__", meta).replace("__DATA__", json.dumps(DATA, ensure_ascii=False))
    OUT.write_text(html, encoding="utf-8")
    print(f"리포트 생성 → {OUT}")
    print(f"  레코드 {n_tagged} · 평가축 {len(AXES)-1} · 평가자 {len(submitters)} · 대상봇 {len(bots)}")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>레드팀 1·2·3주차 피드백 다차원 분류 리포트 — Nexus 축복 상담 AI</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root { --ink:#1A2233; --sub:#5A6678; --line:#E5E9F0; --bg:#F6F8FB; --card:#fff; --accent:#9333EA; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:-apple-system,'Pretendard','Apple SD Gothic Neo',Segoe UI,Roboto,sans-serif;
    background:var(--bg); color:var(--ink); line-height:1.6; -webkit-font-smoothing:antialiased; }
  .wrap { max-width:1240px; margin:0 auto; padding:36px 22px 80px; }
  header.rpt { border-bottom:3px solid var(--accent); padding-bottom:18px; }
  header.rpt .eyebrow { color:var(--accent); font-weight:700; font-size:13px; letter-spacing:.08em; }
  header.rpt h1 { margin:6px 0 4px; font-size:26px; font-weight:800; }
  header.rpt .meta { color:var(--sub); font-size:13.5px; }
  .layout { display:grid; grid-template-columns:264px 1fr; gap:22px; margin-top:22px; align-items:start; }
  .side { position:sticky; top:16px; background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px 16px 20px; max-height:calc(100vh - 32px); overflow:auto; }
  .side h3 { font-size:13px; margin:16px 0 8px; color:var(--ink); font-weight:800; letter-spacing:.02em; }
  .side h3:first-child { margin-top:0; }
  .fgroup { display:flex; flex-wrap:wrap; gap:6px; }
  .chip { font-size:12px; padding:5px 10px; border:1px solid var(--line); border-radius:20px; cursor:pointer; user-select:none; background:#fff; color:#475569; transition:.12s; }
  .chip:hover { border-color:#CBD5E1; }
  .chip.on { background:var(--accent); border-color:var(--accent); color:#fff; font-weight:700; }
  .chip.on[data-c] { background:var(--cc); border-color:var(--cc); }
  .search { width:100%; font-size:13px; padding:8px 11px; border:1px solid var(--line); border-radius:9px; margin-top:2px; font-family:inherit; }
  .reset { display:block; width:100%; margin-top:16px; font-size:13px; color:var(--accent); cursor:pointer; font-weight:700; border:1px solid #EBDDFB; background:#FAF5FF; padding:9px; border-radius:9px; text-align:center; }
  .csv { display:block; width:100%; margin-top:8px; font-size:13px; color:#0F766E; cursor:pointer; font-weight:700; border:1px solid #99F6E4; background:#F0FDFA; padding:9px; border-radius:9px; text-align:center; }
  .kpis { display:grid; grid-template-columns:repeat(5,1fr); gap:12px; margin-bottom:16px; }
  .kpi { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px 16px; border-top:4px solid var(--accent); }
  .kpi .l { color:var(--sub); font-size:12.5px; font-weight:600; }
  .kpi .v { font-size:26px; font-weight:800; margin-top:2px; } .kpi .v small { font-size:13px; font-weight:600; color:var(--sub); }
  .insight { background:linear-gradient(180deg,#FAF5FF,#fff); border:1px solid #EBDDFB; border-radius:14px; padding:18px 20px; margin-bottom:16px; }
  .insight h2 { margin:0 0 8px; font-size:16px; } .insight p { margin:0; font-size:13.5px; }
  .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
  .panel { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px 20px; margin-bottom:16px; }
  .panel h2 { margin:0 0 2px; font-size:15px; font-weight:800; } .panel .desc { color:var(--sub); font-size:12.5px; margin-bottom:12px; }
  .chart-box { position:relative; height:260px; } .chart-box.tall { height:320px; }
  .heat { display:grid; gap:3px; font-size:11.5px; }
  .heat .hc { padding:6px 4px; text-align:center; border-radius:5px; color:#1A2233; }
  .heat .hh { font-weight:700; color:var(--sub); background:none; }
  .cardlist { display:flex; flex-direction:column; gap:10px; }
  .fcard { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px 16px; border-left:4px solid var(--sev); }
  .fcard .head { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:6px; }
  .fcard .sm { font-weight:800; font-size:14px; flex:1; min-width:200px; }
  .tag { font-size:11px; font-weight:700; padding:2px 8px; border-radius:6px; color:#fff; white-space:nowrap; }
  .tag.pol { } .tag.sev { } .tag.ax { }
  .src { font-size:12px; color:var(--sub); margin:2px 0 8px; font-weight:600; }
  .src b { color:#475569; }
  .fb { font-size:13px; color:#334155; white-space:pre-wrap; background:#FBFCFE; border:1px solid var(--line); border-radius:8px; padding:9px 11px; }
  .q { font-size:12px; color:var(--sub); margin-bottom:6px; } .q b { color:#64748B; }
  .rowcount { font-size:13px; font-weight:700; color:var(--sub); }
  footer { color:var(--sub); font-size:12px; text-align:center; margin-top:28px; }
  @media (max-width:980px){ .layout{grid-template-columns:1fr;} .side{position:static;max-height:none;} .kpis{grid-template-columns:repeat(2,1fr);} .grid2{grid-template-columns:1fr;} }
</style>
</head>
<body>
<div class="wrap">
  <header class="rpt">
    <div class="eyebrow">NEXUS · 레드팀 피드백 다차원 분류</div>
    <h1>레드팀 1·2·3주차 피드백 분류 리포트</h1>
    <div class="meta">__META__</div>
  </header>

  <div class="layout">
    <aside class="side" id="side"></aside>
    <main>
      <div class="kpis" id="kpis"></div>
      <div class="insight"><h2>핵심 요약</h2><p id="insight"></p></div>
      <div class="grid2">
        <div class="panel"><h2>평가축 분포</h2><div class="desc">피드백당 복수 태그 · 중복 카운트</div><div class="chart-box tall"><canvas id="axBar"></canvas></div></div>
        <div class="panel"><h2>극성</h2><div class="desc">긍정·부정·혼합·제안</div><div class="chart-box tall"><canvas id="polDo"></canvas></div></div>
      </div>
      <div class="grid2">
        <div class="panel"><h2>심각도(조치 우선순위)</h2><div class="desc">상·중·하</div><div class="chart-box"><canvas id="sevDo"></canvas></div></div>
        <div class="panel"><h2>주차별 건수</h2><div class="desc">1·2·3주차</div><div class="chart-box"><canvas id="weekBar"></canvas></div></div>
      </div>
      <div class="grid2">
        <div class="panel"><h2>대상 봇별 지적</h2><div class="desc">피드백이 지목한 봇</div><div class="chart-box"><canvas id="botBar"></canvas></div></div>
        <div class="panel"><h2>평가자별 건수</h2><div class="desc">제출자</div><div class="chart-box"><canvas id="subBar"></canvas></div></div>
      </div>
      <div class="panel">
        <h2>주차 × 평가축 히트맵</h2><div class="desc">각 칸은 해당 주차에서 그 평가축이 태깅된 건수</div>
        <div id="heat" class="heat"></div>
      </div>
      <div class="panel">
        <h2>피드백 <span class="rowcount" id="rc"></span></h2>
        <div class="desc">심각도→주차 순 정렬 · 카드마다 평가자·회차·원질문 출처 표기</div>
        <div class="cardlist" id="cards"></div>
      </div>
    </main>
  </div>
  <footer>본 리포트는 레드팀 1·2·3주차 피드백을 codex CLI로 다차원 태깅해 자동 생성했습니다. 봇 명칭은 주차별로 다릅니다(1주차 원문 단일봇 · 2주차 통합/원리/정밀 · 3주차 C/D/적절챗봇).</footer>
</div>
<script>
const DATA = __DATA__;
const R = DATA.recs;
const AC = DATA.AXIS_COLOR, PC = DATA.POL_COLOR, SC = DATA.SEV_COLOR;
Chart.defaults.font.family="-apple-system,Pretendard,'Apple SD Gothic Neo',sans-serif";
Chart.defaults.color="#5A6678";
const esc=s=>(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

// 필터 상태: 각 차원별 Set (비면 전체 통과). 다중값 차원은 교집합 매칭.
const F = {w:new Set(),cat:new Set(),ax:new Set(),pol:new Set(),sev:new Set(),tg:new Set(),sub:new Set(),risk:new Set(),rt:new Set(),faq:new Set(),q:''};

function inter(arr,set){return arr.some(x=>set.has(x));}
function ratingBucket(rt){ if(rt==null) return '무평점'; if(rt<=2) return '1-2'; if(rt<=3) return '3'; if(rt<=4) return '4'; return '5'; }
function filtered(){
  return R.filter(r=>
    (!F.w.size   || F.w.has(String(r.w))) &&
    (!F.cat.size || F.cat.has(r.cat)) &&
    (!F.ax.size  || inter(r.ax,F.ax)) &&
    (!F.pol.size || F.pol.has(r.pol)) &&
    (!F.sev.size || F.sev.has(r.sev)) &&
    (!F.tg.size  || inter(r.tg.concat(r.bots),F.tg)) &&
    (!F.sub.size || F.sub.has(r.sub)) &&
    (!F.risk.size|| F.risk.has(r.risk)) &&
    (!F.rt.size  || F.rt.has(ratingBucket(r.rt))) &&
    (!F.faq.size || F.faq.has(r.faq?'FAQ 발동':'일반 응답')) &&
    (!F.q || (r.fb+r.q+r.sm).toLowerCase().includes(F.q))
  );
}

// ── 사이드 필터 UI ──
function chipGroup(title,dim,values,colorMap){
  let h=`<h3>${title}</h3><div class="fgroup">`;
  values.forEach(v=>{
    const col=colorMap?colorMap[v]:null;
    h+=`<span class="chip" data-dim="${dim}" data-v="${esc(String(v))}"${col?` data-c="1" style="--cc:${col}"`:''}>${esc(String(v))}</span>`;
  });
  return h+`</div>`;
}
function buildSide(){
  const ratingVals=['1-2','3','4','5','무평점'];
  let h='';
  h+=chipGroup('주차','w',DATA.weeks.map(String));
  h+=chipGroup('FAQ 자동응답','faq',['FAQ 발동','일반 응답'],{'FAQ 발동':'#B5321E','일반 응답':'#64748B'});
  h+=chipGroup('심각도','sev',DATA.SEVERITY,SC);
  h+=chipGroup('극성','pol',DATA.POLARITY,PC);
  h+=chipGroup('평가축','ax',DATA.AXES,AC);
  h+=chipGroup('주제 카테고리','cat',DATA.categories);
  h+=chipGroup('대상 봇','tg',DATA.bots);
  h+=chipGroup('위험도','risk',DATA.risks);
  h+=chipGroup('평점','rt',ratingVals);
  h+=chipGroup('평가자','sub',DATA.submitters);
  h+=`<h3>본문 검색</h3><input class="search" id="q" placeholder="키워드…">`;
  h+=`<span class="reset" id="reset">필터 초기화</span>`;
  h+=`<span class="csv" id="csv">현재 결과 CSV 내보내기</span>`;
  document.getElementById('side').innerHTML=h;

  document.querySelectorAll('.chip').forEach(c=>c.addEventListener('click',()=>{
    const dim=c.dataset.dim, v=c.dataset.v;
    if(F[dim].has(v)){F[dim].delete(v);c.classList.remove('on');}
    else{F[dim].add(v);c.classList.add('on');}
    render();
  }));
  let t;document.getElementById('q').addEventListener('input',e=>{clearTimeout(t);t=setTimeout(()=>{F.q=e.target.value.trim().toLowerCase();render();},180);});
  document.getElementById('reset').addEventListener('click',()=>{
    Object.keys(F).forEach(k=>{if(F[k] instanceof Set)F[k].clear();});F.q='';
    document.querySelectorAll('.chip').forEach(c=>c.classList.remove('on'));
    document.getElementById('q').value='';render();
  });
  document.getElementById('csv').addEventListener('click',exportCsv);
}

let charts={};
function mk(id,cfg){if(charts[id])charts[id].destroy();charts[id]=new Chart(document.getElementById(id),cfg);}
function countBy(rows,fn){const m={};rows.forEach(r=>{const ks=fn(r);(Array.isArray(ks)?ks:[ks]).forEach(k=>{if(k!=null)m[k]=(m[k]||0)+1;});});return m;}

function renderKPI(rows){
  const neg=rows.filter(r=>r.pol==='부정'||r.pol==='혼합').length;
  const hi=rows.filter(r=>r.sev==='상').length;
  const safe=rows.filter(r=>r.ax.includes('안전·민감성')).length;
  const faq=rows.filter(r=>r.faq).length;
  document.getElementById('kpis').innerHTML=
    `<div class="kpi"><div class="l">표시 피드백</div><div class="v">${rows.length}<small> 건</small></div></div>`+
    `<div class="kpi" style="border-top-color:#B5321E"><div class="l">FAQ 자동응답</div><div class="v">${faq}<small> 건</small></div></div>`+
    `<div class="kpi" style="border-top-color:${SC['상']}"><div class="l">심각도 상</div><div class="v">${hi}<small> 건</small></div></div>`+
    `<div class="kpi" style="border-top-color:${PC['부정']}"><div class="l">부정·혼합(지적)</div><div class="v">${neg}<small> 건</small></div></div>`+
    `<div class="kpi" style="border-top-color:${AC['안전·민감성']}"><div class="l">안전·민감성 태그</div><div class="v">${safe}<small> 건</small></div></div>`;
}
function renderInsight(rows){
  const ax=countBy(rows,r=>r.ax); const topAx=Object.entries(ax).sort((a,b)=>b[1]-a[1]).slice(0,3);
  const pol=countBy(rows,r=>r.pol);
  const w=countBy(rows,r=>'W'+r.w);
  const txt=`표시된 <b>${rows.length}건</b> 중 가장 많이 지적된 평가축은 `+
    topAx.map(([k,v])=>`<b style="color:${AC[k]||'#475569'}">${k}(${v})</b>`).join(' · ')+
    ` 입니다. 극성은 긍정 ${pol['긍정']||0} · 부정 ${pol['부정']||0} · 혼합 ${pol['혼합']||0} · 제안 ${pol['제안']||0}, `+
    `주차 분포는 1주차 ${w['W1']||0} · 2주차 ${w['W2']||0} · 3주차 ${w['W3']||0} 건입니다.`;
  document.getElementById('insight').innerHTML=txt;
}
function renderCharts(rows){
  const ax=countBy(rows,r=>r.ax);
  const axKeys=DATA.AXES.filter(a=>ax[a]).sort((a,b)=>ax[b]-ax[a]);
  mk('axBar',{type:'bar',data:{labels:axKeys,datasets:[{data:axKeys.map(k=>ax[k]),backgroundColor:axKeys.map(k=>AC[k]),borderRadius:4}]},
    options:{indexAxis:'y',plugins:{legend:{display:false}},scales:{x:{beginAtZero:true,grid:{color:'#EEF1F6'}},y:{grid:{display:false},ticks:{font:{size:11}}}}}});

  const pol=countBy(rows,r=>r.pol);
  mk('polDo',{type:'doughnut',data:{labels:DATA.POLARITY,datasets:[{data:DATA.POLARITY.map(k=>pol[k]||0),backgroundColor:DATA.POLARITY.map(k=>PC[k]),borderWidth:2,borderColor:'#fff'}]},
    options:{plugins:{legend:{position:'right',labels:{boxWidth:12,padding:8}}},cutout:'55%'}});

  const sev=countBy(rows,r=>r.sev);
  mk('sevDo',{type:'doughnut',data:{labels:DATA.SEVERITY,datasets:[{data:DATA.SEVERITY.map(k=>sev[k]||0),backgroundColor:DATA.SEVERITY.map(k=>SC[k]),borderWidth:2,borderColor:'#fff'}]},
    options:{plugins:{legend:{position:'right',labels:{boxWidth:12,padding:8}}},cutout:'55%'}});

  const wk=countBy(rows,r=>'W'+r.w); const wkeys=DATA.weeks.map(w=>'W'+w);
  mk('weekBar',{type:'bar',data:{labels:wkeys.map(k=>k.replace('W','')+'주차'),datasets:[{data:wkeys.map(k=>wk[k]||0),backgroundColor:'#9333EA',borderRadius:4}]},
    options:{plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,grid:{color:'#EEF1F6'}},x:{grid:{display:false}}}}});

  const bot=countBy(rows,r=>r.tg); const bkeys=Object.keys(bot).sort((a,b)=>bot[b]-bot[a]);
  mk('botBar',{type:'bar',data:{labels:bkeys,datasets:[{data:bkeys.map(k=>bot[k]),backgroundColor:'#0891B2',borderRadius:4}]},
    options:{indexAxis:'y',plugins:{legend:{display:false}},scales:{x:{beginAtZero:true,grid:{color:'#EEF1F6'}},y:{grid:{display:false},ticks:{font:{size:11}}}}}});

  const sub=countBy(rows,r=>r.sub); const skeys=Object.keys(sub).sort((a,b)=>sub[b]-sub[a]);
  mk('subBar',{type:'bar',data:{labels:skeys,datasets:[{data:skeys.map(k=>sub[k]),backgroundColor:'#DB2777',borderRadius:4}]},
    options:{indexAxis:'y',plugins:{legend:{display:false}},scales:{x:{beginAtZero:true,grid:{color:'#EEF1F6'}},y:{grid:{display:false},ticks:{font:{size:11}}}}}});
}
function renderHeat(rows){
  const axList=DATA.AXES.filter(a=>a!=='미분류');
  const ws=DATA.weeks;
  const m={};ws.forEach(w=>{axList.forEach(a=>m[w+'|'+a]=0);});
  rows.forEach(r=>r.ax.forEach(a=>{if(m[r.w+'|'+a]!==undefined)m[r.w+'|'+a]++;}));
  let max=1;Object.values(m).forEach(v=>{if(v>max)max=v;});
  const el=document.getElementById('heat');
  el.style.gridTemplateColumns=`120px repeat(${ws.length},1fr)`;
  let h=`<div class="hc hh"></div>`+ws.map(w=>`<div class="hc hh">${w}주차</div>`).join('');
  axList.forEach(a=>{
    h+=`<div class="hc hh" style="text-align:right;padding-right:8px">${a}</div>`;
    ws.forEach(w=>{const v=m[w+'|'+a];const t=v/max;const bg=`rgba(147,51,234,${(0.08+t*0.72).toFixed(2)})`;
      h+=`<div class="hc" style="background:${bg};color:${t>0.5?'#fff':'#1A2233'}">${v||''}</div>`;});
  });
  el.innerHTML=h;
}
const SEV_ORD={'상':0,'중':1,'하':2};
function renderCards(rows){
  document.getElementById('rc').textContent=`(${rows.length}건)`;
  const sorted=rows.slice().sort((a,b)=>(SEV_ORD[a.sev]-SEV_ORD[b.sev])||(a.w-b.w));
  const MAX=400;
  const cards=sorted.slice(0,MAX).map(r=>{
    const axTags=r.ax.map(a=>`<span class="tag ax" style="background:${AC[a]||'#94A3B8'}">${esc(a)}</span>`).join('');
    const tg=r.tg.filter(x=>x!=='전반').map(x=>`<span class="tag" style="background:#475569">${esc(x)}</span>`).join('');
    const faqTag=r.faq?`<span class="tag" style="background:#B5321E" title="FAQ 지정답변 자동응답 발동: ${esc(r.faqb.join(', '))}">FAQ #${r.faqi.join('·')} 발동${r.faqb.length?' ('+esc(r.faqb.join('·'))+')':''}</span>`:'';
    return `<div class="fcard" style="--sev:${r.faq?'#B5321E':SC[r.sev]}">
      <div class="head">
        <span class="sm">${esc(r.sm)}</span>
        ${faqTag}
        <span class="tag pol" style="background:${PC[r.pol]}">${r.pol}</span>
        <span class="tag sev" style="background:${SC[r.sev]}">심각 ${r.sev}</span>
        ${axTags}${tg}
      </div>
      <div class="src">평가자 <b>${esc(r.sub)}</b> · <b>${r.w}주차</b> · ${esc(r.cat)}${r.rt!=null?` · 평점 ${r.rt}`:''}${r.risk!=='없음'?` · 위험도 ${r.risk}`:''}</div>
      <div class="q"><b>원질문</b> ${esc(r.q)}</div>
      <div class="fb">${esc(r.fb)}</div>
    </div>`;
  }).join('');
  const more=sorted.length>MAX?`<div class="desc" style="text-align:center;padding:10px">…상위 ${MAX}건만 표시. 필터로 좁혀 보세요 (전체 ${sorted.length}건).</div>`:'';
  document.getElementById('cards').innerHTML=cards+more;
}
function csvEscape(s){s=(s==null?'':String(s));return /[",\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s;}
function exportCsv(){
  const rows=filtered();
  const head=['id','주차','평가자','카테고리','위험도','평점','대상봇','평가축','극성','심각도','FAQ발동','FAQ봇','FAQ번호','요약','원질문','피드백'];
  const lines=[head.join(',')];
  rows.forEach(r=>lines.push([r.id,r.w,r.sub,r.cat,r.risk,r.rt==null?'':r.rt,r.tg.join('|'),r.ax.join('|'),r.pol,r.sev,r.faq?'발동':'',r.faqb.join('|'),r.faqi.join('|'),r.sm,r.q,r.fb].map(csvEscape).join(',')));
  const blob=new Blob(['﻿'+lines.join('\n')],{type:'text/csv;charset=utf-8'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);
  a.download='레드팀피드백_분류_필터결과.csv';a.click();URL.revokeObjectURL(a.href);
}
function render(){
  const rows=filtered();
  renderKPI(rows);renderInsight(rows);renderCharts(rows);renderHeat(rows);renderCards(rows);
}
buildSide();render();
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()
