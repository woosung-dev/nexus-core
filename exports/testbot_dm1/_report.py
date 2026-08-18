# _evals.json 을 자체완결 HTML 검토 리포트로 렌더 → ~/Downloads/테스트봇D1_검증_<날짜>.html
# 질문별: 3주차 사람 피드백·평점 + D-1 답변 + AI 3평가(재발·독립위험도·AI평점). 필터·요약 통계 포함.
import argparse
import json
from datetime import date
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
DIR = ROOT / "exports" / "testbot_dm1"


def main(tag):
    evals = DIR / (f"_evals_{tag}.json" if tag else "_evals.json")
    out = Path.home() / "Downloads" / (
        f"테스트봇D1_검증_{date.today():%Y%m%d}{'_'+tag if tag else ''}.html")
    data = json.load(open(evals))
    results = data["results"]
    n = len(results)

    def cnt(key):
        from collections import Counter
        return dict(Counter(r.get(key) for r in results))

    rated = [r["ai_rating"] for r in results if isinstance(r.get("ai_rating"), (int, float))]
    avg = round(sum(rated) / len(rated), 2) if rated else None
    recur = cnt("risk_recur")
    indep = cnt("independent_risk")
    residual = sum(1 for r in results if r.get("independent_risk") in ("상", "중"))
    nocite = sum(1 for r in results if r.get("n_citations") == 0)

    payload = json.dumps(results, ensure_ascii=False)
    bf = sum(1 for r in results if r.get("bf_n"))
    cited = sum(1 for r in results if (r.get("citations") or r.get("bf_n")))
    summary = {
        "n": n, "avg": avg, "recur": recur, "indep": indep,
        "residual": residual, "nocite": nocite, "bf": bf, "cited": cited,
        "sang": sum(1 for r in results if r["risk"] == "상"),
        "jung": sum(1 for r in results if r["risk"] == "중"),
    }
    model_label = tag.split("_")[0] if tag else "gemini-3.1-flash-lite"
    out.write_text(HTML.replace("__DATA__", payload)
                   .replace("__SUMMARY__", json.dumps(summary, ensure_ascii=False))
                   .replace("__MODEL__", model_label)
                   .replace("__DATE__", f"{date.today():%Y-%m-%d}"),
                   encoding="utf-8")
    print(f"리포트 저장 → {out}")
    print(f"  총 {n}건 · 재발 {recur} · 독립위험도 {indep} · 잔존위험(상/중) {residual} · AI평점 평균 {avg} · 인용복구 {bf}")


HTML = r"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>테스트 봇 D-1 검증 리포트</title>
<style>
:root{--bg:#f4f6fb;--card:#fff;--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--blue:#2563eb;
--red:#b5321e;--amber:#d97706;--green:#15803d;--gray:#94a3b8;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:'IBM Plex Sans KR',-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo',sans-serif;line-height:1.6}
.wrap{max-width:1120px;margin:0 auto;padding:24px 20px 80px}
h1{font-size:22px;margin:0 0 4px}
.sub{color:var(--mut);font-size:13px;margin-bottom:18px}
.mono{font-family:'JetBrains Mono','IBM Plex Mono',ui-monospace,monospace;font-variant-numeric:tabular-nums}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:18px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.stat .k{font-size:11px;color:var(--mut)}
.stat .v{font-size:20px;font-weight:700;margin-top:2px}
.stat .v small{font-size:12px;font-weight:500;color:var(--mut)}
.note{background:#fffbeb;border:1px solid #fde68a;color:#92400e;border-radius:10px;padding:9px 12px;font-size:12px;margin-bottom:16px}
.filters{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px;position:sticky;top:0;background:var(--bg);padding:8px 0;z-index:5}
.filters b{font-size:11px;color:var(--mut);align-self:center;margin-right:2px}
.chip{border:1px solid var(--line);background:var(--card);border-radius:999px;padding:4px 11px;font-size:12px;cursor:pointer;user-select:none}
.chip.on{background:var(--blue);color:#fff;border-color:var(--blue)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-bottom:12px}
.chead{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-bottom:8px}
.q{font-weight:700;font-size:15px;flex:1 1 100%;order:5;margin-top:4px}
.badge{font-size:11px;font-weight:700;border-radius:6px;padding:2px 8px}
.b-red{background:#fbe9e6;color:var(--red)} .b-amber{background:#fef3c7;color:var(--amber)}
.b-green{background:#dcfce7;color:var(--green)} .b-gray{background:#eef2f7;color:var(--mut)}
.b-blue{background:#dbeafe;color:var(--blue)}
.gid{font-size:11px;color:var(--mut)}
.rate{font-weight:700;font-size:14px}
.sect{margin-top:12px}
.sect .lab{font-size:11px;font-weight:700;color:var(--mut);text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px}
.ans{white-space:pre-wrap;font-size:13.5px;background:#f8fafc;border:1px solid var(--line);border-radius:10px;padding:11px 13px}
.eval{display:grid;grid-template-columns:1fr;gap:8px;margin-top:10px}
.ev{border:1px solid var(--line);border-radius:10px;padding:9px 12px;font-size:13px}
.ev .eh{display:flex;align-items:center;gap:6px;font-weight:700;font-size:12px;margin-bottom:3px}
.ev .det{color:#334155;font-size:12.5px}
details.fb summary{cursor:pointer;font-size:12px;color:var(--blue);font-weight:600}
.fb .item{border-left:3px solid var(--line);padding:4px 0 4px 10px;margin-top:6px;font-size:12.5px;color:#334155;white-space:pre-wrap}
.fb .item .who{font-weight:700;color:var(--ink)}
.cites{font-size:11.5px;color:var(--mut);margin-top:6px}
.hide{display:none}
@media(prefers-color-scheme:dark){:root{--bg:#0b1220;--card:#131c2e;--ink:#e6edf7;--mut:#94a3b8;--line:#243149}
.ans{background:#0e1626}.note{background:#2a2410;border-color:#4d3f14;color:#fcd34d}
.filters{background:var(--bg)}.b-gray{background:#1e293b;color:#94a3b8}}
</style></head><body><div class="wrap">
<h1>테스트 봇 D-1 검증 리포트</h1>
<div class="sub">3주차 위험도 상·중 질문을 <b>테스트 봇 D-1</b>(봇 D 페르소나 + 2026 신규 규정집 개정초안 단독 RAG · 모델 <b>__MODEL__</b>)에 재질의하고,
3주차 사람 피드백·평점 기준으로 codex가 ①위험 재발 ②독립 위험도 ③AI 평점을 채점 · 생성일 __DATE__</div>
<div id="stats" class="grid"></div>
<div class="note">⚠️ 답변 생성 경로는 인용 영수증(grounding)을 자주 비워 보냄(페르소나+flash-lite의 알려진 현상) → 검색·반영은 정상인데 "인용 0"으로 보임.
그래서 각 답변에 <b>interactions 재검색으로 "참고한 자료(근사)"를 백필</b>해 표기합니다(실제 페이지까지 복구됨). 근사=표시 답변이 아니라 별도 검색 기준이라 라벨 유지.
D-1은 문서가 2026 규정집 1건뿐이라, 그 안에 없는 주제(예복예물·환불·이수교육 등)는 근거가 빈손일 수 있습니다.</div>
<div class="filters" id="filters"></div>
<div id="cards"></div>
</div>
<script>
const DATA = __DATA__;
const SUM = __SUMMARY__;
const RC = {"재발":"b-red","부분재발":"b-amber","해소":"b-green","판정불가":"b-gray"};
const IR = {"상":"b-red","중":"b-amber","하":"b-green","없음":"b-gray","판정불가":"b-gray"};
function rateCls(v){return v==null?"b-gray":v>=4?"b-green":v>=3?"b-amber":"b-red"}
function esc(s){return (s??"").replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]))}

const stats=document.getElementById('stats');
stats.innerHTML=[
 ['대상 질문',`${SUM.n}<small> 상 ${SUM.sang}·중 ${SUM.jung}</small>`],
 ['해소 / 재발',`${SUM.recur['해소']||0} <small>해소</small> / ${(SUM.recur['재발']||0)+(SUM.recur['부분재발']||0)} <small>재발</small>`],
 ['잔존 위험(독립 상·중)',`${SUM.residual}`],
 ['AI 평점 평균',`${SUM.avg??'-'}<small>/5</small>`],
 ['인용 확보',`${SUM.cited}<small>/${SUM.n} (근사 ${SUM.bf})</small>`],
].map(([k,v])=>`<div class="stat"><div class="k">${k}</div><div class="v mono">${v}</div></div>`).join('');

const F={risk:null,recur:null,indep:null,cite:null};
const FILTERS=[
 ['위험도','risk',['상','중']],
 ['재발','recur',['재발','부분재발','해소','판정불가']],
 ['독립위험도','indep',['상','중','하','없음']],
 ['인용','cite',['있음','없음']],
];
const fbar=document.getElementById('filters');
fbar.innerHTML=FILTERS.map(([lab,key,vals])=>
 `<b>${lab}</b>`+vals.map(v=>`<span class="chip" data-k="${key}" data-v="${v}">${v}</span>`).join('')
).join('<span style="width:10px"></span>');
fbar.addEventListener('click',e=>{const c=e.target.closest('.chip');if(!c)return;
 const k=c.dataset.k,v=c.dataset.v;F[k]=F[k]===v?null:v;
 [...fbar.querySelectorAll(`.chip[data-k="${k}"]`)].forEach(x=>x.classList.toggle('on',x.dataset.v===F[k]));
 render();});

function match(r){
 if(F.risk&&r.risk!==F.risk)return false;
 if(F.recur&&r.risk_recur!==F.recur)return false;
 if(F.indep&&r.independent_risk!==F.indep)return false;
 if(F.cite){const has=(r.n_citations||0)>0;if((F.cite==='있음')!==has)return false;}
 return true;
}
function fbItems(r){return (r.week3_feedback||[]).map(f=>
 `<div class="item"><span class="who">${esc(f.evaluator||'익명')}</span>`+
 `${f.rating!=null?` · 평점 ${f.rating}/5`:''}${f.risk&&f.risk!=='없음'?` · 위험 ${f.risk}`:''}\n${esc(f.text)}</div>`).join('')}

function card(r){
 const direct=r.citations||[], bf=r.bf_citations||[];
 const cites= direct.length?`참고 문서: ${direct.map(esc).join(' · ')}`
   : bf.length?`참고한 자료(근사): ${bf.map(esc).join(' · ')}`
   :`인용 0 (grounding 보고 누락 — 검색·반영은 정상. 백필 빈손)`;
 return `<div class="card">
  <div class="chead">
   <span class="gid mono">#${r.gid}</span>
   <span class="badge ${r.risk==='상'?'b-red':'b-amber'}">위험 ${r.risk}</span>
   <span class="badge ${RC[r.risk_recur]||'b-gray'}">재발: ${esc(r.risk_recur)}</span>
   <span class="badge ${IR[r.independent_risk]||'b-gray'}">독립위험 ${esc(r.independent_risk)}</span>
   <span class="rate mono ${'x'}"><span class="badge ${rateCls(r.ai_rating)}">AI ${r.ai_rating??'-'}/5</span></span>
   ${r.human_ratings&&r.human_ratings.length?`<span class="gid mono">사람 ${r.human_ratings.join(',')}</span>`:''}
   <div class="q">${esc(r.q)}</div>
  </div>
  <div class="sect"><details class="fb"><summary>3주차 사람 피드백 ${r.week3_feedback?`(${r.week3_feedback.length})`:''}</summary>${fbItems(r)}</details></div>
  ${r.model_answer?`<div class="sect"><div class="lab">모범답변</div><div class="ans">${esc(r.model_answer)}</div></div>`:''}
  <div class="sect"><div class="lab">테스트 봇 D-1 답변</div><div class="ans">${esc(r.answer)}</div><div class="cites">${cites}</div></div>
  <div class="eval">
   <div class="ev"><div class="eh"><span class="badge ${RC[r.risk_recur]||'b-gray'}">① 재발 ${esc(r.risk_recur)}</span></div><div class="det">${esc(r.risk_recur_detail)}</div></div>
   <div class="ev"><div class="eh"><span class="badge ${IR[r.independent_risk]||'b-gray'}">② 독립 위험도 ${esc(r.independent_risk)}</span></div><div class="det">${esc(r.independent_risk_detail)}</div></div>
   <div class="ev"><div class="eh"><span class="badge ${rateCls(r.ai_rating)}">③ AI 평점 ${r.ai_rating??'-'}/5</span></div><div class="det">${esc(r.ai_rating_detail)}</div></div>
  </div>
 </div>`;
}
function render(){
 const box=document.getElementById('cards');
 const rows=DATA.filter(match);
 box.innerHTML=rows.length?rows.map(card).join(''):`<div class="card" style="text-align:center;color:var(--mut)">조건에 맞는 질문이 없습니다.</div>`;
}
render();
</script></body></html>"""

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="", help="_evals_<tag>.json → 테스트봇D1_검증_<날짜>_<tag>.html")
    main(ap.parse_args().tag)
