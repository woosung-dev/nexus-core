# 전체 268건을 ver2 스타일 읽기전용 대시보드(개요 차트+전체 필터)로 출력하는 빌드 스크립트
import json
import collections
import statistics
import pathlib

from _build_report import CATEGORIES  # id→사유 범주 매핑 재사용

OUT_DIR = pathlib.Path(__file__).parent
DATA = OUT_DIR / "_data" / "responses.json"
OUT_HTML = OUT_DIR / "3주차_레드팀_CD_전체대시보드_ver2.html"

GROUP_META = {
    "상": {"label": "위험도 상", "sub": "즉시 차단·수정 검토", "color": "#ff5d5d"},
    "중": {"label": "위험도 중", "sub": "정보 누락·회피·규정 불일치", "color": "#ffb02e"},
    "저점": {"label": "적절성 1·2점", "sub": "적절성·유용성 최저점", "color": "#ff8a4a"},
}
PREF_LABEL = {"D": "챗봇D · 여정 동반자", "C": "챗봇C · 따뜻한 실무안내자",
              "둘다부적절": "둘다 적절하지 못함", "B": "챗봇B(정밀) 라벨",
              "A": "챗봇A(통합) 라벨", "기타": "기타"}


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
    flagged = set(id_cats.keys())

    risk_rank = {"상": 0, "중": 1, "하": 2, "없음": 3}
    all_ids = sorted(by_id.keys(), key=lambda i: (
        risk_rank.get(by_id[i]["risk"], 9),
        by_id[i]["score"] if by_id[i]["score"] is not None else 9,
        i,
    ))

    out = []
    for i in all_ids:
        d = by_id[i]
        names = []
        for _g, name in id_cats.get(i, []):
            if name not in names:
                names.append(name)
        out.append({
            "id": d["id"], "evaluator": d.get("evaluator", ""),
            "question": d.get("question", ""),
            "respC": d.get("respC", ""), "respD": d.get("respD", ""),
            "prefRaw": d.get("prefRaw", ""), "pref": d.get("pref", "기타"),
            "score": d.get("score"),
            "good": d.get("good", ""), "bad": d.get("bad", ""),
            "suggest": d.get("suggest", ""), "riskRaw": d.get("riskRaw", ""),
            "etc": d.get("etc", ""), "risk": d["risk"],
            "sev": severity_tags(d), "cats": names,
        })

    summary = []
    for gkey in ["상", "중", "저점"]:
        g = CATEGORIES[gkey]
        gm = GROUP_META[gkey]
        cats = sorted(g["cats"], key=lambda c: -len(c["ids"]))
        summary.append({"key": gkey, "label": gm["label"], "sub": gm["sub"], "color": gm["color"],
                        "cats": [{"name": c["name"], "insight": c["insight"], "ids": list(c["ids"])} for c in cats]})

    scores = [d["score"] for d in data if d["score"] is not None]
    stats = {
        "n": len(data),
        "evaluators": len({d["evaluator"] for d in data if d["evaluator"]}),
        "avg": round(statistics.mean(scores), 2) if scores else None,
        "pref": collections.Counter(d["pref"] for d in data).most_common(),
        "risk": {k: sum(1 for d in data if d["risk"] == k) for k in ["상", "중", "하", "없음"]},
        "score": {str(k): sum(1 for d in data if d["score"] == k) for k in [5, 4, 3, 2, 1]},
        "evlist": collections.Counter(d["evaluator"] for d in data if d["evaluator"]).most_common(),
        "flagged": len(flagged),
    }

    html = (TEMPLATE
            .replace("__DATA__", json.dumps(out, ensure_ascii=False))
            .replace("__SUMMARY__", json.dumps(summary, ensure_ascii=False))
            .replace("__STATS__", json.dumps(stats, ensure_ascii=False))
            .replace("__PREF_LABEL__", json.dumps(PREF_LABEL, ensure_ascii=False)))
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"전체 {stats['n']}건(주요이슈 {stats['flagged']}건) → {OUT_HTML}")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>3주차 레드팀 · 전체 대시보드 (ver2)</title>
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
  --sang:#ff5d5d; --jung:#ffb02e; --low:#ff8a4a; --ha:#5b8cff; --none:#3a414f; --ok:#3ddc97;
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

.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(135px,1fr));gap:12px;margin:18px 0}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:14px 16px;box-shadow:var(--shadow)}
.kpi .big{font-size:24px;font-weight:700}
.kpi .lab{color:var(--mut);font-size:11.5px;margin-top:2px}

.sec-h{font-size:14px;font-weight:700;margin:26px 0 12px;display:flex;align-items:center;gap:9px}
.sec-h .ln{flex:1;height:1px;background:var(--line)}

.charts{display:grid;grid-template-columns:1fr 1fr 1fr;gap:13px}
@media(max-width:880px){.charts{grid-template-columns:1fr}}
.chart{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:14px 16px;box-shadow:var(--shadow)}
.chart h3{margin:0 0 10px;font-size:12.5px;font-weight:700;color:var(--txt)}
.bar{display:flex;align-items:center;gap:9px;margin:6px 0;font-size:11.5px}
.bar .bl{width:108px;flex:0 0 108px;color:var(--mut);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar .bt{flex:1;height:14px;background:#0a0c11;border-radius:5px;overflow:hidden}
.bar .bf{height:100%;border-radius:5px;min-width:3px}
.bar .bn{width:62px;flex:0 0 62px;text-align:right;font-family:var(--mono);color:var(--txt)}

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
.foldbtn{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--mut);cursor:pointer;
  background:none;border:none;font-family:inherit}
.foldbtn svg{width:13px;height:13px;stroke:currentColor;fill:none;stroke-width:2;transition:transform .2s}
.foldbtn[aria-expanded=true] svg{transform:rotate(90deg)}

.filters{position:sticky;top:0;z-index:30;background:rgba(12,14,19,.86);backdrop-filter:blur(10px);
  border:1px solid var(--line);border-radius:var(--radius);padding:11px 13px;margin:8px 0 14px}
.frow{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:4px 0}
.frow .gl{color:var(--mut2);font-size:11px;width:58px;flex:0 0 58px;padding-top:5px}
.fchip{font-size:12px;border:1px solid var(--line2);background:var(--panel2);color:var(--mut);
  border-radius:20px;padding:4px 11px;cursor:pointer;transition:.16s;font-family:inherit}
.fchip:hover{color:var(--txt);border-color:var(--acc)}
.fchip.on{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:600}
.fchip.on.r상{background:var(--sang);border-color:var(--sang)}
.fchip.on.r중{background:var(--jung);border-color:var(--jung);color:#1a1a1a}
.fchip.on.r하{background:var(--ha);border-color:var(--ha)}
.fchip.on.r없음{background:var(--none);border-color:var(--none)}
.fwrap{display:flex;flex-wrap:wrap;gap:6px}
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
.tag.t하{background:rgba(91,140,255,.14);color:#9cc2ff;border-color:rgba(91,140,255,.3)}
.tag.t없음{background:var(--panel2);color:var(--mut2);border-color:var(--line2)}
.tag.t1점{background:rgba(255,93,93,.14);color:#ffa3a3}
.tag.t2점{background:rgba(255,138,74,.16);color:#ffb98a}
.tag.cat{background:var(--panel2);color:var(--mut);border-color:var(--line2);font-size:10px}
.tag.pref{background:rgba(124,91,255,.14);color:#b7a4ff;border-color:rgba(124,91,255,.3)}
.tag.pref.C{background:rgba(61,220,151,.13);color:#7fe9c6;border-color:rgba(61,220,151,.3)}
.tag.pref.both{background:var(--panel2);color:var(--mut);border-color:var(--line2)}
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
.nofb{color:var(--mut2);font-size:12px;margin-bottom:10px}

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
      <h1>3주차 레드팀 · 라이브 C/D 전체 대시보드</h1>
      <div class="sub">전체 응답 <b class="num" id="sN"></b>건 전수 보기 · 위험도·점수·평가자·선호봇 필터 · 주요 이슈 바로가기 (읽기 전용)</div>
    </div>
    <div class="actions">
      <button class="btn" id="expAll"><svg viewBox="0 0 24 24"><path d="M4 9V4h5M20 15v5h-5M4 4l6 6M20 20l-6-6"/></svg>응답 전체 펼치기</button>
    </div>
  </div>

  <div class="kpis" id="kpis"></div>

  <div class="sec-h">개요 <span class="ln"></span></div>
  <div class="charts">
    <div class="chart"><h3>선호 챗봇</h3><div id="chPref"></div></div>
    <div class="chart"><h3>위험도</h3><div id="chRisk"></div></div>
    <div class="chart"><h3>적절성 점수</h3><div id="chScore"></div></div>
  </div>

  <div class="sec-h">주요 이슈 바로가기 <span class="ln"></span>
    <button class="foldbtn" id="foldSum" aria-expanded="true"><svg viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></svg>접기</button></div>
  <div class="sgrid" id="summary"></div>

  <div class="sec-h">전체 항목 <span class="ln"></span></div>
  <div class="filters">
    <div class="frow"><span class="gl">위험도</span><span id="fRisk"></span></div>
    <div class="frow"><span class="gl">점수</span><span id="fScore"></span></div>
    <div class="frow"><span class="gl">선호봇</span><span id="fPref"></span></div>
    <div class="frow"><span class="gl">평가자</span><span class="fwrap" id="fEv"></span></div>
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
const ST = __STATS__;
const PREF_LABEL = __PREF_LABEL__;
const esc = s => (s||"").replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
const byId = Object.fromEntries(DATA.map(d=>[d.id,d]));
const PREF_COLOR={D:"#7c5bff",C:"#3ddc97","둘다부적절":"#8a93a3",A:"#ffb02e",B:"#ffb02e","기타":"#666"};
const RISK_COLOR={"상":"#ff5d5d","중":"#ffb02e","하":"#5b8cff","없음":"#3a414f"};
const SCORE_COLOR={"5":"#3ddc97","4":"#7cc36a","3":"#ffb02e","2":"#ff8a4a","1":"#ff5d5d"};

document.getElementById("sN").textContent=ST.n;

// ---- KPI ----
const cD=ST.pref.find(p=>p[0]==="D"), cC=ST.pref.find(p=>p[0]==="C");
document.getElementById("kpis").innerHTML=[
  ["총 응답",ST.n,""],["평가자",ST.evaluators+"명",""],["평균 적절성",ST.avg,"5점 척도"],
  ["챗봇D 선호",cD?cD[1]:0,""],["챗봇C 선호",cC?cC[1]:0,""],
  ["위험도 상",ST.risk["상"],"var(--sang)"],["위험도 중",ST.risk["중"],"var(--jung)"],
  ["주요 이슈",ST.flagged,"상·중·1·2점"],
].map(k=>`<div class="kpi"><div class="big num" ${k[2]&&k[2].startsWith('var')?`style="color:${k[2]}"`:''}>${k[1]}</div><div class="lab">${k[0]}${k[2]&&!k[2].startsWith('var')?` · ${k[2]}`:''}</div></div>`).join("");

// ---- charts ----
function bars(host,rows,total,colorFn){
  const max=Math.max(...rows.map(r=>r[1]),1);
  document.getElementById(host).innerHTML=rows.map(r=>{
    const pct=(r[1]/max*100).toFixed(1);
    const nt=total?`${r[1]} · ${(r[1]/total*100).toFixed(0)}%`:`${r[1]}`;
    return `<div class="bar"><div class="bl" title="${esc(r[0])}">${esc(r[0])}</div>
      <div class="bt"><div class="bf" style="width:${pct}%;background:${colorFn(r)}"></div></div>
      <div class="bn">${nt}</div></div>`;
  }).join("");
}
bars("chPref",ST.pref.map(p=>[PREF_LABEL[p[0]]||p[0],p[1],p[0]]),ST.n,r=>PREF_COLOR[r[2]]||"#666");
bars("chRisk",["상","중","하","없음"].map(k=>[k,ST.risk[k],k]),ST.n,r=>RISK_COLOR[r[2]]);
bars("chScore",["5","4","3","2","1"].map(k=>[k+"점",ST.score[k]||0,k]),ST.n,r=>SCORE_COLOR[r[2]]);

// ---- summary ----
function renderSummary(){
  document.getElementById("summary").innerHTML=SUMMARY.map(g=>{
    const cats=g.cats.map(c=>{
      const chips=c.ids.map(id=>{const d=byId[id];if(!d)return"";
        return `<button class="chip" onclick="jump(${id})" title="${esc(d.question)}"><b>#${id}</b> ${esc(d.question.slice(0,26))}</button>`;}).join("");
      return `<div class="cat"><div class="ch"><span class="cn">${esc(c.name)}</span><span class="cc">${c.ids.length}건</span></div>
        <div class="ci">${esc(c.insight)}</div><div class="chips">${chips}</div></div>`;}).join("");
    return `<div class="scard" style="border-left-color:${g.color}">
      <div class="gh"><span class="gpill" style="background:${g.color}">${esc(g.label)}</span>
      <span class="gs">${esc(g.sub)} · ${g.cats.reduce((a,c)=>a+c.ids.length,0)}건 · ${g.cats.length}개 범주</span></div>${cats}</div>`;
  }).join("");
}

// ---- filters ----
const F={risk:new Set(),score:new Set(),pref:new Set(),ev:new Set(),text:""};
function chipset(host,items,key,clsPfx){
  document.getElementById(host).innerHTML=items.map(it=>
    `<button class="fchip ${clsPfx?clsPfx+it[0]:""}" data-k="${key}" data-v="${it[0]}">${esc(it[1])}<span style="opacity:.6"> ${it[2]??""}</span></button>`).join("");
}
function buildFilters(){
  chipset("fRisk",["상","중","하","없음"].map(k=>[k,k,ST.risk[k]]),"risk","r");
  const scores=[...new Set(DATA.map(d=>d.score).filter(v=>v!=null))].sort((a,b)=>b-a);
  chipset("fScore",scores.map(s=>[String(s),s+"점",ST.score[String(s)]||""]),"score","");
  chipset("fPref",ST.pref.map(p=>[p[0],PREF_LABEL[p[0]]||p[0],p[1]]),"pref","");
  chipset("fEv",ST.evlist.map(e=>[e[0],e[0],e[1]]),"ev","");
  document.querySelectorAll(".fchip").forEach(b=>b.onclick=()=>{
    const k=b.dataset.k,v=b.dataset.v;
    F[k].has(v)?F[k].delete(v):F[k].add(v); b.classList.toggle("on"); render();});
}
function match(d){
  if(F.risk.size && !F.risk.has(d.risk)) return false;
  if(F.score.size && !F.score.has(String(d.score))) return false;
  if(F.pref.size && !F.pref.has(d.pref)) return false;
  if(F.ev.size && !F.ev.has(d.evaluator)) return false;
  if(F.text){const hay=(d.question+d.respC+d.respD+d.good+d.bad+d.suggest+d.etc+d.cats.join(" ")).toLowerCase();
    if(!hay.includes(F.text)) return false;}
  return true;
}

// ---- card ----
function tagHtml(d){
  let t=`<span class="tag t${d.risk}">위험도 ${d.risk}</span>`;
  if(d.score===1) t+=`<span class="tag t1점">1점</span>`;
  else if(d.score===2) t+=`<span class="tag t2점">2점</span>`;
  const pc=d.pref==="C"?"C":(d.pref==="D"?"":"both");
  if(d.pref==="C"||d.pref==="D") t+=`<span class="tag pref ${pc}">${esc(PREF_LABEL[d.pref])}</span>`;
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
  const fbBlock = fb?`<div class="fb">${fb}</div>`:`<div class="nofb">평가자 추가 피드백 없음 (선택·점수만 제출)</div>`;
  return `<div class="card" id="c${d.id}" data-id="${d.id}">
    <div class="chead"><span class="qid">#${d.id}</span>${tagHtml(d)}
      <span class="meta"><span>${esc(d.evaluator)}</span><span class="num">적절성 ${d.score??'-'}점</span></span></div>
    <div class="cbody">
      <div class="q"><span class="qlab">질문</span>${esc(d.question)}</div>
      ${fbBlock}
      <button class="resp-toggle" aria-expanded="false" onclick="toggleResp(this)"><svg viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></svg>챗봇 C·D 응답 원문 보기</button>
      <div class="resps">
        <div class="resp C"><h4>챗봇 C</h4><div class="t">${esc(d.respC)||'—'}</div></div>
        <div class="resp D"><h4>챗봇 D</h4><div class="t">${esc(d.respD)||'—'}</div></div>
      </div></div></div>`;
}
function render(){
  const rows=DATA.filter(match);
  document.getElementById("count").innerHTML=`<b class="num">${rows.length}</b> / ${DATA.length}건 표시`;
  const list=document.getElementById("list");
  list.innerHTML=rows.length?rows.map(card).join(""):`<div class="empty">조건에 맞는 항목이 없습니다.<br>필터를 초기화해 보세요.</div>`;
}

function toggleResp(btn){
  const open=btn.getAttribute("aria-expanded")==="true";
  btn.setAttribute("aria-expanded",String(!open));
  btn.nextElementSibling.classList.toggle("open",!open);
  btn.lastChild.textContent=open?" 챗봇 C·D 응답 원문 보기":" 응답 원문 접기";
}
function jump(id){
  if(!document.getElementById("c"+id)) document.getElementById("reset").click();
  requestAnimationFrame(()=>{const el=document.getElementById("c"+id);if(!el)return;
    el.scrollIntoView({behavior:"smooth",block:"center"});
    el.classList.remove("flash");void el.offsetWidth;el.classList.add("flash");});
}
window.jump=jump; window.toggleResp=toggleResp;

document.getElementById("reset").onclick=()=>{
  ["risk","score","pref","ev"].forEach(k=>F[k].clear());F.text="";
  document.getElementById("q").value="";
  document.querySelectorAll(".fchip.on").forEach(c=>c.classList.remove("on"));render();
};
document.getElementById("q").oninput=e=>{F.text=e.target.value.toLowerCase().trim();render();};
let allOpen=false;
document.getElementById("expAll").onclick=()=>{
  allOpen=!allOpen;
  document.querySelectorAll(".resp-toggle").forEach(b=>{if((b.getAttribute("aria-expanded")==="true")!==allOpen)toggleResp(b);});
  document.getElementById("expAll").lastChild.textContent=allOpen?"응답 전체 접기":"응답 전체 펼치기";
};
document.getElementById("foldSum").onclick=function(){
  const open=this.getAttribute("aria-expanded")==="true";
  this.setAttribute("aria-expanded",String(!open));
  document.getElementById("summary").style.display=open?"none":"grid";
  this.lastChild.textContent=open?"펼치기":"접기";
};
const toTop=document.getElementById("toTop");
window.addEventListener("scroll",()=>toTop.classList.toggle("show",scrollY>600),{passive:true});
toTop.onclick=()=>scrollTo({top:0,behavior:"smooth"});

buildFilters(); renderSummary(); render();
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()
