# 분류/통계 JSON 을 읽어 클라이언트·관리자용 통계 HTML 보고서(차트 포함)를 생성
import json
from collections import Counter
from datetime import date

BASE = "/Users/woosung/project/agy-project/nexus-core/exports"
classified = json.load(open(f"{BASE}/_classified.json"))
stats = json.load(open(f"{BASE}/_stats.json"))
OUT = f"{BASE}/nexus_chat_report_2026-05-21_to_05-28.html"

# 카테고리 고정 순서/색
CAT_ORDER = [
    "축복 절차·준비", "자격·연령 조건", "순결·과거 고민", "매칭·교류(B4U)",
    "상담·연락처 안내", "축복 정리·재축복", "교육·수련 이수", "의식·예식",
    "신앙·교리·가치", "가정출발·혼인생활", "부모-자녀 소통", "기타·인사", "미분류",
]
PALETTE = [
    "#2F6FED", "#16A34A", "#DC2626", "#9333EA", "#0891B2", "#EA580C",
    "#65A30D", "#DB2777", "#4F46E5", "#0D9488", "#CA8A04", "#64748B", "#94A3B8",
]
PERS_ORDER = [
    "규정·절차 정보제공", "전문가 연결 권유", "공감·정서 위로",
    "신앙적 격려·가치부여", "한계·면책 고지",
]

# 집계
cat_cnt = Counter(c["category"] for c in classified)
pers_cnt = Counter()
for c in classified:
    for p in c["perspectives"]:
        pers_cnt[p] += 1
total_q = len(classified)

# 카테고리별 대표 질문 (각 2개)
examples = {}
for c in classified:
    examples.setdefault(c["category"], [])
    if len(examples[c["category"]]) < 3 and c["q"]:
        examples[c["category"]].append(c["q"][:60])

cat_labels = [c for c in CAT_ORDER if cat_cnt.get(c, 0) > 0]
cat_values = [cat_cnt[c] for c in cat_labels]
cat_colors = [PALETTE[CAT_ORDER.index(c) % len(PALETTE)] for c in cat_labels]

# 카테고리 내림차순(바차트용)
cat_sorted = sorted(zip(cat_labels, cat_values, cat_colors), key=lambda x: -x[1])
bar_labels = [x[0] for x in cat_sorted]
bar_values = [x[1] for x in cat_sorted]
bar_colors = [x[2] for x in cat_sorted]

pers_labels = [p for p in PERS_ORDER if pers_cnt.get(p, 0) > 0]
pers_values = [pers_cnt[p] for p in pers_labels]

daily = stats["daily"]
daily_labels = list(daily.keys())
daily_values = list(daily.values())

fb = stats["feedback"]
fb_up, fb_down, fb_none = fb.get("up", 0), fb.get("down", 0), fb.get("none", 0)
fb_total = fb_up + fb_down
fb_pos_rate = round(fb_up / fb_total * 100) if fb_total else 0

top_cat = cat_sorted[0][0] if cat_sorted else "-"
top_cat_pct = round(cat_sorted[0][1] / total_q * 100) if total_q else 0
top_pers = max(pers_cnt.items(), key=lambda x: x[1])[0] if pers_cnt else "-"
top_pers_pct = round(pers_cnt[top_pers] / total_q * 100) if (pers_cnt and total_q) else 0

# 인사이트 자동 문구
top3 = cat_sorted[:3]
top3_txt = ", ".join(f"<b>{l}</b>({round(v/total_q*100)}%)" for l, v, _ in top3)

example_rows = ""
for l, v, col in cat_sorted:
    exs = " / ".join(examples.get(l, [])) or "-"
    pct = round(v / total_q * 100, 1)
    example_rows += f"""<tr>
      <td><span class="dot" style="background:{col}"></span>{l}</td>
      <td class="num">{v}</td><td class="num">{pct}%</td>
      <td class="ex">{exs}</td></tr>"""

HTML = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nexus 축복 상담 챗봇 — 대화 분석 보고서</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root {{ --ink:#1A2233; --sub:#5A6678; --line:#E5E9F0; --bg:#F6F8FB; --card:#fff; --accent:#2F6FED; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,'Pretendard','Apple SD Gothic Neo',Segoe UI,Roboto,sans-serif;
    background:var(--bg); color:var(--ink); line-height:1.6; -webkit-font-smoothing:antialiased; }}
  .wrap {{ max-width:1120px; margin:0 auto; padding:40px 24px 80px; }}
  header.rpt {{ border-bottom:3px solid var(--accent); padding-bottom:20px; margin-bottom:8px; }}
  header.rpt .eyebrow {{ color:var(--accent); font-weight:700; font-size:13px; letter-spacing:.08em; }}
  header.rpt h1 {{ margin:6px 0 4px; font-size:28px; font-weight:800; }}
  header.rpt .meta {{ color:var(--sub); font-size:14px; }}
  .cards {{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin:28px 0; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px 20px; }}
  .card .label {{ color:var(--sub); font-size:13px; font-weight:600; }}
  .card .value {{ font-size:30px; font-weight:800; margin-top:4px; }}
  .card .value small {{ font-size:14px; font-weight:600; color:var(--sub); }}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; }}
  .panel {{ background:var(--card); border:1px solid var(--line); border-radius:16px; padding:22px 24px; margin-bottom:20px; }}
  .panel h2 {{ margin:0 0 4px; font-size:17px; font-weight:800; }}
  .panel .desc {{ color:var(--sub); font-size:13px; margin-bottom:16px; }}
  .chart-box {{ position:relative; height:300px; }}
  .chart-box.tall {{ height:360px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13.5px; }}
  th,td {{ text-align:left; padding:9px 10px; border-bottom:1px solid var(--line); vertical-align:top; }}
  th {{ color:var(--sub); font-weight:700; font-size:12px; }}
  td.num,th.num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
  td.ex {{ color:var(--sub); font-size:12.5px; }}
  .dot {{ display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:7px; vertical-align:middle; }}
  .insight {{ background:linear-gradient(180deg,#F0F5FF,#fff); border:1px solid #DCE6FB; border-radius:16px;
    padding:22px 24px; margin-bottom:20px; }}
  .insight h2 {{ margin:0 0 10px; font-size:17px; }}
  .insight ul {{ margin:0; padding-left:18px; }}
  .insight li {{ margin:6px 0; }}
  footer {{ color:var(--sub); font-size:12px; text-align:center; margin-top:30px; }}
  @media (max-width:760px) {{ .cards{{grid-template-columns:repeat(2,1fr);}} .grid2{{grid-template-columns:1fr;}} }}
  @media print {{ body{{background:#fff;}} .panel,.card,.insight{{break-inside:avoid;}} }}
</style>
</head>
<body>
<div class="wrap">
  <header class="rpt">
    <div class="eyebrow">NEXUS · 축복 상담 AI 대화 분석</div>
    <h1>주간 대화 분석 보고서</h1>
    <div class="meta">분석 기간 2026-05-21 ~ 2026-05-28 · 테스트 계정(woosung@test.com) 제외 · 생성일 {date.today()}</div>
  </header>

  <div class="cards">
    <div class="card"><div class="label">총 대화 세션</div><div class="value">{stats['sessions']}<small> 건</small></div></div>
    <div class="card"><div class="label">사용자 질문</div><div class="value">{total_q}<small> 건</small></div></div>
    <div class="card"><div class="label">참여 사용자</div><div class="value">{stats['users']}<small> 명</small></div></div>
    <div class="card"><div class="label">긍정 피드백률</div><div class="value">{fb_pos_rate}<small>% ({fb_up}↑/{fb_down}↓)</small></div></div>
  </div>

  <div class="insight">
    <h2>핵심 요약</h2>
    <ul>
      <li>가장 많이 들어온 질문 유형은 {top3_txt} 순입니다.</li>
      <li>AI 답변에서 가장 자주 나타난 관점은 <b>{top_pers}</b>로, 전체 질문의 약 {top_pers_pct}%에서 사용되었습니다.</li>
      <li>답변 대부분이 규정 안내에 그치지 않고 <b>현장 전문가(목회자·가정부장·협회) 연결을 함께 권유</b>하는 안전 지향 패턴을 보였습니다.</li>
      <li>명시적 피드백은 적지만(↑{fb_up} ↓{fb_down}), 부정 피드백 비중이 매우 낮아 답변 수용도가 양호합니다.</li>
    </ul>
  </div>

  <div class="grid2">
    <div class="panel">
      <h2>질문 카테고리 분포</h2>
      <div class="desc">사용자 질문 {total_q}건을 12개 주제로 분류</div>
      <div class="chart-box"><canvas id="catDoughnut"></canvas></div>
    </div>
    <div class="panel">
      <h2>카테고리별 질문 수</h2>
      <div class="desc">많이 들어온 순서</div>
      <div class="chart-box tall"><canvas id="catBar"></canvas></div>
    </div>
  </div>

  <div class="grid2">
    <div class="panel">
      <h2>AI 답변 관점 분포</h2>
      <div class="desc">한 답변에 복수 관점이 포함될 수 있음 (중복 집계)</div>
      <div class="chart-box"><canvas id="persBar"></canvas></div>
    </div>
    <div class="panel">
      <h2>일자별 질문 추이</h2>
      <div class="desc">KST 기준 (메시지 작성 시각)</div>
      <div class="chart-box"><canvas id="dailyLine"></canvas></div>
    </div>
  </div>

  <div class="panel">
    <h2>카테고리별 상세 + 대표 질문</h2>
    <div class="desc">비중과 함께 실제 들어온 질문 예시</div>
    <table>
      <thead><tr><th>카테고리</th><th class="num">건수</th><th class="num">비중</th><th>대표 질문 예시</th></tr></thead>
      <tbody>{example_rows}</tbody>
    </table>
  </div>

  <footer>본 보고서는 Neon 운영 DB의 대화 로그를 기반으로 자동 생성되었으며, 질문/답변 분류는 Gemini 모델로 수행되었습니다.</footer>
</div>

<script>
const CAT = {{labels:{json.dumps(cat_labels, ensure_ascii=False)}, values:{json.dumps(cat_values)}, colors:{json.dumps(cat_colors)}}};
const BAR = {{labels:{json.dumps(bar_labels, ensure_ascii=False)}, values:{json.dumps(bar_values)}, colors:{json.dumps(bar_colors)}}};
const PERS = {{labels:{json.dumps(pers_labels, ensure_ascii=False)}, values:{json.dumps(pers_values)}}};
const DAILY = {{labels:{json.dumps(daily_labels)}, values:{json.dumps(daily_values)}}};
Chart.defaults.font.family = "-apple-system,Pretendard,'Apple SD Gothic Neo',sans-serif";
Chart.defaults.color = "#5A6678";

new Chart(catDoughnut, {{ type:'doughnut',
  data:{{ labels:CAT.labels, datasets:[{{data:CAT.values, backgroundColor:CAT.colors, borderWidth:2, borderColor:'#fff'}}] }},
  options:{{ plugins:{{ legend:{{position:'right', labels:{{boxWidth:12, padding:8, font:{{size:11}}}} }} }}, cutout:'55%' }} }});

new Chart(catBar, {{ type:'bar',
  data:{{ labels:BAR.labels, datasets:[{{data:BAR.values, backgroundColor:BAR.colors, borderRadius:5}}] }},
  options:{{ indexAxis:'y', plugins:{{legend:{{display:false}}}},
    scales:{{ x:{{ beginAtZero:true, grid:{{color:'#EEF1F6'}} }}, y:{{ grid:{{display:false}}, ticks:{{font:{{size:11}}}} }} }} }} }});

new Chart(persBar, {{ type:'bar',
  data:{{ labels:PERS.labels, datasets:[{{data:PERS.values, backgroundColor:'#2F6FED', borderRadius:5}}] }},
  options:{{ indexAxis:'y', plugins:{{legend:{{display:false}}}},
    scales:{{ x:{{ beginAtZero:true, grid:{{color:'#EEF1F6'}} }}, y:{{ grid:{{display:false}} }} }} }} }});

new Chart(dailyLine, {{ type:'line',
  data:{{ labels:DAILY.labels, datasets:[{{data:DAILY.values, borderColor:'#16A34A', backgroundColor:'rgba(22,163,74,.12)',
    fill:true, tension:.35, pointRadius:4, pointBackgroundColor:'#16A34A'}}] }},
  options:{{ plugins:{{legend:{{display:false}}}}, scales:{{ y:{{beginAtZero:true, grid:{{color:'#EEF1F6'}}}}, x:{{grid:{{display:false}}}} }} }} }});
</script>
</body>
</html>"""

open(OUT, "w").write(HTML)
print(f"보고서 저장: {OUT}")
print(f"카테고리 분포: {dict(cat_cnt)}")
print(f"관점 분포: {dict(pers_cnt)}")
