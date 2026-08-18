# 정답지 + 프롬프트 4종의 요청·응답 전문을 한 화면에서 볼 수 있는 HTML 을 만든다.
#
# 왜 필요한가: 수치 리포트(FINDINGS.md)는 "몇 %" 까지만 말한다. 관리자·검토자가 실제로
# 확인해야 하는 것은 **이 질문에 이 봇이 뭐라고 답했는가** 이고, 그건 원문을 봐야 안다.
# 880호출이 전부 디스크에 있으니 새로 부를 것은 없다.
#
# 입력 (전부 기존 산출물)
#   exports/regression/questions.json        문항 + golden + safe_ok + anchors
#   exports/regression/_answers_<팔>_45.json  답변 원문 220건 × 4팔
#   exports/regression/_l3_<팔>_45.json       회차별 의미 판정
#   exports/regression/_l2_<팔>_45.json       규칙 판정
#   exports/golden45_2026-08-11/_golden_vs_docs.json  정답지↔규정집 v20 대조
#   exports/prompt4_2026-08-05/prompts/*      시스템 프롬프트 전문(= 요청의 절반)
#
# 출력: ~/d-file/nexus/<날짜 폴더>/qa-browser.html (자체 완결 · 외부 리소스 0)
import json
import shutil
import sys
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
REG = ROOT / "exports" / "regression"
HERE = Path(__file__).parent
PROMPTS = ROOT / "exports" / "prompt4_2026-08-05" / "prompts"
XLSX = Path.home() / "Downloads" / "축복 챗봇 정답지 요청 0806 (1).xlsx"
OUTDIR = Path.home() / "d-file" / "nexus" / "2026-08-12_축복챗봇_정답지_재측정"

# (태그, 표시 이름, 프롬프트 파일, 검색 모드)
# file_search 팔은 4회, lexical 팔은 1회다 — 회차 수가 다르므로 화면에 그대로 적는다.
PROMPTS_BY_ARM = {
    "sva": ("서비스방향 A", "4_sva_서비스방향A.md"),
    "svb": ("서비스방향 B", "3_svb_서비스방향B.md"),
    "j03": ("03_여정동반자", "1_j03_여정동반자.txt"),
    "e6": ("E_부모동행v6", "2_e6_부모동행v6.md"),
}
ARMS = [(f"{a}_45", f"{PROMPTS_BY_ARM[a][0]}", PROMPTS_BY_ARM[a][1], "file_search")
        for a in ("sva", "svb", "j03", "e6")] + \
       [(f"{a}_lex", f"{PROMPTS_BY_ARM[a][0]}", PROMPTS_BY_ARM[a][1], "lexical")
        for a in ("sva", "svb", "j03", "e6")]


def build():
    qs = json.loads((REG / "questions.json").read_text(encoding="utf-8"))["items"]
    vs = {r["key"]: r for r in
          json.loads((HERE / "_golden_vs_docs.json").read_text(encoding="utf-8"))["rows"]}

    # 문항 뼈대 — key 는 답변 파일이 쓰는 것과 같은 식별자여야 한다(cid 우선, 없으면 gid).
    items = []
    for it in qs:
        key = str(it.get("cid") or it.get("gid"))
        no = it.get("no")
        d = vs.get(str(no)) if no else None
        items.append({
            "key": key, "no": no, "bucket": it["bucket"], "q": it["q"],
            "risk": it.get("risk"), "cat": it.get("cat"),
            "golden": it.get("golden"), "golden_source": it.get("golden_source"),
            "safe_ok": it.get("safe_ok"),
            "anchors": it.get("anchors") or [],
            "evidence_status": it.get("evidence_status"),
            "rubric": it.get("rubric"), "gate": it.get("gate"),
            "must_not": it.get("must_not") or [],
            "vs_verdict": d and d.get("verdict"),
            "vs_reason": d and d.get("reason"),
            "vs_conflict": d and d.get("conflict"),
            "vs_cited": (d or {}).get("cited") or [],
            "calls": {},
        })
    by_key = {i["key"]: i for i in items}

    meta = {}
    for tag, name, pf, mode in ARMS:
        ans = json.loads((REG / f"_answers_{tag}.json").read_text(encoding="utf-8"))
        l3 = json.loads((REG / f"_l3_{tag}.json").read_text(encoding="utf-8"))
        l2 = json.loads((REG / f"_l2_{tag}.json").read_text(encoding="utf-8"))
        judge = {r["key"]: r for r in l3["rows"]}          # "<qkey>#r<rep>"
        rules = {r["key"]: r.get("verdicts") or [] for r in l2["rows"]}
        meta[tag] = {
            "name": name, "prompt_file": pf, "mode": mode,
            "prompt": (PROMPTS / pf).read_text(encoding="utf-8"),
            "prompt_len": ans["bot"]["prompt_len"], "reps": ans["reps"],
            "acc": round(l3["accuracy_pct"], 1),
            "acc_safe": round(l3["accuracy_incl_safe_pct"], 1),
            "hal": round(l3["hallucination_pct"], 1),
            "crit": l3["critical"], "verdicts": l3["verdicts"],
        }
        for r in ans["results"]:
            key = str(r.get("cid") or r.get("gid"))
            it = by_key.get(key)
            if it is None:
                continue
            rep = r.get("rep", 1)
            g = judge.get(f"{key}#r{rep}", {})
            it["calls"].setdefault(tag, []).append({
                "rep": rep, "answer": r["answer"],
                "citations": r.get("citations") or [],
                "ms": (r.get("l1") or {}).get("gen_ms"),
                "chunks": (r.get("l1") or {}).get("grounding_chunks"),
                "verdict": g.get("verdict"), "hallucination": g.get("hallucination"),
                "severity": g.get("severity"), "type": g.get("type"),
                "reason": g.get("reason"),
                "rules": rules.get(f"{key}#r{rep}", []),
            })
    for it in items:
        for tag in it["calls"]:
            it["calls"][tag].sort(key=lambda c: c["rep"])

    payload = {"items": items, "arms": [{"tag": t, **meta[t]} for t, _, _, _ in ARMS]}
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "qa-browser.html").write_text(
        HTML.replace("/*__DATA__*/", json.dumps(payload, ensure_ascii=False)),
        encoding="utf-8")

    if XLSX.exists():
        shutil.copy2(XLSX, OUTDIR / "정답지_관리자회신_0806.xlsx")
    else:
        print(f"⚠ xlsx 원본 없음: {XLSX}", file=sys.stderr)

    n_calls = sum(len(c) for i in items for c in i["calls"].values())
    size = (OUTDIR / "qa-browser.html").stat().st_size
    print(f"문항 {len(items)} · 호출 {n_calls} · {size/1024:.0f}KB → {OUTDIR/'qa-browser.html'}")


HTML = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>정답지 · 요청/응답 전문 — 축복 챗봇 2026-08-12</title>
<style>
:root{--bg:#fbfaf8;--panel:#fff;--ink:#1c1a17;--dim:#6b6560;--line:#e3ddd5;
 --accent:#8a5a2b;--soft:#f3ebe1;--good:#2f6b46;--good-bg:#eaf3ed;--warn:#8a6d1f;
 --warn-bg:#f7f0dc;--bad:#9b3232;--bad-bg:#f8ebea;--info:#2d5f8a;--info-bg:#e9f0f7;
 --mono:ui-monospace,SFMono-Regular,Menlo,monospace;
 --sans:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",Pretendard,"Noto Sans KR",sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
 --bg:#15140f;--panel:#1e1c17;--ink:#eae5dc;--dim:#9d968c;--line:#332f27;
 --accent:#d9a066;--soft:#2a2318;--good:#7fc39a;--good-bg:#1a2a20;--warn:#d8bd6a;
 --warn-bg:#2a2415;--bad:#e08b85;--bad-bg:#2c1c1b;--info:#8ab6dd;--info-bg:#182430}}
:root[data-theme=dark]{--bg:#15140f;--panel:#1e1c17;--ink:#eae5dc;--dim:#9d968c;--line:#332f27;
 --accent:#d9a066;--soft:#2a2318;--good:#7fc39a;--good-bg:#1a2a20;--warn:#d8bd6a;
 --warn-bg:#2a2415;--bad:#e08b85;--bad-bg:#2c1c1b;--info:#8ab6dd;--info-bg:#182430}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.7}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px 80px}
header{padding:36px 0 18px;border-bottom:1px solid var(--line)}
h1{font-size:26px;margin:6px 0 6px;letter-spacing:-.02em}
.sub{color:var(--dim);font-size:14px;margin:0}
.kicker{font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);font-weight:700}
.bar{position:sticky;top:0;z-index:20;background:var(--bg);border-bottom:1px solid var(--line);
 padding:12px 0;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
input[type=search],select{font:inherit;font-size:13.5px;padding:7px 11px;border:1px solid var(--line);
 border-radius:8px;background:var(--panel);color:var(--ink)}
input[type=search]{flex:1 1 160px;min-width:120px}
.bar>select,.bar>button{flex:0 0 auto}
button{font:inherit;font-size:13px;padding:7px 12px;border:1px solid var(--line);border-radius:8px;
 background:var(--panel);color:var(--ink);cursor:pointer}
button:hover{background:var(--soft)}
button.on{background:var(--accent);color:var(--bg);border-color:var(--accent)}
.count{font-size:13px;color:var(--dim);margin-left:auto;white-space:nowrap;flex:0 0 auto}
.q{border:1px solid var(--line);border-radius:11px;background:var(--panel);margin:12px 0;overflow:hidden}
.qh{padding:13px 16px;cursor:pointer;display:flex;gap:11px;align-items:flex-start}
.qh:hover{background:var(--soft)}
.qn{font-family:var(--mono);font-size:12.5px;color:var(--accent);font-weight:700;
 min-width:42px;padding-top:2px}
.qt{flex:1;font-weight:600;line-height:1.55}
.qm{display:flex;gap:5px;flex-wrap:wrap;justify-content:flex-end;max-width:340px}
.qb{padding:0 16px 18px;border-top:1px solid var(--line);display:none}
.q.open .qb{display:block}
.q.open .qh{background:var(--soft)}
.tag{display:inline-block;font-size:11px;font-weight:700;padding:2px 8px;border-radius:99px;white-space:nowrap}
.t-good{background:var(--good-bg);color:var(--good)}
.t-warn{background:var(--warn-bg);color:var(--warn)}
.t-bad{background:var(--bad-bg);color:var(--bad)}
.t-info{background:var(--info-bg);color:var(--info)}
.t-dim{background:var(--soft);color:var(--dim)}
h4{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--dim);
 margin:20px 0 7px;font-weight:700}
.box{border-radius:9px;padding:12px 15px;font-size:14.2px;white-space:pre-wrap;line-height:1.72}
.gold{background:var(--warn-bg);border-left:3px solid var(--warn)}
.docs{background:var(--info-bg);border-left:3px solid var(--info);font-size:13.6px}
.ans{background:var(--bg);border:1px solid var(--line)}
.arm{margin:16px 0;border:1px solid var(--line);border-radius:10px;overflow:hidden}
.armh{padding:9px 14px;background:var(--soft);font-weight:700;font-size:13.5px;
 display:flex;gap:9px;align-items:center;flex-wrap:wrap}
.armb{padding:12px 14px}
.rep{margin:11px 0;padding-top:11px;border-top:1px dashed var(--line)}
.rep:first-child{border-top:0;padding-top:0;margin-top:0}
.rl{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:6px;font-size:12px;color:var(--dim)}
.why{font-size:13px;color:var(--dim);margin-top:7px;padding-left:11px;border-left:2px solid var(--line)}
.cite{font-size:11.5px;color:var(--dim);margin-top:6px}
code{font-family:var(--mono);font-size:.87em;background:var(--soft);padding:1px 5px;border-radius:4px}
details.pr{border:1px solid var(--line);border-radius:10px;margin:10px 0;background:var(--panel)}
details.pr>summary{padding:11px 15px;cursor:pointer;font-weight:700;font-size:14px}
details.pr pre{margin:0;padding:0 15px 15px;white-space:pre-wrap;font-family:var(--mono);
 font-size:12.5px;line-height:1.65;color:var(--ink)}
.hint{font-size:13px;color:var(--dim);margin:14px 0}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12.5px;color:var(--dim);margin:10px 0 0}
@media (max-width:700px){.qm{max-width:none;justify-content:flex-start}.qh{flex-wrap:wrap}}
</style></head><body><div class="wrap">
<header>
 <div class="kicker">Nexus · 축복 챗봇 QA</div>
 <h1>정답지 · 요청/응답 전문</h1>
 <p class="sub">관리자 정답 45문항 + 불변제약 10 · 봇 11 테스트 봇 D-1 ver2 · gemini-3.5-flash-lite<br>
 <b>RAG 검색(file_search)</b> 4종 × 4회 = 880호출　+　<b>위키 검색(lexical)</b> 4종 × 2회 = 440호출
 　→　<b>총 1,320호출 전문</b></p>
</header>

<div class="bar">
 <input type="search" id="s" placeholder="질문·정답·답변 본문 검색">
 <select id="risk"><option value="">위험도 전체</option><option>상</option><option>중</option><option>하</option><option>없음</option></select>
 <select id="vs"><option value="">규정집 대조 전체</option><option>일치</option><option>부분일치</option><option>불일치</option><option>문서에없음</option></select>
 <select id="vd"><option value="">판정 전체</option><option value="오류">오류 포함</option><option value="부분">부분 포함</option><option value="안전응대">안전응대 포함</option><option value="정확">정확 포함</option><option value="hal">할루시 포함</option><option value="crit">Critical 포함</option><option value="leak">내부 마커 노출</option></select>
 <select id="md"><option value="">검색 모드 전체</option><option value="file_search">RAG(file_search)만</option><option value="lexical">위키(lexical)만</option></select>
 <button id="ex">전부 펼치기</button>
 <span class="count" id="cnt"></span>
</div>

<div class="legend">
 <span><span class="tag t-good">정확</span> 정답 충족</span>
 <span><span class="tag t-info">안전응대</span> 틀린 말 없이 담당자 연결</span>
 <span><span class="tag t-warn">부분</span> 핵심 일부 누락</span>
 <span><span class="tag t-bad">오류</span> 정답과 모순·지어냄</span>
</div>

<div id="list"></div>

<h4 style="margin-top:36px">요청의 절반 — 시스템 프롬프트 4종 전문</h4>
<p class="hint">각 호출의 요청은 <b>[시스템 프롬프트] + [문항 질문]</b> 이다.
프롬프트는 실행 시 파일에서 교체했고 <code>bots.system_prompt</code> 는 건드리지 않았다.<br>
호출 파라미터: <code>bot_id=11</code> · <code>model=gemini-3.5-flash-lite</code> ·
<code>max_tokens=2048</code> · 호출 간 <code>throttle=8s</code> · 문항당 4회 ·
검색은 Gemini File Search <code>metadata_filter: bot_id = 11</code>(규정집 v20 PDF · 대사전 v4 PDF).</p>
<div id="prompts"></div>

<script id="data" type="application/json">/*__DATA__*/</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const ARM = Object.fromEntries(D.arms.map(a=>[a.tag,a]));
const esc = s => String(s??'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const VC = {'정확':'t-good','안전응대':'t-info','부분':'t-warn','오류':'t-bad'};
const RC = {'상':'t-bad','중':'t-warn','하':'t-dim','없음':'t-dim'};
const SC = {'일치':'t-good','부분일치':'t-warn','불일치':'t-bad','문서에없음':'t-info'};

const LEAKRE = /\[\[\s*src\s*:|\[(?:reg|glo|gong)-\d+\]/;

function armBlock(it, tag){
  const a = ARM[tag], calls = it.calls[tag]||[];
  if(!calls.length) return '';
  const acc = calls.filter(c=>c.verdict==='정확').length;
  const rows = calls.map(c=>`
    <div class="rep">
      <div class="rl">
        <b>${c.rep}회차</b>
        <span class="tag ${VC[c.verdict]||'t-dim'}">${esc(c.verdict||'미채점')}</span>
        ${c.hallucination?'<span class="tag t-bad">할루시</span>':''}
        ${c.severity&&c.severity!=='없음'?`<span class="tag ${c.severity==='Critical'?'t-bad':'t-warn'}">${esc(c.severity)}</span>`:''}
        ${c.type&&c.type!=='없음'?`<span class="tag t-dim">${esc(c.type)}</span>`:''}
        ${LEAKRE.test(c.answer)?'<span class="tag t-bad">내부 마커 노출</span>':''}
        ${(c.rules||[]).map(r=>`<span class="tag t-dim">${esc(r.rule||r)}</span>`).join('')}
        <span style="margin-left:auto">${c.ms?Math.round(c.ms/100)/10+'s':''} · 검색 ${c.chunks??'-'}청크</span>
      </div>
      <div class="box ans">${esc(c.answer)}</div>
      ${c.citations.length?`<div class="cite">인용: ${c.citations.map(esc).join(' · ')}</div>`:'<div class="cite">인용 없음</div>'}
      ${c.reason?`<div class="why">심사: ${esc(c.reason)}</div>`:''}
    </div>`).join('');
  return `<div class="arm">
    <div class="armh"><span>${esc(a.name)}</span>
      <span class="tag ${a.mode==='lexical'?'t-info':'t-dim'}">${a.mode==='lexical'?'위키 검색':'RAG 검색'}</span>
      <span class="tag ${acc===calls.length?'t-good':acc?'t-warn':'t-bad'}">정확 ${acc}/${calls.length}</span>
      <span style="font-weight:400;color:var(--dim);font-size:12px">${a.prompt_len}자 · ${esc(a.prompt_file)}</span>
    </div><div class="armb">${rows||'<i>응답 없음</i>'}</div></div>`;
}

function card(it){
  const fsC = D.arms.filter(a=>a.mode==='file_search').flatMap(a=>it.calls[a.tag]||[]);
  const lxC = D.arms.filter(a=>a.mode==='lexical').flatMap(a=>it.calls[a.tag]||[]);
  const all = fsC.concat(lxC);
  const n = (cs)=>cs.filter(c=>c.verdict==='정확').length;
  const meta = [
    it.risk?`<span class="tag ${RC[it.risk]||'t-dim'}">위험 ${esc(it.risk)}</span>`:'',
    it.bucket==='C'?'<span class="tag t-dim">불변제약</span>':'',
    it.vs_verdict?`<span class="tag ${SC[it.vs_verdict]||'t-dim'}">규정집 ${esc(it.vs_verdict)}</span>`:'',
    `<span class="tag t-dim">RAG ${n(fsC)}/${fsC.length}</span>`,
    `<span class="tag t-info">위키 ${n(lxC)}/${lxC.length}</span>`,
    lxC.some(c=>LEAKRE.test(c.answer))?'<span class="tag t-bad">마커 노출</span>':'',
  ].join('');
  const gold = it.golden ? `
    <h4>① 관리자 정답 ${it.bucket==='C'?'(우리가 만든 불변제약 기준)':''}</h4>
    <div class="box gold">${esc(it.golden)}</div>
    <div class="cite">
      ${it.golden_source?`근거란: ${esc(it.golden_source)} · `:''}
      ${it.safe_ok===true?'「확인되지 않습니다 + 담당자 연결」만 해도 정답 인정':''}
      ${it.evidence_status?` · 관리자 근거상태: ${esc(it.evidence_status)}`:''}
      ${it.must_not.length?` · 금지: ${it.must_not.map(esc).join(', ')}`:''}
    </div>` : '';
  const docs = it.vs_verdict ? `
    <h4>② 규정집 v20 대조</h4>
    <div class="box docs"><b>${esc(it.vs_verdict)}</b>${it.vs_cited.length?` · ${it.vs_cited.map(esc).join(', ')}`:''}
${esc(it.vs_reason||'')}${it.vs_conflict?`\n\n문서 원문: ${esc(it.vs_conflict)}`:''}</div>` : '';
  const anc = it.anchors.length ? `<div class="cite">관리자 키워드: ${it.anchors.map(esc).join(' · ')}</div>` : '';
  return `<div class="q" data-k="${esc(it.key)}">
    <div class="qh"><span class="qn">${it.no?'#'+it.no:esc(it.key)}</span>
      <span class="qt">${esc(it.q)}</span><span class="qm">${meta}</span></div>
    <div class="qb">${gold}${anc}${docs}
      <h4>③ RAG 검색(file_search) — 프롬프트 4종 × 4회</h4>
      ${D.arms.filter(a=>a.mode==='file_search').map(a=>armBlock(it,a.tag)).join('')}
      <h4>④ 위키 검색(lexical) — 프롬프트 4종 × 2회 · 라이브 봇의 실제 경로</h4>
      ${D.arms.filter(a=>a.mode==='lexical').map(a=>armBlock(it,a.tag)).join('') || '<p class="hint">이 문항의 위키 검색 응답 없음</p>'}
    </div></div>`;
}

const list = document.getElementById('list');
function render(){
  const s=document.getElementById('s').value.trim().toLowerCase();
  const r=document.getElementById('risk').value, v=document.getElementById('vs').value,
        d=document.getElementById('vd').value, m=document.getElementById('md').value;
  const hit = D.items.filter(it=>{
    if(r && it.risk!==r) return false;
    if(v && it.vs_verdict!==v) return false;
    const arms = m ? D.arms.filter(a=>a.mode===m) : D.arms;
    const all = arms.flatMap(a=>it.calls[a.tag]||[]);
    if(d==='hal'){ if(!all.some(c=>c.hallucination)) return false; }
    else if(d==='crit'){ if(!all.some(c=>c.severity==='Critical')) return false; }
    else if(d==='leak'){ if(!all.some(c=>LEAKRE.test(c.answer))) return false; }
    else if(d){ if(!all.some(c=>c.verdict===d)) return false; }
    if(s){
      const hay=(it.q+' '+(it.golden||'')+' '+all.map(c=>c.answer).join(' ')).toLowerCase();
      if(!hay.includes(s)) return false;
    }
    return true;
  });
  list.innerHTML = hit.map(card).join('') || '<p class="hint">해당 문항 없음</p>';
  document.getElementById('cnt').textContent = `${hit.length} / ${D.items.length}문항`;
}
list.addEventListener('click', e=>{
  const h=e.target.closest('.qh'); if(h) h.parentElement.classList.toggle('open');
});
['s','risk','vs','vd','md'].forEach(id=>document.getElementById(id)
  .addEventListener('input', render));
document.getElementById('ex').addEventListener('click', e=>{
  const on = e.target.classList.toggle('on');
  document.querySelectorAll('.q').forEach(q=>q.classList.toggle('open', on));
  e.target.textContent = on ? '전부 접기' : '전부 펼치기';
});
// 프롬프트 본문은 모드가 달라도 같은 파일이다 — 한 번만 싣고, 두 모드 수치를 함께 붙인다.
const byFile = {};
D.arms.forEach(a=>{ (byFile[a.prompt_file] ||= []).push(a); });
document.getElementById('prompts').innerHTML = Object.values(byFile).map(g=>{
  const a = g[0];
  const nums = g.map(x=>`${x.mode==='lexical'?'위키':'RAG'} 정확 ${x.acc}% · 할루시 ${x.hal}% · Critical ${x.crit} (${x.reps}회)`).join('　|　');
  return `<details class="pr"><summary>${esc(a.name)} — ${a.prompt_len}자 · <code>${esc(a.prompt_file)}</code>
   <div style="font-weight:400;color:var(--dim);font-size:12.5px;margin-top:3px">${esc(nums)}</div></summary>
   <pre>${esc(a.prompt)}</pre></details>`;
}).join('');
render();
</script>
</div></body></html>
"""

if __name__ == "__main__":
    build()
