# 부분측정 보고서 — 조화연 5문항 블레싱 나 vs A/B/C, 페르소나 에이전트 + codex 이중 평가
import html
import json
from datetime import date
from pathlib import Path

DIR = Path("/Users/woosung/project/agy-project/nexus-core/exports/blessing_vs_abc_2026-06-12")
OUT = Path("/Users/woosung/Downloads") / f"블레싱_나_vs_ABC_부분측정_조화연5문항_{date.today()}.html"
WIN_TO_LETTER = {"통합": "A", "원리": "B", "정밀": "C"}


def esc(s):
    return html.escape(str(s if s is not None else ""))


def load(path):
    try:
        return json.load(open(path))
    except Exception:
        return None


ds = json.load(open(DIR / "dataset_조화연_partial.json"))
items = ds["items"]

agent_raw = load(DIR / "agent_eval.json") or []
agent_eval, agent_summary = {}, {}
for e in agent_raw:
    if e and e.get("eval"):
        agent_eval = {r["qid"]: r for r in e["eval"].get("results", [])}
        agent_summary = e["eval"].get("summary", {})

ce_obj = load(DIR / "codex_eval_조화연.json")
codex_eval = {r["qid"]: r for r in ce_obj.get("results", [])} if ce_obj else {}
codex_summary = ce_obj.get("summary", {}) if ce_obj else {}


def vs_pill(v):
    m = {"win": ("블레싱 우세", "pwin"), "tie": ("비슷", "ptie"), "lose": ("기존 우세", "plose")}
    t, c = m.get(v, ("-", "ptie"))
    return f'<span class="pill {c}">{t}</span>'


def best_pill(b):
    cls = "pbless" if b == "블레싱" else ("pbad" if b == "모두부적절" else "pabc")
    return f'<span class="pill {cls}">{esc(b)}</span>'


def scores_html(sc):
    if not sc:
        return '<span class="muted">-</span>'
    out = []
    for k, lab in [("A", "A"), ("B", "B"), ("C", "C"), ("blessing", "블레싱")]:
        v = sc.get(k, "-")
        hi = "shi" if isinstance(v, int) and v >= 4 else ("slo" if isinstance(v, int) and v <= 2 else "")
        out.append(f'<span class="sc {hi}"><b>{lab}</b> {v}</span>')
    return " ".join(out)


def eval_block(ev, label):
    if not ev:
        return f'<div class="evb"><div class="evh">{label}</div><div class="muted">평가 대기/없음</div></div>'
    issues = ev.get("blessing_issues") or []
    iss = "".join(f"<li>{esc(i)}</li>" for i in issues) or '<li class="muted">없음</li>'
    return f"""<div class="evb">
      <div class="evh">{label} · best {best_pill(ev.get('best'))} · {vs_pill(ev.get('blessing_vs_tester'))}</div>
      <div class="scl">{scores_html(ev.get('scores'))}</div>
      <div class="cmt">{esc(ev.get('comment'))}</div>
      <div class="isl"><b>블레싱 지적</b><ul>{iss}</ul></div>
    </div>"""


rows = []
for it in items:
    qid = it["qid"]
    ae = agent_eval.get(qid)
    ce = codex_eval.get(qid)
    tester_letter = WIN_TO_LETTER.get(it.get("tester_win"), it.get("tester_choice"))
    cites = it.get("blessing_citations") or []
    cite_str = ", ".join(dict.fromkeys(cites)) if cites else "없음"
    ab = best_pill(ae["best"]) if ae else "<span class='muted'>-</span>"
    cb = best_pill(ce["best"]) if ce else "<span class='muted'>-</span>"
    rows.append(f"""<details class="q" open>
      <summary>
        <span class="qid">{esc(qid)}</span>
        <span class="qt">{esc(it.get('qtype'))}</span>
        <span class="qq">{esc(it['q'][:80])}</span>
        <span class="qmeta">테스터→<b>{esc(tester_letter)}</b> · 에이전트 {ab} · codex {cb}</span>
      </summary>
      <div class="qbody">
        <div class="qfull"><b>질문</b> {esc(it['q'])}</div>
        <div class="ans"><div class="al">A · 통합</div><div class="at">{esc(it.get('ansA_통합'))}</div></div>
        <div class="ans"><div class="al">B · 원리</div><div class="at">{esc(it.get('ansB_원리'))}</div></div>
        <div class="ans"><div class="al">C · 정밀</div><div class="at">{esc(it.get('ansC_정밀'))}</div></div>
        <div class="ans bless"><div class="al">★ 블레싱 나 (신규봇) <span class="cite">인용: {esc(cite_str)}</span></div><div class="at">{esc(it.get('blessing_answer'))}</div></div>
        <div class="tf"><b>테스터(조화연) 원선택</b> {esc(tester_letter)} · <b>당시 피드백</b> {esc(it.get('tester_feedback'))}</div>
        <div class="evgrid">{eval_block(ae, '페르소나 에이전트(조화연)')}{eval_block(ce, 'codex(독립 LLM)')}</div>
      </div>
    </details>""")


def g(d, k):
    return d.get(k, "-") if d else "-"


HTML = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>블레싱 나 vs A/B/C — 부분측정(조화연 5문항) {date.today()}</title>
<style>
:root{{--ink:#1A2233;--sub:#5A6678;--line:#E5E9F0;--bg:#F6F8FB;--card:#fff;--accent:#9333EA;--ok:#16A34A;--warn:#D97706;--bad:#DC2626;}}
*{{box-sizing:border-box;}}body{{margin:0;font-family:-apple-system,'Pretendard','Apple SD Gothic Neo',sans-serif;background:var(--bg);color:var(--ink);line-height:1.6;}}
.wrap{{max-width:1080px;margin:0 auto;padding:36px 22px 90px;}}
header{{border-bottom:3px solid var(--accent);padding-bottom:16px;}}
.eyebrow{{color:var(--accent);font-weight:700;font-size:13px;letter-spacing:.06em;}}
h1{{margin:6px 0 4px;font-size:25px;}}h2{{font-size:18px;margin:30px 0 12px;border-left:4px solid var(--accent);padding-left:10px;}}
.meta{{color:var(--sub);font-size:13.5px;}}
.banner{{background:#FFFBEB;border:1px solid #FDE68A;border-radius:12px;padding:14px 18px;margin:18px 0;font-size:13.5px;color:#92400E;}}
.banner b{{color:#7C2D12;}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0;}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:13px;padding:14px 16px;}}
.card .big{{font-size:23px;font-weight:800;}}.card .lab{{font-size:12px;color:var(--sub);}}.card .sub2{{font-size:11.5px;color:var(--sub);margin-top:3px;}}
.summ{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:10px 0;}}
.scard{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;}}
.scard .h{{font-weight:800;margin-bottom:8px;}}
.scard .vr{{font-size:13px;color:#2A3344;margin-top:6px;}}
.scard ul{{margin:6px 0 0;padding-left:18px;font-size:12.5px;color:#991B1B;}}
details.q{{background:var(--card);border:1px solid var(--line);border-radius:12px;margin-bottom:10px;overflow:hidden;}}
details.q summary{{cursor:pointer;padding:11px 14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:13.5px;list-style:none;}}
details.q summary::-webkit-details-marker{{display:none;}}
.qid{{font-weight:800;color:var(--accent);font-size:12px;}}
.qt{{font-size:11px;color:var(--sub);background:#F1F3F8;padding:1px 7px;border-radius:999px;}}
.qq{{flex:1 1 280px;}}.qmeta{{font-size:11.5px;color:var(--sub);}}
.qbody{{padding:6px 16px 16px;border-top:1px solid var(--line);}}
.qfull{{font-size:13.5px;margin:10px 0;}}
.ans{{margin:8px 0;border:1px solid var(--line);border-radius:9px;overflow:hidden;}}
.ans .al{{background:#F1F3F8;padding:5px 10px;font-size:12px;font-weight:700;}}
.ans.bless .al{{background:#F3E8FF;color:#6B21A8;}}
.ans .at{{padding:9px 12px;font-size:13px;white-space:pre-wrap;color:#2A3344;}}
.cite{{font-weight:500;color:var(--sub);font-size:11px;margin-left:6px;}}
.tf{{font-size:12.5px;background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;padding:8px 11px;margin:10px 0;}}
.evgrid{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px;}}
.evb{{border:1px solid var(--line);border-radius:9px;padding:10px 12px;background:#FCFDFF;}}
.evh{{font-size:12.5px;font-weight:700;margin-bottom:6px;}}
.scl{{margin:4px 0;}}.sc{{display:inline-block;font-size:11.5px;padding:1px 7px;border-radius:6px;background:#F1F3F8;margin-right:4px;}}
.sc.shi{{background:#DCFCE7;color:#166534;}}.sc.slo{{background:#FEE2E2;color:#991B1B;}}
.cmt{{font-size:12.5px;color:#2A3344;margin:5px 0;}}
.isl{{font-size:12px;margin-top:4px;}}.isl ul{{margin:3px 0 0;padding-left:18px;}}.isl li{{color:#991B1B;}}
.pill{{display:inline-block;padding:1px 8px;border-radius:999px;font-size:11px;font-weight:700;}}
.pwin{{background:#DCFCE7;color:#166534;}}.ptie{{background:#F1F3F8;color:#475569;}}.plose{{background:#FEE2E2;color:#991B1B;}}
.pbless{{background:#F3E8FF;color:#6B21A8;}}.pabc{{background:#E0E7FF;color:#3730A3;}}.pbad{{background:#FEE2E2;color:#991B1B;}}
.muted{{color:#9AA5B5;}}
.note{{font-size:12.5px;color:var(--sub);background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-top:16px;}}
@media(max-width:680px){{.evgrid,.summ{{grid-template-columns:1fr;}}}}
</style></head><body><div class="wrap">
<header>
  <div class="eyebrow">REDTEAM · 신규봇 비교 검증 (부분측정)</div>
  <h1>블레싱 나 vs A(통합)·B(원리)·C(정밀)</h1>
  <div class="meta">조화연 2주차 레드팀 질문 · 신규 봇 "블레싱 나"(bot id=3, gemini-3.1-flash-lite) 재질의 · 페르소나 에이전트 + codex 이중 평가 · {date.today()}</div>
</header>
<div class="banner">⚠️ <b>부분측정</b> — 신규 봇 운영 모델(gemini-3.1-flash-lite)의 무료 일일 요청 한도(500/일)가 소진되어,
당초 계획한 90문항(조화연·신은비·김소영 각 30) 중 <b>조화연 5문항</b>만 신규 봇 응답을 확보했습니다.
나머지는 할당량 리셋(PT 자정 ≈ 16:00 KST) 이후 동일 절차로 재현 가능합니다. 아래는 확보된 5문항 기준 결과입니다.</div>
<div class="cards">
  <div class="card"><div class="big">5 / 90</div><div class="lab">측정 완료 문항</div><div class="sub2">조화연만</div></div>
  <div class="card"><div class="big">{g(agent_summary,'blessing_best_count')} / {g(codex_summary,'blessing_best_count')}</div><div class="lab">블레싱 최우수</div><div class="sub2">에이전트 / codex (5문항 중)</div></div>
  <div class="card"><div class="big">{g(agent_summary,'blessing_win_count')} / {g(codex_summary,'blessing_win_count')}</div><div class="lab">기존선택 대비 우세</div><div class="sub2">에이전트 / codex</div></div>
  <div class="card"><div class="big">{g(agent_summary,'blessing_lose_count')} / {g(codex_summary,'blessing_lose_count')}</div><div class="lab">기존선택이 우세</div><div class="sub2">에이전트 / codex</div></div>
</div>
<h2>평가자별 총평</h2>
<div class="summ">
  <div class="scard"><div class="h">페르소나 에이전트 (조화연 / redteam-johwayeon)</div>
    <div class="vr"><b>결론</b> {esc(g(agent_summary,'verdict'))}</div>
    <div><b style="font-size:12.5px">반복 지적</b><ul>{"".join(f"<li>{esc(x)}</li>" for x in (agent_summary.get('recurring_issues') or [])) or '<li class="muted">-</li>'}</ul></div>
  </div>
  <div class="scard"><div class="h">codex (독립 LLM)</div>
    <div class="vr"><b>결론</b> {esc(g(codex_summary,'verdict'))}</div>
    <div><b style="font-size:12.5px">반복 지적</b><ul>{"".join(f"<li>{esc(x)}</li>" for x in (codex_summary.get('recurring_issues') or [])) or '<li class="muted">-</li>'}</ul></div>
  </div>
</div>
<h2>문항별 상세 (조화연 5문항)</h2>
{"".join(rows)}
<div class="note"><b>방법</b> · A/B/C = 2주차 레드팀에서 테스터(조화연)가 본 3개 봇(통합/원리/정밀) 답변(고정). 블레싱 나 = 신규 봇(bot id=3)을 동일 질문에 운영동일 파라미터(generate_with_rag, max_tokens=2048)로 재질의한 새 답변. 평가는 (1) 조화연 페르소나 레드팀 에이전트(Claude)와 (2) codex(독립 LLM)가 동일 루브릭·도메인 정답기준(domain_facts.md)으로 독립 수행. blessing_vs_tester = 조화연이 당시 고른 답변 대비 블레싱의 우열.</div>
</div></body></html>"""

OUT.write_text(HTML, encoding="utf-8")
print(f"보고서 저장: {OUT}")
print(f"에이전트 요약: best={g(agent_summary,'blessing_best_count')} win={g(agent_summary,'blessing_win_count')} lose={g(agent_summary,'blessing_lose_count')}")
print(f"codex 요약: best={g(codex_summary,'blessing_best_count')} win={g(codex_summary,'blessing_win_count')} lose={g(codex_summary,'blessing_lose_count')}")
