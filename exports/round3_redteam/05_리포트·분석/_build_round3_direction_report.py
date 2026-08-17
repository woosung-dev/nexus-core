# 3주차 레드팀 방향 보고서(정성도 가중 분석) 마크다운을 관리자 공유용 단독 HTML로 렌더링
import re
import markdown
from pathlib import Path

SRC = Path("/Users/woosung/.claude/plans/dapper-snacking-wadler.md")
OUT = Path(__file__).resolve().parent / "블레싱_3주차_레드팀_방향보고서_2026-06-09.html"
GEN_DATE = "2026-06-09"

text = SRC.read_text(encoding="utf-8")

# 첫 H1 을 헤더 배너 제목으로 빼내고 본문에서 제거
title = "3회차(최종) 레드팀 방향 보고서"
m = re.search(r"^#\s+(.+)$", text, flags=re.M)
if m:
    title = m.group(1).strip()
    text = text[: m.start()] + text[m.end():]

# 마크다운이 HTML 태그로 오인하는 bare <followups> 를 코드 스팬으로 감싸 노출 보장
text = text.replace('"<followups>가', '"`<followups>`가')

md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists", "toc", "attr_list"])
body = md.convert(text)
toc = md.toc  # ## 헤딩 기반 목차

HTML = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{
    --accent: #9333EA;        /* 레드팀 보라 */
    --accent-deep: #7C3AED;
    --accent-soft: #F3E8FF;
    --accent-line: #E9D5FF;
    --ink: #1F2430;
    --muted: #6B7280;
    --line: #E5E7EB;
    --bg: #FAFAFB;
    --crit: #DC2626;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--ink);
    font-family: "Pretendard", -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", sans-serif;
    line-height: 1.65; font-size: 15px; -webkit-font-smoothing: antialiased;
  }}
  .wrap {{ max-width: 1000px; margin: 0 auto; padding: 0 20px 80px; }}
  header.banner {{
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent-deep) 100%);
    color: #fff; padding: 40px 20px 34px; margin-bottom: 8px;
  }}
  header.banner .inner {{ max-width: 1000px; margin: 0 auto; }}
  header.banner .eyebrow {{ font-size: 13px; letter-spacing: .12em; text-transform: uppercase; opacity: .85; font-weight: 600; }}
  header.banner h1 {{ margin: 8px 0 10px; font-size: 27px; line-height: 1.3; font-weight: 800; }}
  header.banner .meta {{ font-size: 13.5px; opacity: .9; }}
  header.banner .meta b {{ font-weight: 700; }}

  .layout {{ display: grid; grid-template-columns: 230px 1fr; gap: 36px; align-items: start; margin-top: 28px; }}
  nav.toc {{ position: sticky; top: 20px; font-size: 13px; border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; background: #fff; }}
  nav.toc .toctitle {{ font-weight: 700; color: var(--accent-deep); margin-bottom: 8px; font-size: 12px; letter-spacing: .08em; text-transform: uppercase; }}
  nav.toc ul {{ list-style: none; margin: 0; padding: 0; }}
  nav.toc li {{ margin: 3px 0; }}
  nav.toc a {{ color: var(--muted); text-decoration: none; display: block; padding: 3px 6px; border-radius: 6px; }}
  nav.toc a:hover {{ color: var(--accent-deep); background: var(--accent-soft); }}
  nav.toc > ul > li > ul {{ display: none; }}   /* 2단계까지만 */

  main {{ min-width: 0; }}
  main h2 {{ font-size: 20px; font-weight: 800; margin: 38px 0 14px; padding: 8px 0 8px 14px;
            border-left: 5px solid var(--accent); color: #15181F; scroll-margin-top: 16px; }}
  main h3 {{ font-size: 16px; font-weight: 700; margin: 26px 0 10px; color: var(--accent-deep); }}
  main p {{ margin: 12px 0; }}
  main strong {{ font-weight: 700; color: #111418; }}
  main em {{ color: var(--muted); font-style: italic; }}
  a {{ color: var(--accent-deep); }}
  hr {{ border: 0; border-top: 1px solid var(--line); margin: 30px 0; }}

  blockquote {{ margin: 16px 0; padding: 12px 16px; background: var(--accent-soft);
               border-left: 4px solid var(--accent); border-radius: 0 8px 8px 0; color: #3B2A52; }}
  blockquote p {{ margin: 4px 0; }}

  code {{ background: #F1F1F4; padding: 1.5px 5px; border-radius: 5px; font-size: 12.5px;
         font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; color: #4C1D95; }}
  pre {{ background: #1E1B2E; color: #E9E3F5; padding: 16px 18px; border-radius: 10px; overflow-x: auto;
        font-size: 12.5px; line-height: 1.5; }}
  pre code {{ background: none; color: inherit; padding: 0; }}

  table {{ border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 13px; }}
  th, td {{ border: 1px solid var(--line); padding: 8px 10px; text-align: left; vertical-align: top; word-break: break-word; }}
  thead th {{ background: var(--accent-soft); color: #4C1D95; font-weight: 700; white-space: nowrap; }}
  tbody tr:nth-child(even) {{ background: #FBFAFD; }}
  td strong {{ color: #6D28D9; }}

  .tablescroll {{ overflow-x: auto; }}
  footer {{ margin-top: 50px; padding-top: 18px; border-top: 1px solid var(--line); color: var(--muted); font-size: 12.5px; }}

  @media (max-width: 820px) {{
    .layout {{ grid-template-columns: 1fr; }}
    nav.toc {{ position: static; }}
  }}
  @media print {{
    body {{ background: #fff; font-size: 11px; }}
    header.banner {{ background: var(--accent) !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    nav.toc {{ display: none; }}
    .layout {{ grid-template-columns: 1fr; }}
    thead th {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    h2 {{ page-break-after: avoid; }}
    table {{ page-break-inside: avoid; }}
  }}
</style>
</head>
<body>
<header class="banner">
  <div class="inner">
    <div class="eyebrow">블레싱 네비게이션 · RED TEAM ROUND 3</div>
    <h1>{title}</h1>
    <div class="meta">정성도 가중 분석 · 의사결정용 보고서 &nbsp;|&nbsp; <b>{GEN_DATE}</b> &nbsp;|&nbsp; 주관 신한국협회 가정행복국 · 개발 ㈜포너즈</div>
  </div>
</header>
<div class="wrap">
  <div class="layout">
    <nav class="toc">
      <div class="toctitle">목차</div>
      {toc}
    </nav>
    <main>
      {body}
      <footer>
        본 문서는 1·2차 레드팀 원시 피드백 직접 집계 + 다중 에이전트 분석(정성도 평가 → 가중 합성 → 방향안 → 소크라테스 검증)으로 작성된 의사결정 보고서다.
        직책은 모집 응답 시트 '현재 직책' 기준이며, 정량 지표·인용은 원본 데이터로 재현 가능하다. 생성일 {GEN_DATE}.
      </footer>
    </main>
  </div>
</div>
</body>
</html>
"""

OUT.write_text(HTML, encoding="utf-8")
print(f"WROTE {OUT}  ({len(HTML):,} bytes)")
print(f"toc entries: {toc.count('<a ')}, tables: {body.count('<table>')}")
