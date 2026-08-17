# 응답_전체.json을 읽어 봇별 질문·응답 HTML 보고서(채점 없음)를 봇별질문응답/에 생성
import html
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "봇별질문응답"
DATA = json.loads((BASE / "_data" / "응답_전체.json").read_text(encoding="utf-8"))

ACCENT = "#9333EA"


def esc(s):
    return html.escape(str(s or ""))


def nl(s):
    return esc(s).replace("\n", "<br>")


def chips(items, cls):
    if not items:
        return '<span class="none">—</span>'
    return "".join(f'<span class="chip {cls}">{esc(x)}</span>' for x in items)


CSS = f"""
:root{{--ink:#1A2233;--sub:#5A6678;--line:#E5E9F0;--bg:#F6F8FB;--card:#fff;--accent:{ACCENT};}}
*{{box-sizing:border-box;}}
body{{margin:0;font-family:-apple-system,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;background:var(--bg);color:var(--ink);line-height:1.6;}}
.wrap{{max-width:980px;margin:0 auto;padding:32px 20px 80px;}}
header.rpt{{border-left:5px solid var(--accent);padding:6px 0 6px 18px;margin-bottom:8px;}}
.eyebrow{{color:var(--accent);font-weight:700;font-size:13px;letter-spacing:.04em;}}
h1{{margin:6px 0 10px;font-size:26px;}}
.meta{{color:var(--sub);font-size:13px;}}
.botbar{{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 24px;}}
.pill{{background:#fff;border:1px solid var(--line);border-radius:999px;padding:5px 12px;font-size:13px;}}
.pill b{{color:var(--accent);}}
.note{{background:#FBF5FF;border:1px solid #E9D5FF;border-radius:10px;padding:12px 16px;font-size:13px;color:#6B21A8;margin-bottom:22px;}}
.qcard{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin-bottom:16px;box-shadow:0 1px 3px rgba(20,30,60,.04);}}
.qhead{{display:flex;align-items:center;gap:10px;margin-bottom:8px;}}
.qid{{background:var(--accent);color:#fff;border-radius:7px;padding:2px 9px;font-weight:700;font-size:13px;}}
.qarea{{color:var(--sub);font-size:12px;background:#F1F3F8;border-radius:6px;padding:2px 8px;}}
.qtext{{font-weight:600;font-size:16px;margin-bottom:12px;}}
.alabel{{font-size:12px;color:var(--sub);font-weight:700;margin:10px 0 4px;}}
.atext{{background:#FAFBFE;border:1px solid var(--line);border-radius:10px;padding:12px 14px;font-size:14.5px;white-space:normal;}}
.atext.err{{background:#FEF2F2;border-color:#FCA5A5;color:#B91C1C;}}
.chips{{margin-top:8px;}}
.chip{{display:inline-block;border-radius:999px;padding:3px 10px;font-size:12px;margin:3px 4px 0 0;}}
.chip.cite{{background:#EEF2FF;color:#3730A3;border:1px solid #C7D2FE;}}
.chip.fup{{background:#F0FDF4;color:#166534;border:1px solid #BBF7D0;}}
.none{{color:#9AA4B2;font-size:12px;}}
footer{{margin-top:30px;color:#9AA4B2;font-size:12px;text-align:center;}}
"""


def render_bot(bot):
    rmap = {r["qid"]: r for r in DATA["responses"] if r["bot_id"] == bot["id"]}
    cards = []
    for q in DATA["questions"]:
        r = rmap.get(q["id"], {})
        ans = r.get("answer", "")
        is_err = ans.startswith("[ERROR]")
        cards.append(f"""
<div class="qcard">
  <div class="qhead"><span class="qid">{esc(q['id'])}</span><span class="qarea">{esc(q['category'])}</span></div>
  <div class="qtext">{esc(q['q'])}</div>
  <div class="alabel">봇 응답</div>
  <div class="atext{' err' if is_err else ''}">{nl(ans)}</div>
  <div class="chips"><span class="alabel" style="display:inline">인용</span> {chips(r.get('citations', []), 'cite')}</div>
  <div class="chips"><span class="alabel" style="display:inline">후속질문</span> {chips(r.get('followups', []), 'fup')}</div>
</div>""")
    m = DATA["meta"]
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(bot['name'])} — 질문·응답</title><style>{CSS}</style></head><body><div class="wrap">
<header class="rpt"><div class="eyebrow">블레싱 3회차 · 봇별 질문·응답</div>
<h1>{esc(bot['name'])} <span style="font-size:16px;color:var(--sub)">(id {bot['id']})</span></h1>
<div class="meta">난이도 '중' {len(DATA['questions'])}문항 · 생성 {esc(m['generated_at'])}</div></header>
<div class="botbar">
<span class="pill">성격 <b>{esc(bot['성격'])}</b></span>
<span class="pill">프롬프트 <b>{bot['prompt_len']:,}자</b></span>
<span class="pill">RAG <b>{bot['rag_docs']}문서</b></span>
<span class="pill">모델 <b>{esc(bot['llm_model'])}</b></span>
<span class="pill">temp <b>{m['temperature']}</b></span>
</div>
<div class="note">이 문서는 <b>채점 없이 응답만</b> 담습니다. 정답지 대비 채점은 「봇별정답체점」 폴더를 참고하세요. ({esc(m['note'])})</div>
{''.join(cards)}
<footer>블레싱 네비게이션 3회차 테스트 · 봇별질문응답</footer>
</div></body></html>"""


def main():
    for bot in DATA["bots"]:
        out = BASE / f"{bot['slug']}.html"
        out.write_text(render_bot(bot), encoding="utf-8")
        print(f"  생성: {out.name}")
    print(f"\n봇별 응답 HTML {len(DATA['bots'])}개 완료")


if __name__ == "__main__":
    main()
