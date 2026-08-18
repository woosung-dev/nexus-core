# 3주차 검증 과정·결과 + 실제 질문/봇응답 전문을 단일 HTML 보고서로 정리(~/Downloads)
import json
from datetime import date
from pathlib import Path

EXPORTS = Path("/Users/woosung/project/agy-project/nexus-core/exports")
OUT = Path("/Users/woosung/Downloads") / f"블레싱_3주차_검증보고_{date.today()}.html"

base_g = json.loads((EXPORTS / "probe_graded.json").read_text(encoding="utf-8"))
boost_g = json.loads((EXPORTS / "probe_graded_boost.json").read_text(encoding="utf-8"))
base_a = json.loads((EXPORTS / "probe_answers.json").read_text(encoding="utf-8"))
boost_a = json.loads((EXPORTS / "probe_answers_boost.json").read_text(encoding="utf-8"))

# (candidate, qid) → 실제 응답/인용
ans_map = {}
for src in (base_a, boost_a):
    for r in src["results"]:
        ans_map[(r["candidate"], r["qid"])] = (r["answer"], r.get("citations", []))

rows = []
for src in (base_g, boost_g):
    for r in src["graded"]:
        g = r["grade"]
        ans, cites = ans_map.get((r["candidate"], r["qid"]), (r.get("answer", ""), r.get("citations", [])))
        # 인용 문서명 중복 제거(빈도 표기)
        from collections import Counter
        cc = Counter(cites)
        cite_str = ", ".join(f"{n}×{c}" if c > 1 else n for n, c in cc.items()) if cc else "(없음)"
        rows.append({
            "candidate": r["candidate"], "qid": r["qid"], "area": r["area"],
            "q": r["q"], "golden": r["golden"], "answer": ans, "cites": cite_str,
            "accuracy": g.get("accuracy", "?"), "hallu": bool(g.get("hallucination")),
            "unsafe": (not g.get("safe", True)), "markup": bool(g.get("markup_leak")),
            "reason": g.get("reason", ""),
        })

summary = dict(base_g["summary"]); summary.update(boost_g["summary"])
order = ["A_원리", "B_정밀정보", "D_통합v5", "B_정밀정보+보강"]
chart = [{"name": k, "acc": summary[k]["accuracy_pct"], "정확": summary[k]["정확"],
          "부분": summary[k]["부분오류"], "오류": summary[k]["오류"]} for k in order if k in summary]

DATA = {"rows": rows, "chart": chart}

html = r"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>블레싱 네비게이션 — 3주차 검증 보고</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root{--ink:#1A2233;--sub:#5A6678;--line:#E5E9F0;--bg:#F6F8FB;--card:#fff;--accent:#9333EA;--ok:#16A34A;--warn:#D97706;--bad:#DC2626;}
*{box-sizing:border-box;}body{margin:0;font-family:-apple-system,'Pretendard','Apple SD Gothic Neo',sans-serif;background:var(--bg);color:var(--ink);line-height:1.65;}
.wrap{max-width:1000px;margin:0 auto;padding:40px 24px 80px;}
header{border-bottom:3px solid var(--accent);padding-bottom:18px;margin-bottom:8px;}
.eyebrow{color:var(--accent);font-weight:700;font-size:13px;letter-spacing:.08em;}
h1{margin:6px 0 4px;font-size:27px;}h2{font-size:18px;margin:30px 0 12px;border-left:4px solid var(--accent);padding-left:10px;}
.meta{color:var(--sub);font-size:14px;}
.verdict{margin:22px 0;padding:18px 22px;border-radius:14px;font-size:19px;font-weight:800;color:#fff;background:var(--warn);}
.verdict small{display:block;font-weight:500;font-size:13px;margin-top:6px;opacity:.95;}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;}
.card .big{font-size:26px;font-weight:800;}.card .lab{font-size:12px;color:var(--sub);}
.panel{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px 24px;margin-bottom:18px;}
table{width:100%;border-collapse:collapse;font-size:13.5px;}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top;}
th{color:var(--sub);font-size:12px;}
.pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700;}
.p정확{background:#DCFCE7;color:#166534;}.p부분오류{background:#FEF3C7;color:#92400E;}.p오류{background:#FEE2E2;color:#991B1B;}
.flag{color:var(--bad);font-weight:700;font-size:11px;}
select{padding:7px 10px;border:1px solid var(--line);border-radius:9px;font-size:13px;}
.step{display:flex;gap:12px;align-items:flex-start;margin-bottom:10px;}
.step .n{flex:0 0 26px;height:26px;border-radius:50%;background:var(--accent);color:#fff;font-weight:800;display:flex;align-items:center;justify-content:center;font-size:13px;}
.step .t b{font-size:14px;}.step .t div{font-size:13px;color:var(--sub);}
.ok{color:var(--ok);font-weight:700;}.bad{color:var(--bad);font-weight:700;}
footer{color:var(--sub);font-size:12px;text-align:center;margin-top:26px;}
canvas{max-height:300px;}
/* Q&A 카드 */
.qa{border:1px solid var(--line);border-radius:12px;margin-bottom:12px;overflow:hidden;}
.qa>summary{list-style:none;cursor:pointer;padding:13px 16px;display:flex;gap:10px;align-items:center;background:#fafbfe;}
.qa>summary::-webkit-details-marker{display:none;}
.qa>summary .qid{font-weight:800;flex:0 0 auto;}
.qa>summary .area{color:var(--sub);font-size:12.5px;flex:1 1 auto;}
.qa>summary .arrow{color:var(--sub);font-size:12px;}
.qa[open]>summary{border-bottom:1px solid var(--line);}
.qabody{padding:14px 16px;}
.qabody .lbl{font-size:11px;font-weight:800;color:var(--accent);letter-spacing:.04em;margin:12px 0 4px;}
.qabody .lbl:first-child{margin-top:0;}
.qabody .q{font-size:14.5px;font-weight:700;}
.qabody .golden{font-size:13px;color:#5A6678;background:#F6F8FB;border-radius:8px;padding:8px 10px;}
.qabody .ans{font-size:13.5px;white-space:pre-wrap;background:#fff;border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:8px;padding:11px 13px;max-height:380px;overflow:auto;}
.qabody .cites{font-size:12px;color:var(--sub);}
.qabody .reason{font-size:13px;background:#FFFBEB;border-radius:8px;padding:8px 10px;}
.toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:14px;}
.legend{font-size:12px;color:var(--sub);}
</style></head><body><div class="wrap">
<header><div class="eyebrow">신한국협회 가정행복국 · ㈜포너즈 · 레드팀 3주차 최종</div>
<h1>블레싱 네비게이션 — 검증 보고서</h1>
<div class="meta">실서버(Neon) 반영 전 검증 과정·결과 + 실제 질문/봇응답 전문 · 생성일 __DATE__</div></header>

<div class="verdict">⏸️ go/no-go 잠정 보류 — 확정 불가 (데이터 부재)
<small>단일 봇 베이스 = B_정밀정보 + 보강레이어로 freeze 방향 확정(정확율 66.7% 잠정). 누락 공문 2종(가해/피해 구분 폐지·천일국매칭 폐지) 미반영이 정확도 상한을 구조적으로 제한 — 미달은 no-go가 아니라 데이터 부재. 두 공문 확보가 go 선행조건.</small></div>

<div class="grid">
<div class="card"><div class="big ok">36/36</div><div class="lab">백엔드 테스트 통과 (replace 5 + followups 8 + 기존 23)</div></div>
<div class="card"><div class="big">88=8×11</div><div class="lab">RAG 실측 — 봇 8개 × 고유 11문서, 봇 내 중복 0건</div></div>
<div class="card"><div class="big">53.3% → <span class="ok">66.7%</span></div><div class="lab">베이스(B_정밀정보) → +보강레이어 정확율</div></div>
<div class="card"><div class="big" style="color:var(--warn)">2종</div><div class="lab">미확보 공문(go 선행조건)</div></div>
</div>

<h2>1. 어떻게 검증했나 (방법)</h2>
<div class="panel">
<div class="step"><div class="n">1</div><div class="t"><b>코드·파일 사실 검증</b><div>6개 병렬 탐색 에이전트 + codex(외부 AI) 코드 대조 — 착수 프롬프트의 코드 주장을 file:line 증거로 전량 확인. codex가 P1 8건 교정 → 계획 반영.</div></div></div>
<div class="step"><div class="n">2</div><div class="t"><b>라이브 스토어 읽기전용 실측</b><div>"8배 중복" 전제가 사실은 8봇 × 11 고유(봇 내 중복 0)임을 측정으로 반증. id5(라이브)는 이미 정본 → 비가역 purge 불필요.</div></div></div>
<div class="step"><div class="n">3</div><div class="t"><b>코드 수정 TDD</b><div>replace_document·followups 파서 견고화를 테스트 먼저 작성 후 구현. 내부마커 노출 0건 보장.</div></div></div>
<div class="step"><div class="n">4</div><div class="t"><b>스코어카드 ↔ 폼 글자단위 대조 + 합성 회귀</b><div>정확도 분모·치명 안전·효용/이해 게이트 3대 불일치를 합의값(D1~D3)대로 수정·회귀 검증.</div></div></div>
<div class="step"><div class="n">5</div><div class="t"><b>15문항 정확성 프로브(운영동일 모델)</b><div>운영과 동일한 gemini-3.1-flash-lite로 호출, gpt-4o-mini로 채점. 베이스 3후보 + 보강 적용 비교. <b>아래 3·4절에 실제 질문/봇응답 전문 수록.</b></div></div></div>
</div>

<h2>2. 프로브 결과 (정확율 비교)</h2>
<div class="panel"><canvas id="chart"></canvas>
<p style="font-size:13px;color:var(--sub);margin-top:12px;">정밀형(B_정밀정보)이 정확율 최고 → 베이스 freeze. 통합형(D_통합v5)은 최저(33.3%)라 "정밀 발전형 스왑" 결정과 일치. 보강레이어 +13.4%p(하늘부모님·이수교육·12일 가정출발의식 교정).</p></div>

<h2>3. 실제 질문 &amp; 봇 응답 (휴먼체크용)</h2>
<div class="panel">
<div class="toolbar">
 <span>후보</span><select id="filter" onchange="render()"></select>
 <span>정확도</span><select id="accf" onchange="render()"><option>전체</option><option>정확</option><option>부분오류</option><option>오류</option></select>
 <button onclick="toggleAll(true)" style="margin-left:auto;padding:6px 10px;border:1px solid var(--line);border-radius:8px;background:#fff;cursor:pointer;">모두 펼치기</button>
 <button onclick="toggleAll(false)" style="padding:6px 10px;border:1px solid var(--line);border-radius:8px;background:#fff;cursor:pointer;">모두 접기</button>
</div>
<div class="legend">각 문항을 클릭하면 <b>골든 기준 · 봇 실제 응답 전문 · 인용 문서 · 채점 사유</b>가 펼쳐집니다.</div>
<div id="qalist" style="margin-top:12px;"></div>
</div>

<h2>4. 코드·산출물 검증 요약</h2>
<div class="panel"><table>
<thead><tr><th>항목</th><th>검증</th><th>결과</th></tr></thead><tbody>
<tr><td>replace_document upsert</td><td>pytest (중복 수렴·업로드 실패 시 보존)</td><td class="ok">5/5 통과</td></tr>
<tr><td>followups 파서 견고화</td><td>pytest (닫는태그누락·공백·코드펜스·숫자보존·잔여마커)</td><td class="ok">8/8 통과 · 노출 0</td></tr>
<tr><td>백엔드 전체</td><td>pytest</td><td class="ok">36/36 통과</td></tr>
<tr><td>스코어카드 D1·D2·D3</td><td>합성 데이터 회귀</td><td class="ok">전량 통과</td></tr>
<tr><td>RAG 스테이징</td><td>store bot_id 3 공문 4종 추가</td><td class="ok">11→15, 검색 확인</td></tr>
<tr><td>병합 system_prompt</td><td>localhost 개발 DB id5 검증 적용</td><td class="ok">1737→8473자(운영 미반영)</td></tr>
</tbody></table></div>

<h2>5. 실서버 반영 전 남은 선행조건</h2>
<div class="panel"><ol style="font-size:14px;margin:0;padding-left:20px;">
<li><b>누락 공문 2종 확보</b>(가해/피해 폐지·천일국매칭 폐지) — 정확도 상한 제한 해소. <span class="bad">go 1순위 선행조건.</span></li>
<li><b>운영(Neon) 반영</b> — 현 환경은 개발 DB(localhost, 카카오 매핑 없음). 승인·접근 후 store bot_id 5 공문 추가 + system_prompt 교체.</li>
<li>규정집 4대성물·미검증영역 검색 보강 → 104문항 폼 기반 정식 스코어카드.</li>
</ol></div>

<footer>본 보고서는 3주차 검증 과정·측정 결과·실제 Q&amp;A를 실서버 반영 전 검토용으로 정리한 것입니다. 정확율은 누락 공문 2종 미반영 상태의 잠정치입니다.</footer>
</div>
<script>
const DATA = __DATA__;
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
new Chart(document.getElementById('chart'), {type:'bar',
 data:{labels:DATA.chart.map(d=>d.name), datasets:[{label:'정확율(%)', data:DATA.chart.map(d=>d.acc), backgroundColor:['#A78BDA','#9333EA','#C9B6E8','#16A34A']}]},
 options:{responsive:true, plugins:{legend:{display:false}, tooltip:{callbacks:{afterLabel:(ctx)=>{const d=DATA.chart[ctx.dataIndex];return `정확 ${d['정확']} / 부분 ${d['부분']} / 오류 ${d['오류']}`;}}}},
  scales:{y:{beginAtZero:true,max:100,title:{display:true,text:'정확율 %'},grid:{color:'#eee'}}}}});

const filter=document.getElementById('filter'), accf=document.getElementById('accf');
const cands=[...new Set(DATA.rows.map(r=>r.candidate))];
filter.innerHTML=cands.map(c=>`<option${c==='B_정밀정보+보강'?' selected':''}>${c}</option>`).join('');
function render(){
 const f=filter.value, a=accf.value;
 const rows=DATA.rows.filter(r=>r.candidate===f && (a==='전체'||r.accuracy===a));
 document.getElementById('qalist').innerHTML=rows.map(r=>{
  const flags=[r.hallu?'할루시':'',r.unsafe?'unsafe':'',r.markup?'마크업노출':''].filter(Boolean).join(' · ');
  return `<details class="qa"><summary>
    <span class="qid">Q${r.qid}</span>
    <span class="pill p${r.accuracy}">${r.accuracy}</span>
    <span class="area">${esc(r.area)}${flags?' · <span class=flag>'+flags+'</span>':''}</span>
    <span class="arrow">▼ 펼치기</span></summary>
   <div class="qabody">
    <div class="lbl">질문 (레드팀이 봇에게 던진 것)</div><div class="q">${esc(r.q)}</div>
    <div class="lbl">골든 기준 (정답 채점 기준)</div><div class="golden">${esc(r.golden)}</div>
    <div class="lbl">봇 실제 응답</div><div class="ans">${esc(r.answer)}</div>
    <div class="lbl">인용 문서</div><div class="cites">${esc(r.cites)}</div>
    <div class="lbl">채점 (gpt-4o-mini)</div><div class="reason"><b>${r.accuracy}</b>${flags?' ('+flags+')':''} — ${esc(r.reason)}</div>
   </div></details>`;
 }).join('') || '<div style="color:#5A6678;padding:20px;">해당 조건의 문항 없음</div>';
}
function toggleAll(open){document.querySelectorAll('#qalist details').forEach(d=>d.open=open);}
render();
</script>
</body></html>"""

html = html.replace("__DATE__", str(date.today())).replace("__DATA__", json.dumps(DATA, ensure_ascii=False))
OUT.write_text(html, encoding="utf-8")
print("검증 보고서(질문/응답 전문 포함) 저장:", OUT)
print("Q&A 행:", len(rows))
