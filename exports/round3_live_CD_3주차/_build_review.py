# 위험·저점 72건을 검토자용 읽기전용 인터랙티브 대시보드(단일 HTML)로 출력하는 빌드 스크립트
import json
import pathlib

from _build_report import CATEGORIES  # id→사유 범주 매핑 재사용

OUT_DIR = pathlib.Path(__file__).parent
DATA = OUT_DIR / "_data" / "responses.json"
OUT_HTML = OUT_DIR / "3주차_레드팀_CD_검토대시보드_ver2.html"

GROUP_META = {
    "상": {"label": "위험도 상", "sub": "즉시 차단·수정 검토", "color": "#ff5d5d"},
    "중": {"label": "위험도 중", "sub": "정보 누락·회피·규정 불일치", "color": "#ffb02e"},
    "저점": {"label": "적절성 1·2점", "sub": "적절성·유용성 최저점", "color": "#ff8a4a"},
}


def build_id_tags():
    id_cats = {}
    for gkey, group in CATEGORIES.items():
        for cat in group["cats"]:
            for i in cat["ids"]:
                id_cats.setdefault(i, []).append((gkey, cat["name"]))
    return id_cats


def severity_tags(d):
    tags = []
    if d["risk"] == "상":
        tags.append("위험도 상")
    elif d["risk"] == "중":
        tags.append("위험도 중")
    if d.get("score") == 1:
        tags.append("1점")
    elif d.get("score") == 2:
        tags.append("2점")
    return tags


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    by_id = {d["id"]: d for d in data}
    id_cats = build_id_tags()

    target_ids = sorted(id_cats.keys())
    risk_rank = {"상": 0, "중": 1, "하": 2, "없음": 3}
    target_ids.sort(key=lambda i: (
        risk_rank.get(by_id[i]["risk"], 9),
        by_id[i]["score"] if by_id[i]["score"] is not None else 9,
        i,
    ))

    out = []
    for i in target_ids:
        d = by_id[i]
        names = []
        for _g, name in id_cats.get(i, []):
            if name not in names:
                names.append(name)
        out.append({
            "id": d["id"],
            "evaluator": d.get("evaluator", ""),
            "question": d.get("question", ""),
            "respC": d.get("respC", ""),
            "respD": d.get("respD", ""),
            "score": d.get("score"),
            "good": d.get("good", ""),
            "bad": d.get("bad", ""),
            "suggest": d.get("suggest", ""),
            "riskRaw": d.get("riskRaw", ""),
            "etc": d.get("etc", ""),
            "risk": d["risk"],
            "sev": severity_tags(d),
            "cats": names,
        })

    summary = []
    for gkey in ["상", "중", "저점"]:
        g = CATEGORIES[gkey]
        gm = GROUP_META[gkey]
        cats = sorted(g["cats"], key=lambda c: -len(c["ids"]))
        summary.append({
            "key": gkey, "label": gm["label"], "sub": gm["sub"], "color": gm["color"],
            "cats": [{"name": c["name"], "insight": c["insight"],
                      "ids": [x for x in c["ids"] if x in target_ids]} for c in cats],
        })

    n_sang = sum(1 for o in out if o["risk"] == "상")
    n_jung = sum(1 for o in out if o["risk"] == "중")
    n_low = sum(1 for o in out if o["score"] in (1, 2))

    html = (TEMPLATE
            .replace("__DATA__", json.dumps(out, ensure_ascii=False))
            .replace("__SUMMARY__", json.dumps(summary, ensure_ascii=False))
            .replace("__N_TOTAL__", str(len(out)))
            .replace("__N_SANG__", str(n_sang))
            .replace("__N_JUNG__", str(n_jung))
            .replace("__N_LOW__", str(n_low)))
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"검토 대상 {len(out)}건(상{n_sang}·중{n_jung}·1·2점{n_low}) → {OUT_HTML}")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>3주차 레드팀 · 검토 대시보드 (ver2)</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>
:root{
  --bg:#0c0e13; --panel:#13161d; --panel2:#1a1f2a; --elev:#1f2533;
  --line:#272d3a; --line2:#323a4a;
  --txt:#e9edf4; --mut:#98a2b3; --mut2:#727c8c;
  --acc:#5b8cff; --acc-d:#3f6fe0;
  --sang:#ff5d5d; --jung:#ffb02e; --low:#ff8a4a; --ok:#3ddc97;
  --mono:"Fira Code",ui-monospace,SFMono-Regular,Menlo,monospace;
  --radius:13px; --shadow:0 1px 0 rgba(255,255,255,.02),0 8px 24px rgba(0,0,0,.35);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--txt);
  font-family:"Pretendard","Apple SD Gothic Neo","Noto Sans KR",-apple-system,BlinkMacSystemFont,sans-serif;
  font-size:14px;line-height:1.65;-webkit-font-smoothing:antialiased}
.num{font-family:var(--mono);font-variant-numeric:tabular-nums}
.wrap{max-width:1180px;margin:0 auto;padding:24px 22px 120px}
::selection{background:rgba(91,140,255,.3)}

.top{display:flex;flex-wrap:wrap;gap:16px;align-items:flex-end;justify-content:space-between;margin-bottom:6px}
h1{font-size:21px;margin:0;letter-spacing:-.01em}
.sub{color:var(--mut);font-size:12.5px;margin-top:4px}
.actions{display:flex;gap:8px;flex-wrap:wrap}
.btn{display:inline-flex;align-items:center;gap:6px;background:var(--panel2);border:1px solid var(--line2);
  color:var(--txt);border-radius:9px;padding:8px 13px;font-size:12.5px;cursor:pointer;
  transition:border-color .18s,background .18s,transform .06s;font-family:inherit}
.btn:hover{border-color:var(--acc);background:var(--elev)}
.btn:active{transform:translateY(1px)}
.btn:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
.btn svg{width:15px;height:15px;stroke:currentColor;fill:none;stroke-width:2}

.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:14px 16px;box-shadow:var(--shadow)}
.kpi .big{font-size:25px;font-weight:700}
.kpi .lab{color:var(--mut);font-size:11.5px;margin-top:2px}

.sec-h{font-size:14px;font-weight:700;margin:26px 0 12px;display:flex;align-items:center;gap:9px}
.sec-h .ln{flex:1;height:1px;background:var(--line)}
.sgrid{display:grid;grid-template-columns:1fr 1fr;gap:13px}
@media(max-width:780px){.sgrid{grid-template-columns:1fr}}
.scard{background:var(--panel);border:1px solid var(--line);border-left:4px solid;border-radius:var(--radius);
  padding:14px 16px;box-shadow:var(--shadow)}
.scard .gh{display:flex;align-items:center;gap:9px;margin-bottom:4px}
.gpill{font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;color:#0c0e13}
.scard .gs{color:var(--mut);font-size:11.5px}
.cat{padding:10px 0;border-top:1px solid var(--line)}
.cat:first-of-type{border-top:none}
.cat .ch{display:flex;align-items:baseline;gap:8px}
.cat .cn{font-weight:600;font-size:13px}
.cat .cc{font-size:11px;color:var(--mut);font-family:var(--mono)}
.cat .ci{color:var(--mut);font-size:12px;margin:3px 0 7px;line-height:1.5}
.chips{display:flex;flex-wrap:wrap;gap:5px}
.chip{display:inline-flex;align-items:center;gap:5px;font-size:11px;background:var(--panel2);
  border:1px solid var(--line2);border-radius:7px;padding:4px 8px;cursor:pointer;color:var(--mut);
  max-width:240px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  transition:border-color .16s,color .16s,background .16s;font-family:inherit}
.chip:hover{border-color:var(--acc);color:var(--txt);background:var(--elev)}
.chip:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
.chip b{color:var(--acc);font-family:var(--mono)}

.filters{position:sticky;top:0;z-index:30;background:rgba(12,14,19,.86);backdrop-filter:blur(10px);
  border:1px solid var(--line);border-radius:var(--radius);padding:11px 13px;margin:8px 0 14px}
.frow{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:4px 0}
.frow .gl{color:var(--mut2);font-size:11px;width:58px;flex:0 0 58px}
.fchip{font-size:12px;border:1px solid var(--line2);background:var(--panel2);color:var(--mut);
  border-radius:20px;padding:4px 11px;cursor:pointer;transition:.16s;font-family:inherit}
.fchip:hover{color:var(--txt);border-color:var(--acc)}
.fchip.on{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:600}
.fchip.on.r상{background:var(--sang);border-color:var(--sang)}
.fchip.on.r중{background:var(--jung);border-color:var(--jung);color:#1a1a1a}
.search{flex:1;min-width:200px;display:flex;align-items:center;gap:8px;background:#0a0c11;
  border:1px solid var(--line2);border-radius:9px;padding:7px 11px}
.search svg{width:15px;height:15px;stroke:var(--mut);fill:none;stroke-width:2;flex:0 0 15px}
.search input{flex:1;background:none;border:none;color:var(--txt);font-size:13px;outline:none;font-family:inherit}
.count{color:var(--mut);font-size:12px;margin:2px 2px 12px}

.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);
  margin:0 0 14px;box-shadow:var(--shadow);overflow:hidden;scroll-margin-top:120px}
.card.flash{animation:flash 1.6s ease}
@keyframes flash{0%,30%{box-shadow:0 0 0 2px var(--acc),var(--shadow)}100%{box-shadow:var(--shadow)}}
.chead{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:13px 16px;border-bottom:1px solid var(--line)}
.qid{font-family:var(--mono);font-weight:600;color:var(--acc);font-size:13px}
.tag{font-size:10.5px;padding:2px 8px;border-radius:20px;white-space:nowrap;border:1px solid transparent}
.tag.t상{background:rgba(255,93,93,.16);color:#ff9a9a;border-color:rgba(255,93,93,.35)}
.tag.t중{background:rgba(255,176,46,.15);color:#ffce7a;border-color:rgba(255,176,46,.35)}
.tag.t1점{background:rgba(255,93,93,.14);color:#ffa3a3}
.tag.t2점{background:rgba(255,138,74,.16);color:#ffb98a}
.tag.cat{background:var(--panel2);color:var(--mut);border-color:var(--line2);font-size:10px}
.chead .meta{margin-left:auto;color:var(--mut2);font-size:11.5px;display:flex;gap:10px;align-items:center}
.cbody{padding:14px 16px}
.q{font-size:15px;font-weight:600;line-height:1.55;margin:0 0 12px}
.q .qlab{display:block;font-size:10.5px;color:var(--mut2);font-weight:500;margin-bottom:3px;letter-spacing:.04em}

.fb{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-bottom:12px}
@media(max-width:680px){.fb{grid-template-columns:1fr}}
.fb .it{background:var(--panel2);border:1px solid var(--line);border-radius:9px;padding:9px 11px}
.fb .it.full{grid-column:1/-1}
.fb .k{font-size:10.5px;color:var(--mut2);margin-bottom:3px;letter-spacing:.03em}
.fb .v{font-size:12.5px;white-space:pre-wrap;word-break:break-word;color:#cfd6e1}
.fb .it.bad{border-color:rgba(255,138,74,.3)} .fb .it.bad .k{color:var(--low)}
.fb .it.sug{border-color:rgba(91,140,255,.28)} .fb .it.sug .k{color:var(--acc)}

.resp-toggle{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--mut);
  cursor:pointer;background:none;border:none;padding:6px 0;font-family:inherit}
.resp-toggle:hover{color:var(--txt)}
.resp-toggle svg{width:13px;height:13px;stroke:currentColor;fill:none;stroke-width:2;transition:transform .2s}
.resp-toggle[aria-expanded=true] svg{transform:rotate(90deg)}
.resps{display:none;grid-template-columns:1fr 1fr;gap:10px;margin:6px 0 4px}
.resps.open{display:grid}
@media(max-width:780px){.resps{grid-template-columns:1fr}}
.resp{background:#0a0c11;border:1px solid var(--line);border-left:3px solid;border-radius:9px;padding:9px 12px}
.resp.C{border-left-color:var(--ok)} .resp.D{border-left-color:#7c5bff}
.resp h4{margin:0 0 5px;font-size:11px;color:var(--mut)}
.resp.C h4{color:var(--ok)} .resp.D h4{color:#a892ff}
.resp .t{font-size:12px;white-space:pre-wrap;word-break:break-word;color:#c4ccd8;max-height:320px;overflow:auto;line-height:1.55}

.empty{text-align:center;color:var(--mut);padding:60px 20px;background:var(--panel);
  border:1px dashed var(--line2);border-radius:var(--radius)}
.fab{position:fixed;right:22px;bottom:24px;z-index:40;width:46px;height:46px;border-radius:50%;
  background:var(--acc-d);border:1px solid var(--acc);color:#fff;cursor:pointer;display:none;
  align-items:center;justify-content:center;box-shadow:0 8px 24px rgba(0,0,0,.5)}
.fab.show{display:flex}
.fab svg{width:20px;height:20px;stroke:currentColor;fill:none;stroke-width:2.2}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div>
      <h1>3주차 레드팀 · 라이브 C/D 검토 대시보드</h1>
      <div class="sub">위험도 상·중 + 적절성 1·2점 <b class="num">__N_TOTAL__</b>건 · 사유별 분류 + 평가자 피드백 + 챗봇 C·D 응답 원문을 검토용으로 정리 (읽기 전용)</div>
    </div>
    <div class="actions">
      <button class="btn" id="expAll"><svg viewBox="0 0 24 24"><path d="M4 9V4h5M20 15v5h-5M4 4l6 6M20 20l-6-6"/></svg>응답 전체 펼치기</button>
    </div>
  </div>

  <div class="kpis">
    <div class="kpi"><div class="big num">__N_TOTAL__</div><div class="lab">검토 대상</div></div>
    <div class="kpi"><div class="big num" style="color:var(--sang)">__N_SANG__</div><div class="lab">위험도 상</div></div>
    <div class="kpi"><div class="big num" style="color:var(--jung)">__N_JUNG__</div><div class="lab">위험도 중</div></div>
    <div class="kpi"><div class="big num" style="color:var(--low)">__N_LOW__</div><div class="lab">적절성 1·2점</div></div>
  </div>

  <div class="sec-h">사유별 분류 요약 <span class="ln"></span> <span style="font-weight:400;color:var(--mut);font-size:12px">칩 클릭 → 해당 항목으로 이동</span></div>
  <div class="sgrid" id="summary"></div>

  <div class="sec-h">항목 검토 <span class="ln"></span></div>
  <div class="filters">
    <div class="frow"><span class="gl">위험도</span><span id="fRisk"></span></div>
    <div class="frow"><span class="gl">점수</span><span id="fScore"></span></div>
    <div class="frow">
      <div class="search"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4-4"/></svg>
        <input id="q" type="search" placeholder="질문·응답·피드백 검색…" aria-label="검색"></div>
      <button class="btn" id="reset">필터 초기화</button>
    </div>
  </div>
  <div class="count" id="count"></div>
  <div id="list"></div>
</div>

<button class="fab" id="toTop" aria-label="맨 위로"><svg viewBox="0 0 24 24"><path d="M12 19V5M5 12l7-7 7 7"/></svg></button>

<script>
const DATA = __DATA__;
const SUMMARY = __SUMMARY__;
const esc = s => (s||"").replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
const byId = Object.fromEntries(DATA.map(d=>[d.id,d]));

// ---- summary ----
function renderSummary(){
  document.getElementById("summary").innerHTML = SUMMARY.map(g=>{
    const cats = g.cats.map(c=>{
      const chips = c.ids.map(id=>{
        const d=byId[id]; if(!d) return "";
        return `<button class="chip" onclick="jump(${id})" title="${esc(d.question)}"><b>#${id}</b> ${esc(d.question.slice(0,26))}</button>`;
      }).join("");
      return `<div class="cat"><div class="ch"><span class="cn">${esc(c.name)}</span><span class="cc">${c.ids.length}건</span></div>
        <div class="ci">${esc(c.insight)}</div><div class="chips">${chips}</div></div>`;
    }).join("");
    return `<div class="scard" style="border-left-color:${g.color}">
      <div class="gh"><span class="gpill" style="background:${g.color}">${esc(g.label)}</span>
      <span class="gs">${esc(g.sub)} · ${g.cats.reduce((a,c)=>a+c.ids.length,0)}건 · ${g.cats.length}개 범주</span></div>
      ${cats}</div>`;
  }).join("");
}

// ---- filters ----
const F={risk:new Set(),score:new Set(),text:""};
function chipset(host,items,key,clsPfx){
  document.getElementById(host).innerHTML=items.map(it=>
    `<button class="fchip ${clsPfx?clsPfx+it[0]:""}" data-k="${key}" data-v="${it[0]}">${esc(it[1])}</button>`).join("");
}
function buildFilters(){
  chipset("fRisk",[["상","위험도 상"],["중","위험도 중"]],"risk","r");
  const scores=[...new Set(DATA.map(d=>d.score).filter(v=>v!=null))].sort((a,b)=>a-b);
  chipset("fScore",scores.map(s=>[String(s),s+"점"]),"score","");
  document.querySelectorAll(".fchip").forEach(b=>b.onclick=()=>{
    const k=b.dataset.k,v=b.dataset.v;
    F[k].has(v)?F[k].delete(v):F[k].add(v); b.classList.toggle("on"); render();
  });
}
function match(d){
  if(F.risk.size && !F.risk.has(d.risk)) return false;
  if(F.score.size && !F.score.has(String(d.score))) return false;
  if(F.text){
    const hay=(d.question+d.respC+d.respD+d.good+d.bad+d.suggest+d.etc+d.cats.join(" ")).toLowerCase();
    if(!hay.includes(F.text)) return false;
  }
  return true;
}

// ---- card ----
function tagHtml(d){
  let t=d.sev.map(s=>`<span class="tag t${s.replace('위험도 ','')}">${esc(s)}</span>`).join("");
  t+=d.cats.map(c=>`<span class="tag cat">${esc(c)}</span>`).join("");
  return t;
}
function card(d){
  const fb=[
    d.bad?`<div class="it bad"><div class="k">아쉬운 점</div><div class="v">${esc(d.bad)}</div></div>`:"",
    d.suggest?`<div class="it sug"><div class="k">보완·제안</div><div class="v">${esc(d.suggest)}</div></div>`:"",
    d.good?`<div class="it"><div class="k">좋았던 점</div><div class="v">${esc(d.good)}</div></div>`:"",
    d.riskRaw?`<div class="it"><div class="k">위험도(원문)</div><div class="v">${esc(d.riskRaw)}</div></div>`:"",
    d.etc?`<div class="it full"><div class="k">기타 의견</div><div class="v">${esc(d.etc)}</div></div>`:"",
  ].filter(Boolean).join("");
  return `<div class="card" id="c${d.id}" data-id="${d.id}">
    <div class="chead">
      <span class="qid">#${d.id}</span>${tagHtml(d)}
      <span class="meta"><span>${esc(d.evaluator)}</span><span class="num">적절성 ${d.score??'-'}점</span></span>
    </div>
    <div class="cbody">
      <div class="q"><span class="qlab">질문</span>${esc(d.question)}</div>
      <div class="fb">${fb}</div>
      <button class="resp-toggle" aria-expanded="false" onclick="toggleResp(this)"><svg viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></svg>챗봇 C·D 응답 원문 보기</button>
      <div class="resps">
        <div class="resp C"><h4>챗봇 C</h4><div class="t">${esc(d.respC)||'—'}</div></div>
        <div class="resp D"><h4>챗봇 D</h4><div class="t">${esc(d.respD)||'—'}</div></div>
      </div>
    </div>
  </div>`;
}
function render(){
  const rows=DATA.filter(match);
  document.getElementById("count").innerHTML=`<b class="num">${rows.length}</b> / ${DATA.length}건 표시`;
  const list=document.getElementById("list");
  list.innerHTML = rows.length ? rows.map(card).join("")
    : `<div class="empty">조건에 맞는 항목이 없습니다.<br>필터를 초기화해 보세요.</div>`;
}

function toggleResp(btn){
  const open=btn.getAttribute("aria-expanded")==="true";
  btn.setAttribute("aria-expanded",String(!open));
  btn.nextElementSibling.classList.toggle("open",!open);
  btn.lastChild.textContent = open?" 챗봇 C·D 응답 원문 보기":" 응답 원문 접기";
}
function jump(id){
  const card=document.getElementById("c"+id);
  if(!card){ document.getElementById("reset").click(); }
  requestAnimationFrame(()=>{
    const el=document.getElementById("c"+id); if(!el) return;
    el.scrollIntoView({behavior:"smooth",block:"center"});
    el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash");
  });
}
window.jump=jump; window.toggleResp=toggleResp;

// ---- toolbar ----
document.getElementById("reset").onclick=()=>{
  F.risk.clear();F.score.clear();F.text="";
  document.getElementById("q").value="";
  document.querySelectorAll(".fchip.on").forEach(c=>c.classList.remove("on"));
  render();
};
document.getElementById("q").oninput=e=>{F.text=e.target.value.toLowerCase().trim();render();};
let allOpen=false;
document.getElementById("expAll").onclick=()=>{
  allOpen=!allOpen;
  document.querySelectorAll(".resp-toggle").forEach(b=>{
    if((b.getAttribute("aria-expanded")==="true")!==allOpen) toggleResp(b);
  });
  document.getElementById("expAll").lastChild.textContent=allOpen?"응답 전체 접기":"응답 전체 펼치기";
};
const toTop=document.getElementById("toTop");
window.addEventListener("scroll",()=>toTop.classList.toggle("show",scrollY>600),{passive:true});
toTop.onclick=()=>scrollTo({top:0,behavior:"smooth"});

// ---- init ----
buildFilters(); renderSummary(); render();
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()
