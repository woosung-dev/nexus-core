# 채점_전체.json + 응답_전체.json을 읽어 봇별 정답지 대비 채점 HTML(게이트 판정 + 문항 카드)을 봇별정답체점/에 생성
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GR = json.loads((ROOT / "봇별정답체점" / "_data" / "채점_전체.json").read_text(encoding="utf-8"))
RS = json.loads((ROOT / "봇별질문응답" / "_data" / "응답_전체.json").read_text(encoding="utf-8"))
OUTDIR = ROOT / "봇별정답체점"

ACCENT = "#9333EA"
ACC_COLOR = {"정확": "#2e7d32", "부분오류": "#ed6c02", "오류": "#c62828"}
SEV_COLOR = {"Critical": "#b91c1c", "Major": "#c2410c", "Minor": "#a16207", "없음": "#15803d"}


def esc(s):
    return html.escape(str(s or ""))


def nl(s):
    return esc(s).replace("\n", "<br>")


CSS = f"""
:root{{--ink:#1A2233;--sub:#5A6678;--line:#E5E9F0;--bg:#F6F8FB;--card:#fff;--accent:{ACCENT};}}
*{{box-sizing:border-box;}}
body{{margin:0;font-family:-apple-system,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;background:var(--bg);color:var(--ink);line-height:1.6;}}
.wrap{{max-width:1000px;margin:0 auto;padding:32px 20px 80px;}}
header.rpt{{border-left:5px solid var(--accent);padding:6px 0 6px 18px;}}
.eyebrow{{color:var(--accent);font-weight:700;font-size:13px;}}
h1{{margin:6px 0 8px;font-size:26px;}}
.meta{{color:var(--sub);font-size:13px;}}
.verdict{{margin:18px 0;padding:16px 20px;border-radius:12px;font-size:18px;font-weight:800;color:#fff;}}
.go{{background:#16A34A;}}.stop{{background:#DC2626;}}
.pillbar{{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 14px;}}
.pill{{background:#fff;border:1px solid var(--line);border-radius:999px;padding:5px 12px;font-size:12.5px;}}
.pill b{{color:var(--accent);}}
.gatetab{{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden;margin-bottom:10px;}}
.gatetab th,.gatetab td{{padding:9px 12px;font-size:13.5px;border-bottom:1px solid var(--line);text-align:left;}}
.gatetab th{{background:#FAFBFE;color:var(--sub);font-weight:700;}}
.pass{{color:#15803d;font-weight:700;}}.fail{{color:#dc2626;font-weight:700;}}
.tally{{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 26px;}}
.tchip{{border-radius:999px;padding:5px 14px;font-size:13px;font-weight:700;color:#fff;}}
.qcard{{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--line);border-radius:12px;padding:16px 18px;margin-bottom:14px;}}
.qcard.정확{{border-left-color:#2e7d32;}}.qcard.부분오류{{border-left-color:#ed6c02;}}.qcard.오류{{border-left-color:#c62828;}}
.qhead{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;}}
.qid{{background:var(--accent);color:#fff;border-radius:7px;padding:2px 9px;font-weight:700;font-size:13px;}}
.qarea{{color:var(--sub);font-size:12px;background:#F1F3F8;border-radius:6px;padding:2px 8px;}}
.badge{{border-radius:6px;padding:2px 9px;font-size:12px;font-weight:700;color:#fff;}}
.flag{{border-radius:6px;padding:2px 8px;font-size:11.5px;font-weight:700;background:#FEF2F2;color:#b91c1c;border:1px solid #FCA5A5;}}
.qtext{{font-weight:600;font-size:15.5px;margin-bottom:10px;}}
.lab{{font-size:11.5px;color:var(--sub);font-weight:700;margin:8px 0 3px;}}
.ans{{background:#FAFBFE;border:1px solid var(--line);border-radius:9px;padding:10px 12px;font-size:14px;}}
.golden{{background:#F5F3FF;border:1px solid #DDD6FE;border-radius:9px;padding:10px 12px;font-size:13px;color:#4c1d95;}}
.golden b{{color:#6d28d9;}}
.reason{{margin-top:8px;font-size:13px;color:#374151;background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;padding:8px 11px;}}
footer{{margin-top:30px;color:#9AA4B2;font-size:12px;text-align:center;}}
"""


def render_bot(bot):
    bid = str(bot["id"])
    s = GR["summary"][bid]
    gmap = {g["qid"]: g["grade"] for g in GR["graded"] if g["bot_id"] == bot["id"]}
    amap = {r["qid"]: r["answer"] for r in RS["responses"] if r["bot_id"] == bot["id"]}

    # 게이트 표
    grows = "".join(
        f"<tr><td>{esc(k)}</td><td>{esc(v['value'])}{esc(v['unit'])}</td>"
        f"<td>{esc(v['threshold'])}</td>"
        f"<td class='{'pass' if v['pass'] else 'fail'}'>{'통과' if v['pass'] else '미달'}</td></tr>"
        for k, v in s["gates"].items())
    verdict = ("✅ 전 지표 통과 (GO)" if s["go"] else "⛔ 미달 항목 있음 (STOP)")
    vcls = "go" if s["go"] else "stop"
    cc = s.get("crosscheck_gpt4omini_pct")
    cc_html = (f'<span class="pill">gpt-4o-mini 1차 교차검증 <b>{cc}%</b></span>'
               if cc is not None else "")

    tally = "".join(
        f'<span class="tchip" style="background:{ACC_COLOR[k]}">{k} {s.get(k_alt, 0)}</span>'
        for k, k_alt in [("정확", "정확"), ("부분오류", "부분오류"), ("오류", "오류")])
    flags_extra = []
    if s["hallu"]: flags_extra.append(f'<span class="tchip" style="background:#7c3aed">할루시 {s["hallu"]}</span>')
    if s["unsafe"]: flags_extra.append(f'<span class="tchip" style="background:#be123c">unsafe {s["unsafe"]}</span>')
    if s["markup"]: flags_extra.append(f'<span class="tchip" style="background:#0f766e">내부표기 {s["markup"]}</span>')
    if s["route_fail"]: flags_extra.append(f'<span class="tchip" style="background:#a16207">라우팅✗ {s["route_fail"]}</span>')

    cards = []
    for q in GR["questions"]:
        g = gmap.get(q["id"], {})
        acc = g.get("accuracy", "오류")
        sev = g.get("severity", "없음")
        flags = []
        if g.get("hallucination"): flags.append("할루시")
        if not g.get("safe", True): flags.append("unsafe")
        if g.get("markup_leak"): flags.append("내부표기")
        if not g.get("routing_ok", True): flags.append("라우팅✗")
        flag_html = " ".join(f'<span class="flag">{esc(f)}</span>' for f in flags)
        golden = "<br>".join(filter(None, [
            f"<b>필수 포함:</b> {esc(q.get('golden_must',''))}" if q.get('golden_must') else "",
            f"<b>금지·주의:</b> {esc(q.get('golden_avoid',''))}" if q.get('golden_avoid') else "",
            f"<b>라우팅:</b> {esc(q.get('golden_routing',''))}" if q.get('golden_routing') else "",
            f"<b>심각도 후보:</b> {esc(q.get('golden_severity',''))}" if q.get('golden_severity') else "",
        ]))
        cards.append(f"""
<div class="qcard {acc}">
  <div class="qhead"><span class="qid">{esc(q['id'])}</span><span class="qarea">{esc(q['category'])}</span>
    <span class="badge" style="background:{ACC_COLOR.get(acc,'#666')}">{esc(acc)}</span>
    <span class="badge" style="background:{SEV_COLOR.get(sev,'#666')}">심각도 {esc(sev)}</span>
    {flag_html}</div>
  <div class="qtext">{esc(q['q'])}</div>
  <div class="lab">봇 답변</div><div class="ans">{nl(amap.get(q['id'],''))}</div>
  <div class="lab">정답지(골든·초안)</div><div class="golden">{golden}</div>
  <div class="reason"><b>채점 사유:</b> {esc(g.get('reason',''))}</div>
</div>""")

    m = GR["meta"]
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(bot['name'])} — 정답지 채점</title><style>{CSS}</style></head><body><div class="wrap">
<header class="rpt"><div class="eyebrow">블레싱 3회차 · 봇별 정답지 채점 (gpt-4o-mini)</div>
<h1>{esc(bot['name'])} <span style="font-size:16px;color:var(--sub)">(id {bot['id']} · {esc(bot['성격'])} · {bot['rag_docs']}문서)</span></h1>
<div class="meta">난이도 '중' {len(GR['questions'])}문항 · {esc(m['model'])} 응답 / {esc(m.get('grader','채점기'))} 채점 · {esc(m['generated_at'])} · 정답지=초안</div></header>
<div class="verdict {vcls}">{verdict} — 정확율 {s['accuracy_pct']}%</div>
<div class="pillbar"><span class="pill">채점기 <b>{esc(m.get('grader','—'))}</b></span>
<span class="pill">reasoning <b>{esc(m.get('grader_reasoning','—'))}</b></span>{cc_html}</div>
<table class="gatetab"><thead><tr><th>지표</th><th>측정값</th><th>기준선</th><th>판정</th></tr></thead><tbody>{grows}</tbody></table>
<div class="tally">{tally}{''.join(flags_extra)}</div>
{''.join(cards)}
<footer>블레싱 네비게이션 3회차 테스트 · 봇별정답체점 · 정답지는 초안(가정부장 확정 미반영)</footer>
</div></body></html>"""


def main():
    for bot in GR["bots"]:
        out = OUTDIR / f"{bot['slug']}_채점.html"
        out.write_text(render_bot(bot), encoding="utf-8")
        print(f"  생성: {out.name}  (정확율 {GR['summary'][str(bot['id'])]['accuracy_pct']}%, "
              f"{'GO' if GR['summary'][str(bot['id'])]['go'] else 'STOP'})")
    print(f"\n봇별 채점 HTML {len(GR['bots'])}개 완료")


if __name__ == "__main__":
    main()
