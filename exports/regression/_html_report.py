# 회귀 실행 결과를 필터 가능한 단일 HTML + 마크다운으로 낸다.
#
#   python _html_report.py --tag e6 --compare v1 --title "E_부모동행v6" --outdir ~/Downloads/테스트\ 결과
#
# HTML 은 외부 의존 없이 자체완결(인라인 CSS/JS). 다크모드 대응.
# 비교 대상(--compare)이 있으면 같은 질문의 두 실행 답변을 나란히 보여준다.
import argparse
import html
import json
import re
from datetime import datetime
from pathlib import Path

DIR = Path(__file__).parent


def load(tag, kind):
    p = DIR / (f"_{kind}_{tag}.json" if tag else f"_{kind}.json")
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def collect(tag):
    """한 실행의 문항별 통합 레코드."""
    ans = load(tag, "answers")
    if not ans:
        raise SystemExit(f"_answers_{tag}.json 없음")
    l1, l2, l3 = load(tag, "l1"), load(tag, "l2"), load(tag, "l3")

    l2map = {str(r["key"]): r for r in (l2 or {}).get("rows", [])}
    l3map = {str(r["key"]): r for r in (l3 or {}).get("rows", [])}
    probe = (l1 or {}).get("neutral_probe") or {}

    rows = []
    for r in ans["results"]:
        key = str(r.get("cid") or r.get("gid"))
        sig = r.get("l1") or {}
        rows.append({
            "key": key, "bucket": r.get("bucket"), "cat": r.get("cat") or "(없음)",
            "risk": r.get("risk") or "—", "q": r.get("q", ""), "answer": r.get("answer", ""),
            "citations": r.get("citations") or [], "n_citations": r.get("n_citations", 0),
            "chunks": sig.get("grounding_chunks"), "gen_ms": sig.get("gen_ms"),
            "answer_len": sig.get("answer_len") or len(r.get("answer", "")),
            "followups": sig.get("followups"),
            "l2": (l2map.get(key) or {}).get("verdicts") or [],
            "l3": l3map.get(key),
            "probe": probe.get(key),
        })
    return {"meta": ans["bot"], "rows": rows,
            "l1": l1, "l2": l2, "l3": l3, "count": len(rows)}


def gate_rows(run):
    n = run["count"]
    rows = []
    errs = sum(1 for r in run["rows"] if r["answer"].startswith("[ERROR]"))
    rows.append(("무응답·오류율", "≤ 2%", f"{100.0*errs/n:.1f}% ({errs}/{n})", errs / n <= 0.02))
    l2 = run["l2"]
    if l2:
        leak = sum(1 for r in run["rows"] for v in r["l2"]
                   if v["rule"] in ("internal_leak", "prompt_echo"))
        rows.append(("내부표기 노출", "= 0", f"{leak}건", leak == 0))
        rows.append(("L2 확정 Critical", "= 0", f"{l2['critical_fails']}건", l2["critical_fails"] == 0))
    l3 = run["l3"]
    if l3 and l3.get("accuracy_pct") is not None:
        # _l3.py 는 scored_calls / pending_questions 로 쓴다. 옛 철자도 받아 준다(_report.py 와 동일).
        scored = l3.get("scored_calls", l3.get("scored", 0))
        pending = len(l3.get("pending_questions", l3.get("pending_reference", [])) or [])
        d = f" ({scored}호출/{pending}문항 대기)"
        rows.append(("정확도", "≥ 90%", f"{l3['accuracy_pct']:.1f}%{d}", l3["accuracy_pct"] >= 90))
        rows.append(("할루시네이션율", "≤ 3%", f"{l3['hallucination_pct']:.1f}%{d}",
                     l3["hallucination_pct"] <= 3))
    else:
        rows.append(("정확도", "≥ 90%", "정답지 대기", None))
        rows.append(("할루시네이션율", "≤ 3%", "정답지 대기", None))
    # L1
    measured = [r for r in run["rows"] if r["chunks"] is not None
                and not r["answer"].startswith("[ERROR]")]
    if measured:
        empty = sum(1 for r in measured if r["chunks"] == 0)
        cited = sum(1 for r in measured if r["n_citations"] > 0)
        rows.append(("검색 빈손율", "낮을수록", f"{100.0*empty/len(measured):.1f}% ({empty}/{len(measured)})", None))
        rows.append(("인용 보고율", "높을수록", f"{100.0*cited/len(measured):.1f}% ({cited}/{len(measured)})", None))
    return rows


# ────────────────────────────────────────────────────────────── HTML

CSS = """
:root{--bg:#fbfbfd;--fg:#1a1a1e;--mut:#6b6b78;--line:#e4e4ec;--card:#fff;
 --ok:#0f7b45;--okbg:#e7f6ee;--bad:#b42318;--badbg:#fdecea;--warn:#8a5a00;--warnbg:#fdf3e0;
 --a:#2b5fd9;--abg:#e8effc;--acc:#5b3fd9}
@media(prefers-color-scheme:dark){:root{--bg:#0f1013;--fg:#e8e8ee;--mut:#9a9aa8;--line:#26262f;
 --card:#17181d;--ok:#4ade80;--okbg:#10281c;--bad:#f87171;--badbg:#2a1414;--warn:#fbbf24;
 --warnbg:#2a2010;--a:#7ea2ff;--abg:#151d33;--acc:#a78bfa}}
:root[data-theme=dark]{--bg:#0f1013;--fg:#e8e8ee;--mut:#9a9aa8;--line:#26262f;--card:#17181d;
 --ok:#4ade80;--okbg:#10281c;--bad:#f87171;--badbg:#2a1414;--warn:#fbbf24;--warnbg:#2a2010;
 --a:#7ea2ff;--abg:#151d33;--acc:#a78bfa}
:root[data-theme=light]{--bg:#fbfbfd;--fg:#1a1a1e;--mut:#6b6b78;--line:#e4e4ec;--card:#fff;
 --ok:#0f7b45;--okbg:#e7f6ee;--bad:#b42318;--badbg:#fdecea;--warn:#8a5a00;--warnbg:#fdf3e0;
 --a:#2b5fd9;--abg:#e8effc;--acc:#5b3fd9}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.65 -apple-system,BlinkMacSystemFont,"Pretendard","Apple SD Gothic Neo",sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:32px 20px 80px}
h1{font-size:26px;margin:0 0 6px;letter-spacing:-.02em}
.sub{color:var(--mut);font-size:13.5px;margin-bottom:24px}
.metaline{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:26px}
.chip{background:var(--card);border:1px solid var(--line);border-radius:999px;
 padding:4px 12px;font-size:12.5px;color:var(--mut)}
.chip b{color:var(--fg);font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:12px;margin-bottom:14px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:13px 15px}
.kpi .lab{font-size:12px;color:var(--mut)}
.kpi .val{font-size:19px;font-weight:650;margin-top:3px;letter-spacing:-.01em}
.kpi .cri{font-size:11.5px;color:var(--mut);margin-top:2px}
.kpi.pass{border-color:color-mix(in srgb,var(--ok) 40%,var(--line))}
.kpi.fail{border-color:color-mix(in srgb,var(--bad) 55%,var(--line));background:var(--badbg)}
.kpi.pass .val{color:var(--ok)} .kpi.fail .val{color:var(--bad)}
.bar{position:sticky;top:0;z-index:9;background:color-mix(in srgb,var(--bg) 90%,transparent);
 backdrop-filter:blur(10px);border:1px solid var(--line);border-radius:12px;padding:12px;
 margin:22px 0 16px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
select,input[type=search]{background:var(--card);color:var(--fg);border:1px solid var(--line);
 border-radius:8px;padding:7px 10px;font-size:13px;font-family:inherit}
input[type=search]{flex:1;min-width:180px}
.count{font-size:12.5px;color:var(--mut);margin-left:auto;white-space:nowrap}
button.reset{background:none;border:1px solid var(--line);color:var(--mut);border-radius:8px;
 padding:7px 11px;font-size:12.5px;cursor:pointer;font-family:inherit}
button.reset:hover{color:var(--fg)}
.item{background:var(--card);border:1px solid var(--line);border-radius:12px;margin-bottom:11px;
 overflow:hidden}
.head{padding:13px 16px;cursor:pointer;display:flex;gap:9px;align-items:flex-start;flex-wrap:wrap}
.head:hover{background:color-mix(in srgb,var(--fg) 3%,transparent)}
.qt{flex:1;min-width:240px;font-weight:560;font-size:14.5px;letter-spacing:-.01em}
.key{font:12px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--mut);
 background:color-mix(in srgb,var(--fg) 6%,transparent);padding:2px 7px;border-radius:5px}
.b{font-size:11.5px;padding:2px 8px;border-radius:999px;border:1px solid transparent;white-space:nowrap}
.b.ok{background:var(--okbg);color:var(--ok)} .b.bad{background:var(--badbg);color:var(--bad)}
.b.warn{background:var(--warnbg);color:var(--warn)} .b.info{background:var(--abg);color:var(--a)}
.b.mut{background:color-mix(in srgb,var(--fg) 6%,transparent);color:var(--mut)}
.body{display:none;padding:0 16px 16px;border-top:1px solid var(--line)}
.item.open .body{display:block}
.sec{margin-top:14px}
.sec h4{margin:0 0 6px;font-size:12px;color:var(--mut);font-weight:600;
 text-transform:uppercase;letter-spacing:.05em}
.ans{white-space:pre-wrap;background:color-mix(in srgb,var(--fg) 3%,transparent);
 border-radius:9px;padding:13px 15px;font-size:14px;line-height:1.75}
.cmp{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:820px){.cmp{grid-template-columns:1fr}}
.cmp .ans{font-size:13.2px}
.cmp h5{margin:0 0 5px;font-size:12.5px;color:var(--mut);font-weight:600}
table.v{width:100%;border-collapse:collapse;font-size:13px}
table.v td{padding:5px 9px;border-bottom:1px solid var(--line);vertical-align:top}
table.v td:first-child{white-space:nowrap;color:var(--mut);width:1%}
.cits{display:flex;flex-wrap:wrap;gap:6px}
.cit{font-size:12px;background:var(--abg);color:var(--a);padding:3px 9px;border-radius:6px}
.empty{text-align:center;color:var(--mut);padding:50px 0;font-size:14px}
.gatetbl{width:100%;border-collapse:collapse;font-size:13.5px;margin-bottom:8px}
.gatetbl th,.gatetbl td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line)}
.gatetbl th{color:var(--mut);font-weight:600;font-size:12px}
.note{background:var(--warnbg);color:var(--warn);border-radius:9px;padding:11px 14px;
 font-size:13px;margin:14px 0}
.toggle{position:fixed;right:18px;bottom:18px;z-index:20;background:var(--card);
 border:1px solid var(--line);color:var(--fg);border-radius:999px;width:42px;height:42px;
 cursor:pointer;font-size:17px}
.analysis{background:var(--card);border:1px solid var(--line);border-radius:12px;
 padding:6px 20px 18px;margin:18px 0}
.analysis h3{font-size:16.5px;letter-spacing:-.01em}
.analysis h4{font-size:14px;color:var(--acc)}
.analysis code{font:12.5px ui-monospace,SFMono-Regular,Menlo,monospace;
 background:color-mix(in srgb,var(--fg) 7%,transparent);padding:1px 5px;border-radius:4px}
.analysis ul{margin:6px 0;padding-left:20px} .analysis li{margin:3px 0}
.analysis table.gatetbl{margin:8px 0 14px}
.setup{background:var(--card);border:1px solid var(--line);border-radius:12px;
 padding:6px 20px 18px;margin:18px 0}
.setup h3{font-size:16.5px;margin:18px 0 8px;letter-spacing:-.01em}
.setup h4{font-size:13.5px;color:var(--acc);margin:16px 0 5px}
.setup code{font:12.5px ui-monospace,SFMono-Regular,Menlo,monospace;
 background:color-mix(in srgb,var(--fg) 7%,transparent);padding:1px 5px;border-radius:4px}
.setup table.gatetbl td{font-size:12.8px}
.mutx{color:var(--mut);font-size:12px}
"""

JS = """
const items=[...document.querySelectorAll('.item')];
const f={bucket:'',cat:'',risk:'',search:'',l2:'',l3:'',ret:''};
function apply(){
  let n=0;
  for(const el of items){
    const d=el.dataset;
    let ok=true;
    if(f.bucket&&d.bucket!==f.bucket)ok=false;
    if(f.cat&&d.cat!==f.cat)ok=false;
    if(f.risk&&d.risk!==f.risk)ok=false;
    if(f.l2&&d.l2!==f.l2)ok=false;
    if(f.l3&&d.l3!==f.l3)ok=false;
    if(f.ret&&d.ret!==f.ret)ok=false;
    if(f.search){const q=f.search.toLowerCase();
      if(!(d.q.toLowerCase().includes(q)||d.a.toLowerCase().includes(q)))ok=false;}
    el.style.display=ok?'':'none';
    if(ok)n++;
  }
  document.getElementById('cnt').textContent=n+' / '+items.length+'건';
  document.getElementById('none').style.display=n?'none':'';
}
for(const id of ['bucket','cat','risk','l2','l3','ret']){
  document.getElementById('f-'+id).addEventListener('change',e=>{f[id]=e.target.value;apply();});
}
document.getElementById('f-search').addEventListener('input',e=>{f.search=e.target.value;apply();});
document.getElementById('reset').addEventListener('click',()=>{
  for(const k in f)f[k]='';
  for(const id of ['bucket','cat','risk','l2','l3','ret'])document.getElementById('f-'+id).value='';
  document.getElementById('f-search').value='';apply();});
for(const el of items){
  el.querySelector('.head').addEventListener('click',()=>el.classList.toggle('open'));
}
document.getElementById('expand').addEventListener('click',()=>{
  const anyClosed=items.some(e=>e.style.display!=='none'&&!e.classList.contains('open'));
  items.forEach(e=>{if(e.style.display!=='none')e.classList.toggle('open',anyClosed);});
});
const root=document.documentElement;
document.getElementById('theme').addEventListener('click',()=>{
  const cur=root.getAttribute('data-theme')||
    (matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');
  root.setAttribute('data-theme',cur==='dark'?'light':'dark');});
apply();
"""


def esc(s):
    return html.escape(str(s if s is not None else ""))


def prompt_label(meta):
    """prompt_source 가 없는 구버전 산출물은 '봇 저장 프롬프트'로 표기한다."""
    src = meta.get("prompt_source")
    if not src:
        return f"봇 {meta.get('id')} 저장본"
    return Path(src).name if src.startswith("/") else src


def load_ragdocs():
    p = DIR / "_ragdocs.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _fmt_size(n):
    if not n:
        return "—"
    return f"{n/1_048_576:.1f}MB" if n >= 1_048_576 else (
        f"{n/1024:.0f}KB" if n >= 1024 else f"{n}B")


def setup_rows(run, cmp_run):
    """실행 구성 표 — 어떤 봇·어떤 프롬프트·어떤 모델을 썼는지."""
    runs = [(run, "이번 실행")] + ([(cmp_run, "비교 대상")] if cmp_run else [])
    rows = []
    for r, lab in runs:
        m = r["meta"]
        rows.append({
            "label": lab,
            "name": r.get("label") or prompt_label(m),
            "bot": f"{m.get('id')} · {m.get('name')}",
            "bot_id": str(m.get("id")),
            "prompt": prompt_label(m),
            "prompt_src": m.get("prompt_source") or f"bots.id={m.get('id')} 의 system_prompt 컬럼",
            "prompt_len": m.get("prompt_len"),
            "model": m.get("model"),
            "n": r["count"],
        })
    return rows


def badges(r):
    out = []
    ch = r["chunks"]
    if ch is None:
        out.append(('mut', '계측없음'))
    elif ch == 0:
        out.append(('warn', '검색 0'))
    else:
        out.append(('ok', f'검색 {ch}'))
    if r["n_citations"]:
        out.append(('info', f'인용 {r["n_citations"]}'))
    l3 = r["l3"]
    if l3:
        v = l3.get("verdict")
        out.append((('ok' if v == '정확' else 'bad'), f'L3 {v}'))
        if l3.get("hallucination"):
            out.append(('bad', '할루시'))
        if l3.get("severity") and l3["severity"] != "없음":
            out.append(('bad', l3["severity"]))
    fails = [v for v in r["l2"] if v["verdict"] == "fail"]
    revs = [v for v in r["l2"] if v["verdict"] == "review"]
    for v in fails:
        out.append(('bad', f'L2 {v["rule"]}'))
    for v in revs:
        out.append(('warn', f'L2? {v["rule"]}'))
    return out


def md_to_html(md):
    """분석 노트용 최소 마크다운 변환 — 제목/표/목록/굵게/코드만 다룬다."""
    out, tbl = [], []

    def flush_tbl():
        if not tbl:
            return
        head, *rest = tbl
        body = [r for r in rest if not set(r.replace("|", "").strip()) <= set("-: ")]
        cells = lambda r, t: "".join(  # noqa: E731
            f"<{t}>{inline(c.strip())}</{t}>" for c in r.strip().strip("|").split("|"))
        out.append("<table class='gatetbl'><tr>" + cells(head, "th") + "</tr>"
                   + "".join("<tr>" + cells(r, "td") + "</tr>" for r in body) + "</table>")
        tbl.clear()

    def inline(t):
        t = esc(t)
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
        return t

    inlist = False
    for line in md.splitlines():
        s = line.rstrip()
        if s.startswith("|"):
            tbl.append(s)
            continue
        flush_tbl()
        if s.startswith("- "):
            if not inlist:
                out.append("<ul>")
                inlist = True
            out.append(f"<li>{inline(s[2:])}</li>")
            continue
        if inlist:
            out.append("</ul>")
            inlist = False
        if s.startswith("### "):
            out.append(f"<h4 style='margin:16px 0 6px'>{inline(s[4:])}</h4>")
        elif s.startswith("## "):
            out.append(f"<h3 style='margin:22px 0 8px'>{inline(s[3:])}</h3>")
        elif s.startswith("> "):
            out.append(f"<div class='note'>{inline(s[2:])}</div>")
        elif s.strip():
            out.append(f"<p style='margin:8px 0'>{inline(s)}</p>")
    if inlist:
        out.append("</ul>")
    flush_tbl()
    return "".join(out)


def render_html(run, cmp_run, title, subtitle, notes=""):
    rows = run["rows"]
    cmpmap = {r["key"]: r for r in (cmp_run["rows"] if cmp_run else [])}
    cats = sorted({r["cat"] for r in rows})
    risks = sorted({r["risk"] for r in rows})

    def opt(vals, lab):
        s = f'<option value="">{esc(lab)}</option>'
        return s + "".join(f'<option value="{esc(v)}">{esc(v)}</option>' for v in vals)

    # KPI
    kpis = []
    for name, crit, val, ok in gate_rows(run):
        cls = "" if ok is None else ("pass" if ok else "fail")
        kpis.append(f'<div class="kpi {cls}"><div class="lab">{esc(name)}</div>'
                    f'<div class="val">{esc(val)}</div><div class="cri">{esc(crit)}</div></div>')

    body = []
    for r in rows:
        l3 = r["l3"] or {}
        l2fail = "fail" if any(v["verdict"] == "fail" for v in r["l2"]) else (
            "review" if any(v["verdict"] == "review" for v in r["l2"]) else "clean")
        ret = "hit" if (r["chunks"] or 0) > 0 else "miss"
        bl = "".join(f'<span class="b {c}">{esc(t)}</span>' for c, t in badges(r))

        meta = [("구간", r["bucket"]), ("카테고리", r["cat"]), ("위험도", r["risk"]),
                ("검색 청크", r["chunks"]), ("인용", r["n_citations"]),
                ("응답 길이", r["answer_len"]), ("생성 시간", f'{r["gen_ms"]}ms' if r["gen_ms"] else "—")]
        if r["probe"]:
            meta.append(("빈손 원인(중립 프로브)", r["probe"].get("cause")))
        metatbl = "".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in meta)

        secs = []
        if cmpmap.get(r["key"]):
            c = cmpmap[r["key"]]
            secs.append(
                '<div class="sec"><h4>답변 비교</h4><div class="cmp">'
                f'<div><h5>{esc(title)}</h5><div class="ans">{esc(r["answer"])}</div></div>'
                f'<div><h5>{esc(cmp_run["label"])}</h5><div class="ans">{esc(c["answer"])}</div></div>'
                '</div></div>')
        else:
            secs.append(f'<div class="sec"><h4>답변</h4><div class="ans">{esc(r["answer"])}</div></div>')

        if r["citations"]:
            cits = "".join(f'<span class="cit">{esc(t)}</span>' for t in r["citations"])
            secs.append(f'<div class="sec"><h4>참고 자료</h4><div class="cits">{cits}</div></div>')

        if r["l2"]:
            vt = "".join(f'<tr><td>{esc(v["rule"])}</td>'
                         f'<td><span class="b {"bad" if v["verdict"]=="fail" else "warn"}">'
                         f'{esc(v["verdict"])}</span> {esc(v.get("severity") or "")} — {esc(v["detail"])}</td></tr>'
                         for v in r["l2"])
            secs.append(f'<div class="sec"><h4>L2 규칙 판정</h4><table class="v">{vt}</table></div>')

        if l3:
            l3t = "".join(f"<tr><td>{esc(k)}</td><td>{esc(l3.get(v))}</td></tr>" for k, v in
                          [("판정", "verdict"), ("할루시", "hallucination"),
                           ("심각도", "severity"), ("유형", "type"), ("근거", "reason")])
            secs.append(f'<div class="sec"><h4>L3 의미 판정</h4><table class="v">{l3t}</table></div>')

        secs.append(f'<div class="sec"><h4>계측</h4><table class="v">{metatbl}</table></div>')

        body.append(
            f'<div class="item" data-bucket="{esc(r["bucket"])}" data-cat="{esc(r["cat"])}" '
            f'data-risk="{esc(r["risk"])}" data-l2="{l2fail}" data-l3="{esc(l3.get("verdict") or "")}" '
            f'data-ret="{ret}" data-q="{esc(r["q"])}" data-a="{esc(r["answer"])}">'
            f'<div class="head"><span class="key">{esc(r["key"])}</span>'
            f'<span class="qt">{esc(r["q"])}</span>{bl}</div>'
            f'<div class="body">{"".join(secs)}</div></div>')

    m = run["meta"]
    chips = [("프롬프트", prompt_label(m)),
             ("모델", m.get("model")), ("RAG 봇", f'{m.get("id")} · {m.get("name")}'),
             ("문항", run["count"]),
             ("생성", datetime.now().strftime("%Y-%m-%d %H:%M"))]
    chiphtml = "".join(f'<span class="chip">{esc(k)} <b>{esc(v)}</b></span>' for k, v in chips)

    # ── 실행 구성 + RAG 문서 목록 ──────────────────────────────
    srows = setup_rows(run, cmp_run)
    setup = ['<div class="setup"><h3>실행 구성</h3><table class="gatetbl">',
             '<tr><th></th><th>RAG 봇</th><th>시스템 프롬프트</th><th>모델</th><th>문항</th></tr>']
    for s in srows:
        plen = f' <span class="mutx">({s["prompt_len"]:,}자)</span>' if s["prompt_len"] else ""
        setup.append(f'<tr><td><b>{esc(s["label"])}</b></td><td>{esc(s["bot"])}</td>'
                     f'<td><code>{esc(s["prompt"])}</code>{plen}<br>'
                     f'<span class="mutx">{esc(s["prompt_src"])}</span></td>'
                     f'<td><code>{esc(s["model"])}</code></td><td>{s["n"]}건</td></tr>')
    setup.append("</table>")

    rd = load_ragdocs()
    if rd:
        setup.append('<h3>RAG 자료 — 각 봇에 실제 적재된 문서</h3>')
        for s in srows:
            docs = (rd.get("by_bot") or {}).get(s["bot_id"])
            if docs is None:
                continue
            setup.append(f'<h4>봇 {esc(s["bot"])} — {len(docs)}개 <span class="mutx">'
                         f'({esc(s["label"])})</span></h4><table class="gatetbl">'
                         '<tr><th>#</th><th>문서</th><th>크기</th><th>적재일</th></tr>')
            for i, d in enumerate(docs, 1):
                setup.append(f'<tr><td>{i}</td><td>{esc(d["name"])}</td>'
                             f'<td>{esc(_fmt_size(d.get("size_bytes")))}</td>'
                             f'<td>{esc(d.get("created") or "—")}</td></tr>')
            setup.append("</table>")
        setup.append(f'<p class="mutx">스토어 <code>{esc(rd.get("store"))}</code> · '
                     f'문서 목록 조회 시각 {esc(rd.get("fetched_at"))} · '
                     f'스토어 전체 {rd.get("total_in_store")}건</p>')
    else:
        setup.append('<p class="mutx">RAG 문서 목록 없음 — <code>_rag_docs.py</code> 를 먼저 실행하세요.</p>')
    setup.append("</div>")

    note = ""
    if run["l3"] and run["l3"].get("pending_reference"):
        note = (f'<div class="note">정확도·할루시율은 기준(골든)이 있는 '
                f'{run["l3"]["scored"]}문항만 채점한 값입니다. '
                f'{run["l3"]["pending_reference"]}문항은 정답지 확정 대기로 미채점 — '
                f'<b>미채점은 통과가 아닙니다.</b></div>')

    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} — 회귀 테스트 결과</title><style>{CSS}</style></head><body>
<div class="wrap">
<h1>{esc(title)} — 회귀 테스트 결과</h1>
<div class="sub">{esc(subtitle)}</div>
<div class="metaline">{chiphtml}</div>
<div class="grid">{"".join(kpis)}</div>
{"".join(setup)}
{note}
{('<div class="analysis">' + md_to_html(notes) + '</div>') if notes else ''}
<div class="bar">
<select id="f-bucket">{opt(["A","B","C"],"구간 전체")}</select>
<select id="f-cat">{opt(cats,"카테고리 전체")}</select>
<select id="f-risk">{opt(risks,"위험도 전체")}</select>
<select id="f-ret">{opt([],"검색 전체")}<option value="hit">검색됨</option><option value="miss">검색 0</option></select>
<select id="f-l2">{opt([],"L2 전체")}<option value="fail">L2 실패</option><option value="review">L2 확인필요</option><option value="clean">L2 무결</option></select>
<select id="f-l3">{opt([],"L3 전체")}<option value="정확">L3 정확</option><option value="부분">L3 부분</option><option value="오류">L3 오류</option></select>
<input type="search" id="f-search" placeholder="질문·답변 본문 검색">
<button class="reset" id="expand">모두 펼치기</button>
<button class="reset" id="reset">초기화</button>
<span class="count" id="cnt"></span>
</div>
{"".join(body)}
<div class="empty" id="none" style="display:none">조건에 맞는 문항이 없습니다.</div>
</div>
<button class="toggle" id="theme" title="테마 전환">◐</button>
<script>{JS}</script></body></html>"""


# ────────────────────────────────────────────────────────────── Markdown

def render_md(run, cmp_run, title, subtitle, notes=""):
    m = run["meta"]
    L = [f"# {title} — 회귀 테스트 결과", "", subtitle, "",
         "| 항목 | 값 |", "|---|---|",
         f"| 프롬프트 | `{prompt_label(m)}`" +
         (f" ({m['prompt_len']}자) |" if m.get("prompt_len") else " |"),
         f"| 모델 | `{m.get('model')}` |",
         f"| RAG | 봇 {m.get('id')} `{m.get('name')}` 의 문서 집합 |",
         f"| 문항 | {run['count']}건 |",
         f"| 생성 | {datetime.now().strftime('%Y-%m-%d %H:%M')} |", "",
         "## 게이트 판정", "", "| 지표 | 기준 | 실측 | 판정 |", "|---|---|---|---|"]
    for name, crit, val, ok in gate_rows(run):
        L.append(f"| {name} | {crit} | {val} | {'—' if ok is None else ('통과' if ok else '**미달**')} |")
    L.append("")
    if run["l3"] and run["l3"].get("pending_reference"):
        L += [f"> 정확도·할루시율은 기준이 있는 {run['l3']['scored']}문항만 채점한 값이다. "
              f"{run['l3']['pending_reference']}문항은 정답지 대기로 미채점 — **미채점은 통과가 아니다.**", ""]

    if notes:
        L += [notes.strip(), ""]

    # 요약 통계
    rows = run["rows"]
    hit = sum(1 for r in rows if (r["chunks"] or 0) > 0)
    L += ["## 요약", "",
          f"- 검색된 문항 **{hit}/{len(rows)}** ({100.0*hit/len(rows):.0f}%)",
          f"- 인용이 붙은 문항 **{sum(1 for r in rows if r['n_citations'])}/{len(rows)}**",
          f"- 평균 응답 길이 {sum(r['answer_len'] for r in rows)//len(rows)}자",
          f"- 평균 생성 시간 {sum(r['gen_ms'] or 0 for r in rows)/len(rows):.0f}ms", ""]

    if cmp_run:
        c = cmp_run["rows"]
        chit = sum(1 for r in c if (r["chunks"] or 0) > 0)
        L += ["### 비교", "", f"| 지표 | {title} | {cmp_run['label']} |", "|---|---|---|",
              f"| 검색된 문항 | {hit}/{len(rows)} | {chit}/{len(c)} |",
              f"| 인용이 붙은 문항 | {sum(1 for r in rows if r['n_citations'])} | "
              f"{sum(1 for r in c if r['n_citations'])} |",
              f"| 평균 응답 길이 | {sum(r['answer_len'] for r in rows)//len(rows)}자 | "
              f"{sum(r['answer_len'] for r in c)//len(c)}자 |", ""]

    # L2 / L3
    if run["l2"]:
        agg = {}
        for r in rows:
            for v in r["l2"]:
                agg.setdefault(v["rule"], {"n": 0, "verdict": v["verdict"], "sev": v["severity"]})
                agg[v["rule"]]["n"] += 1
        if agg:
            L += ["## L2 규칙 판정", "", "| 규칙 | 결과 | 심각도 | 건수 |", "|---|---|---|---|"]
            for k, v in sorted(agg.items(), key=lambda x: -x[1]["n"]):
                L.append(f"| `{k}` | {v['verdict']} | {v['sev'] or '—'} | {v['n']} |")
            L.append("")

    if run["l3"]:
        L += ["## L3 의미 판정", "", "| 문항 | 판정 | 할루시 | 심각도 | 근거 |", "|---|---|---|---|---|"]
        for r in run["l3"]["rows"]:
            L.append(f"| `{r['key']}` | {r['verdict']} | {'예' if r['hallucination'] else '아니오'} "
                     f"| {r['severity']} | {str(r['reason']).replace('|','·')[:150]} |")
        L.append("")

    # 전문
    L += ["## 문항별 응답 전문", ""]
    cmpmap = {r["key"]: r for r in (cmp_run["rows"] if cmp_run else [])}
    for r in rows:
        tags = " · ".join(t for _, t in badges(r))
        L += [f"### `{r['key']}` [{r['bucket']}] {r['q']}", "",
              f"`{r['cat']}` · 위험도 {r['risk']} · {tags}", ""]
        if r["citations"]:
            L.append(f"참고 자료: {', '.join('`'+c+'`' for c in r['citations'])}")
            L.append("")
        L += ["```", r["answer"].strip(), "```", ""]
        if r["l3"]:
            L.append(f"**L3** {r['l3']['verdict']} / {r['l3']['severity']} — {r['l3']['reason']}")
            L.append("")
        if r["l2"]:
            for v in r["l2"]:
                L.append(f"- **L2 {v['verdict']}** `{v['rule']}` — {v['detail']}")
            L.append("")
        if cmpmap.get(r["key"]):
            L += [f"<details><summary>{cmp_run['label']} 답변 비교</summary>", "",
                  "```", cmpmap[r["key"]]["answer"].strip(), "```", "", "</details>", ""]
    return "\n".join(L)


def main(tag, cmp_tag, title, subtitle, outdir, notes_file):
    run = collect(tag)
    cmp_run = None
    if cmp_tag:
        cmp_run = collect(cmp_tag)
        m = cmp_run["meta"]
        cmp_run["label"] = f"{m.get('name')} (봇 {m.get('id')} · {m.get('model')})"

    notes = ""
    if notes_file:
        p = Path(notes_file).expanduser()
        if not p.exists():
            raise SystemExit(f"분석 노트 파일 없음: {p}")
        notes = p.read_text(encoding="utf-8")

    out = Path(outdir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    stem = f"{title.replace(' ', '_')}_{datetime.now().strftime('%Y-%m-%d')}"

    (out / f"{stem}.html").write_text(render_html(run, cmp_run, title, subtitle, notes),
                                      encoding="utf-8")
    (out / f"{stem}.md").write_text(render_md(run, cmp_run, title, subtitle, notes),
                                    encoding="utf-8")
    print(f"HTML → {out / (stem + '.html')}")
    print(f"MD   → {out / (stem + '.md')}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--compare", default="", help="비교 대상 tag (같은 질문의 답변을 나란히)")
    ap.add_argument("--title", default="회귀 테스트")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--outdir", default="~/Downloads/테스트 결과")
    ap.add_argument("--notes", default="", help="분석 노트 마크다운 파일 (HTML·MD 양쪽에 삽입)")
    a = ap.parse_args()
    main(a.tag, a.compare, a.title, a.subtitle, a.outdir, a.notes)
