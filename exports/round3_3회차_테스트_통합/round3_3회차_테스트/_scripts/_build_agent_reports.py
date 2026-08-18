# 에이전트별체점/_data/<agent>.json(6인 페르소나 평가)을 읽어 에이전트당 HTML(5봇 상대비교)을 생성
import html
import json
import re
from pathlib import Path


def load_tolerant(fp):
    """트레일링 콤마·코드펜스가 섞여도 파싱되도록 관대하게 로드."""
    t = fp.read_text(encoding="utf-8").strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    i, j = t.find("{"), t.rfind("}")
    if i != -1 and j != -1:
        t = t[i:j + 1]
    t = re.sub(r",(\s*[}\]])", r"\1", t)  # 트레일링 콤마 제거
    return json.loads(t)

ROOT = Path(__file__).resolve().parent.parent
DATADIR = ROOT / "에이전트별체점" / "_data"
OUTDIR = ROOT / "에이전트별체점"
RS = json.loads((ROOT / "봇별질문응답" / "_data" / "응답_전체.json").read_text(encoding="utf-8"))
BOTMETA = {b["id"]: b for b in RS["bots"]}
BOT_ORDER = [b["id"] for b in RS["bots"]]

ACCENT = "#0EA5A4"  # 에이전트(정성리뷰) = 청록 계열로 채점(보라)과 구분
SEV_COLOR = {"Critical": "#b91c1c", "Major": "#c2410c", "Minor": "#a16207"}

# 파일순서·표기 (없으면 _data 안의 json 자동 수집)
AGENTS = [
    ("redteam-ohchansu", "오찬수", "2세 당사자 — 봇 간 상대비교·정체성 검증"),
    ("redteam-johwayeon", "조화연", "행정·규정 전문가 — 사실/용어/분류 정확성"),
    ("redteam-shineunbi", "신은비", "상담심리 전문가 — 심리적 안전성 7축"),
    ("redteam-kimkwanwoo", "김관우", "현실주의 종합가 — 명확성·전제오류·오용위험"),
    ("redteam-leeboyoung", "이보영", "프로덕트·UX — 니즈충족·출처·독자적합성"),
    ("redteam-leejinyoung", "이진영", "목회적 따뜻함 + QA — 말씀동반·위로/엄격 균형"),
    ("redteam-kimsoyoung", "김소영", "현장 가정부장 — 행정집·현장 괴리 검증·질문자 마음 보호"),
    ("redteam-miyazakishiho", "미야자키시호", "생활 실무 가정부장 — 실무 디테일 보강·답변 조합 제안"),
    ("redteam-leejuhwa", "이주화", "미래인재부장 — 세대 구분 정확성·의미 중심 교육력"),
]


def esc(s):
    return html.escape(str(s or ""))


def nl(s):
    return esc(s).replace("\n", "<br>")


def botname(bid):
    if str(bid) == "-1":
        return "전봇 공통"
    b = BOTMETA.get(int(bid)) if str(bid).isdigit() else None
    return f"{b['name']} (id{b['id']})" if b else f"id{bid}"


CSS = f"""
:root{{--ink:#1A2233;--sub:#5A6678;--line:#E5E9F0;--bg:#F6F8FB;--card:#fff;--accent:{ACCENT};}}
*{{box-sizing:border-box;}}
body{{margin:0;font-family:-apple-system,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;background:var(--bg);color:var(--ink);line-height:1.6;}}
.wrap{{max-width:1000px;margin:0 auto;padding:32px 20px 80px;}}
header.rpt{{border-left:5px solid var(--accent);padding:6px 0 6px 18px;}}
.eyebrow{{color:var(--accent);font-weight:700;font-size:13px;}}
h1{{margin:6px 0 8px;font-size:26px;}}
.meta{{color:var(--sub);font-size:13px;}}
.persona{{background:#ECFEFF;border:1px solid #A5F3FC;border-radius:10px;padding:12px 16px;font-size:13.5px;color:#155e63;margin:16px 0 22px;}}
h2{{font-size:18px;margin:28px 0 12px;border-bottom:2px solid var(--line);padding-bottom:6px;}}
.rank{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px;}}
.rankpill{{background:#fff;border:1px solid var(--line);border-radius:999px;padding:6px 14px;font-size:13.5px;}}
.rankpill .n{{display:inline-block;background:var(--accent);color:#fff;border-radius:50%;width:20px;height:20px;text-align:center;font-size:12px;font-weight:700;margin-right:6px;}}
.botcard{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin-bottom:14px;}}
.botcard h3{{margin:0 0 6px;font-size:16px;display:flex;align-items:center;gap:10px;}}
.score{{background:var(--accent);color:#fff;border-radius:7px;padding:2px 10px;font-size:14px;font-weight:800;}}
.sub{{color:var(--sub);font-size:12px;font-weight:500;}}
.cols{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:8px;}}
@media(max-width:680px){{.cols{{grid-template-columns:1fr;}}}}
.col h4{{margin:0 0 4px;font-size:12px;color:var(--sub);}}
.col.good h4{{color:#15803d;}}.col.bad h4{{color:#c2410c;}}
.col ul{{margin:0;padding-left:18px;font-size:13.5px;}}
.verdict{{margin-top:8px;font-size:13.5px;background:#F8FAFC;border-left:3px solid var(--accent);padding:6px 12px;}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden;}}
th,td{{padding:8px 11px;font-size:13px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top;}}
th{{background:#FAFBFE;color:var(--sub);}}
.badge{{border-radius:6px;padding:1px 8px;font-size:11.5px;font-weight:700;color:#fff;}}
.overall{{background:#F0FDFA;border:1px solid #99F6E4;border-radius:12px;padding:16px 18px;font-size:14.5px;margin-top:18px;}}
footer{{margin-top:30px;color:#9AA4B2;font-size:12px;text-align:center;}}
"""


def render(agent_key, kname, kdesc, d):
    # 봇 카드 (data 순서 우선, 없으면 BOT_ORDER)
    bots = d.get("bots", [])
    bot_by_id = {int(b["bot_id"]): b for b in bots if str(b.get("bot_id", "")).isdigit()}
    cards = []
    for bid in BOT_ORDER:
        b = bot_by_id.get(bid)
        if not b:
            continue
        good = "".join(f"<li>{esc(x)}</li>" for x in b.get("strengths", []))
        bad = "".join(f"<li>{esc(x)}</li>" for x in b.get("weaknesses", []))
        sc = b.get("score", "—")
        cards.append(f"""
<div class="botcard">
  <h3><span class="score">{esc(sc)}</span>{esc(BOTMETA[bid]['name'])}
    <span class="sub">id{bid} · {esc(BOTMETA[bid]['성격'])} · {BOTMETA[bid]['rag_docs']}문서</span></h3>
  <div class="cols">
    <div class="col good"><h4>좋았던 점</h4><ul>{good or '<li class=sub>—</li>'}</ul></div>
    <div class="col bad"><h4>아쉬운 점·개선</h4><ul>{bad or '<li class=sub>—</li>'}</ul></div>
  </div>
  <div class="verdict">{esc(b.get('verdict',''))}</div>
</div>""")

    # 순위
    ranking = d.get("ranking", [])
    rank_html = "".join(
        f'<span class="rankpill"><span class="n">{i+1}</span>{esc(botname(bid))}</span>'
        for i, bid in enumerate(ranking))

    # 플래그
    flags = d.get("flags", [])
    if flags:
        frows = "".join(
            f"<tr><td>{esc(botname(f.get('bot_id','')))}</td><td>{esc(f.get('qid',''))}</td>"
            f"<td>{esc(f.get('issue',''))}</td>"
            f"<td><span class='badge' style='background:{SEV_COLOR.get(f.get('severity',''),'#666')}'>"
            f"{esc(f.get('severity','-'))}</span></td></tr>"
            for f in flags)
        flag_html = (f"<h2>지적 사항</h2><table><thead><tr><th>봇</th><th>문항</th>"
                     f"<th>이슈</th><th>심각도</th></tr></thead><tbody>{frows}</tbody></table>")
    else:
        flag_html = ""

    # 문항별(선택)
    pq = d.get("per_question", [])
    pq_html = ""
    if pq:
        prows = "".join(
            f"<tr><td>{esc(p.get('qid',''))}</td><td>{esc(botname(p.get('best_bot','')))}</td>"
            f"<td>{esc(p.get('note',''))}</td></tr>" for p in pq)
        pq_html = (f"<h2>문항별 최우수·코멘트</h2><table><thead><tr><th>문항</th>"
                   f"<th>최우수</th><th>코멘트</th></tr></thead><tbody>{prows}</tbody></table>")

    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(kname)} — 5봇 평가</title><style>{CSS}</style></head><body><div class="wrap">
<header class="rpt"><div class="eyebrow">블레싱 3회차 · 에이전트별 정성 리뷰</div>
<h1>{esc(kname)} 평가관 <span style="font-size:15px;color:var(--sub)">({esc(agent_key)})</span></h1>
<div class="meta">난이도 '중' {len(RS['questions'])}문항 · 5봇 상대비교 · 입력=봇별질문응답</div></header>
<div class="persona">{esc(d.get('persona', kdesc))}</div>
<h2>봇 순위 (이 평가관 기준)</h2><div class="rank">{rank_html or '<span class=sub>—</span>'}</div>
<h2>봇별 평가</h2>{''.join(cards)}
{flag_html}
{pq_html}
<div class="overall"><b>종합 총평</b><br>{nl(d.get('overall',''))}</div>
<footer>블레싱 네비게이션 3회차 테스트 · 에이전트별체점 · {esc(kname)}</footer>
</div></body></html>"""


def main():
    n = 0
    for agent_key, kname, kdesc in AGENTS:
        fp = DATADIR / f"{agent_key}.json"
        if not fp.exists():
            print(f"  (건너뜀: {fp.name} 없음)")
            continue
        d = load_tolerant(fp)
        out = OUTDIR / f"{kname}_{agent_key}.html"
        out.write_text(render(agent_key, kname, kdesc, d), encoding="utf-8")
        print(f"  생성: {out.name}")
        n += 1
    print(f"\n에이전트 HTML {n}개 완료")


if __name__ == "__main__":
    main()
