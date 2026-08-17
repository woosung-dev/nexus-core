# 레드팀 피드백 집계/요약 JSON 으로 차트 포함 HTML 보고서를 생성
import json
from datetime import date

BASE = "/Users/woosung/project/agy-project/nexus-core/exports"
data = json.load(open(f"{BASE}/_redteam_data.json"))
summary = json.load(open(f"{BASE}/_redteam_summary.json"))
agg = data["agg"]
OUT = f"{BASE}/redteam_feedback_report_2026-05-22_to_05-28.html"

PALETTE = ["#2F6FED", "#9333EA", "#0891B2", "#EA580C", "#DB2777", "#16A34A", "#CA8A04"]

# 질문유형 (내림차순)
qt = sorted(agg["qtype"].items(), key=lambda x: -x[1])
qt_labels = [k for k, _ in qt]
qt_values = [v for _, v in qt]
qt_colors = [PALETTE[i % len(PALETTE)] for i in range(len(qt))]

# 점수 분포 1~5
score_labels = ["1점", "2점", "3점", "4점", "5점"]
score_values = [agg["score"][str(i)] for i in range(1, 6)]
score_colors = ["#DC2626", "#F87171", "#FBBF24", "#86C765", "#16A34A"]

# 개선영역 (내림차순)
ar = sorted(agg["area"].items(), key=lambda x: -x[1])
ar_labels = [k for k, _ in ar]
ar_values = [v for _, v in ar]

# 질문유형별 평균점수
qa = sorted(agg["qtype_avg"].items(), key=lambda x: x[1])
qa_labels = [k for k, _ in qa]
qa_values = [v for _, v in qa]
qa_colors = ["#DC2626" if v < 3 else "#EA580C" if v < 3.3 else "#16A34A" for v in qa_values]

# 테스터별
us = sorted(agg["user"].items(), key=lambda x: -x[1])
us_labels = [k for k, _ in us]
us_values = [v for _, v in us]

# 일자별
dt = agg["date"]
dt_labels = list(dt.keys())
dt_values = list(dt.values())

# 자유 피드백 주제 카드
theme_cards = ""
for i, t in enumerate(sorted(summary.get("themes", []), key=lambda x: -x.get("count", 0))):
    quotes = "".join(f'<li>"{q}"</li>' for q in t.get("quotes", [])[:2])
    theme_cards += f"""<div class="theme">
      <div class="theme-head"><span class="rank">{i+1}</span><h3>{t['title']}</h3><span class="cnt">{t.get('count','?')}건</span></div>
      <p class="theme-desc">{t.get('desc','')}</p>
      <ul class="quotes">{quotes}</ul>
    </div>"""

# 개선영역 테이블 비중
total = agg["total"]
area_rows = ""
for k, v in ar:
    area_rows += f'<tr><td>{k}</td><td class="num">{v}</td><td class="num">{round(v/total*100)}%</td></tr>'

worst_qt = qa_labels[0] if qa_labels else "-"
worst_score = qa_values[0] if qa_values else 0
top_area = ar_labels[0] if ar_labels else "-"

HTML = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>레드팀 피드백 분석 보고서 — Nexus 축복 상담 AI</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root {{ --ink:#1A2233; --sub:#5A6678; --line:#E5E9F0; --bg:#F6F8FB; --card:#fff; --accent:#9333EA; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,'Pretendard','Apple SD Gothic Neo',Segoe UI,Roboto,sans-serif;
    background:var(--bg); color:var(--ink); line-height:1.6; -webkit-font-smoothing:antialiased; }}
  .wrap {{ max-width:1120px; margin:0 auto; padding:40px 24px 80px; }}
  header.rpt {{ border-bottom:3px solid var(--accent); padding-bottom:20px; }}
  header.rpt .eyebrow {{ color:var(--accent); font-weight:700; font-size:13px; letter-spacing:.08em; }}
  header.rpt h1 {{ margin:6px 0 4px; font-size:28px; font-weight:800; }}
  header.rpt .meta {{ color:var(--sub); font-size:14px; }}
  .cards {{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin:28px 0; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px 20px; }}
  .card .label {{ color:var(--sub); font-size:13px; font-weight:600; }}
  .card .value {{ font-size:30px; font-weight:800; margin-top:4px; }}
  .card .value small {{ font-size:14px; font-weight:600; color:var(--sub); }}
  .card.warn .value {{ color:#DC2626; }}
  .card.good .value {{ color:#16A34A; }}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; }}
  .panel {{ background:var(--card); border:1px solid var(--line); border-radius:16px; padding:22px 24px; margin-bottom:20px; }}
  .panel h2 {{ margin:0 0 4px; font-size:17px; font-weight:800; }}
  .panel .desc {{ color:var(--sub); font-size:13px; margin-bottom:16px; }}
  .chart-box {{ position:relative; height:300px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13.5px; }}
  th,td {{ text-align:left; padding:9px 10px; border-bottom:1px solid var(--line); }}
  th {{ color:var(--sub); font-weight:700; font-size:12px; }}
  td.num,th.num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
  .insight {{ background:linear-gradient(180deg,#FAF5FF,#fff); border:1px solid #EBDDFB; border-radius:16px; padding:22px 24px; margin-bottom:20px; }}
  .insight h2 {{ margin:0 0 10px; font-size:17px; }}
  .insight ul {{ margin:0; padding-left:18px; }} .insight li {{ margin:6px 0; }}
  .themes {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  .theme {{ border:1px solid var(--line); border-radius:14px; padding:16px 18px; background:#fff; }}
  .theme-head {{ display:flex; align-items:center; gap:10px; }}
  .theme-head h3 {{ margin:0; font-size:15px; font-weight:800; flex:1; }}
  .rank {{ width:24px; height:24px; border-radius:50%; background:var(--accent); color:#fff; font-size:13px;
    font-weight:800; display:flex; align-items:center; justify-content:center; }}
  .cnt {{ font-size:12px; font-weight:700; color:var(--accent); background:#F3E8FF; padding:2px 9px; border-radius:20px; }}
  .theme-desc {{ font-size:13px; color:var(--sub); margin:8px 0; }}
  .quotes {{ margin:0; padding-left:16px; }} .quotes li {{ font-size:12.5px; color:#475569; margin:4px 0; }}
  footer {{ color:var(--sub); font-size:12px; text-align:center; margin-top:30px; }}
  @media (max-width:760px) {{ .cards{{grid-template-columns:repeat(2,1fr);}} .grid2,.themes{{grid-template-columns:1fr;}} }}
  @media print {{ body{{background:#fff;}} .wrap{{max-width:none;}} .panel,.card,.insight,.theme{{break-inside:avoid;}} }}
</style>
</head>
<body>
<div class="wrap">
  <header class="rpt">
    <div class="eyebrow">NEXUS · 레드팀 테스트 결과 분석</div>
    <h1>레드팀 피드백 분석 보고서</h1>
    <div class="meta">테스트 기간 2026-05-22 ~ 2026-05-28 · 응답 {agg['total']}건 · 테스터 {agg['users']}명 · 생성일 {date.today()}</div>
  </header>

  <div class="cards">
    <div class="card"><div class="label">총 피드백</div><div class="value">{agg['total']}<small> 건</small></div></div>
    <div class="card good"><div class="label">평균 만족도</div><div class="value">{agg['avg_score']}<small>/5</small></div></div>
    <div class="card warn"><div class="label">부정 평가(1~2점)</div><div class="value">{agg['neg_pct']}<small>% ({agg['neg_count']}건)</small></div></div>
    <div class="card good"><div class="label">긍정 평가(4~5점)</div><div class="value">{agg['pos_pct']}<small>% ({agg['pos_count']}건)</small></div></div>
  </div>

  <div class="insight">
    <h2>핵심 요약</h2>
    <ul>
      <li>{summary.get('overall','')}</li>
      <li>가장 많이 지적된 개선 영역은 <b>{top_area}</b>이며, 질문 유형 중 만족도가 가장 낮은 영역은 <b>{worst_qt}</b>(평균 {worst_score}점)입니다.</li>
      <li>테스트 질문의 대부분({round(qt_values[0]/agg['total']*100)}%)이 <b>{qt_labels[0]}</b>에 집중되어, 해당 영역의 답변 품질이 전체 만족도를 좌우합니다.</li>
    </ul>
  </div>

  <div class="grid2">
    <div class="panel"><h2>테스트 질문 유형</h2><div class="desc">레드팀이 테스트한 질문의 주제 분포</div><div class="chart-box"><canvas id="qtDoughnut"></canvas></div></div>
    <div class="panel"><h2>응답 만족도 분포</h2><div class="desc">5점 척도 · 평가 {agg['rated']}건 (무응답 제외)</div><div class="chart-box"><canvas id="scoreBar"></canvas></div></div>
  </div>

  <div class="grid2">
    <div class="panel"><h2>개선 필요 영역 (복수 선택)</h2><div class="desc">한 응답에서 여러 영역 선택 가능</div><div class="chart-box"><canvas id="areaBar"></canvas></div></div>
    <div class="panel"><h2>질문 유형별 평균 만족도</h2><div class="desc">낮을수록 우선 개선 대상 (빨강&lt;3.0)</div><div class="chart-box"><canvas id="qaBar"></canvas></div></div>
  </div>

  <div class="grid2">
    <div class="panel"><h2>테스터별 응답 수</h2><div class="desc">레드팀 참여 현황</div><div class="chart-box"><canvas id="userBar"></canvas></div></div>
    <div class="panel"><h2>일자별 응답 추이</h2><div class="desc">제출 타임스탬프 기준</div><div class="chart-box"><canvas id="dateLine"></canvas></div></div>
  </div>

  <div class="panel">
    <h2>자유서술 피드백 — 주요 개선 주제</h2>
    <div class="desc">테스터 서술형 의견을 AI로 그룹핑 (언급 빈도순)</div>
    <div class="themes">{theme_cards}</div>
  </div>

  <div class="panel">
    <h2>개선 필요 영역 상세</h2>
    <table><thead><tr><th>개선 영역</th><th class="num">선택 수</th><th class="num">응답 대비</th></tr></thead>
    <tbody>{area_rows}</tbody></table>
  </div>

  <footer>본 보고서는 레드팀 피드백 설문(Google Forms) 150건을 기반으로 자동 생성되었으며, 자유서술 의견 요약은 OpenAI 모델로 수행되었습니다.</footer>
</div>
<script>
Chart.defaults.font.family="-apple-system,Pretendard,'Apple SD Gothic Neo',sans-serif";
Chart.defaults.color="#5A6678";
new Chart(qtDoughnut,{{type:'doughnut',data:{{labels:{json.dumps(qt_labels,ensure_ascii=False)},datasets:[{{data:{json.dumps(qt_values)},backgroundColor:{json.dumps(qt_colors)},borderWidth:2,borderColor:'#fff'}}]}},options:{{plugins:{{legend:{{position:'right',labels:{{boxWidth:12,padding:8,font:{{size:11}}}}}}}},cutout:'55%'}}}});
new Chart(scoreBar,{{type:'bar',data:{{labels:{json.dumps(score_labels,ensure_ascii=False)},datasets:[{{data:{json.dumps(score_values)},backgroundColor:{json.dumps(score_colors)},borderRadius:5}}]}},options:{{plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:true,grid:{{color:'#EEF1F6'}}}},x:{{grid:{{display:false}}}}}}}}}});
new Chart(areaBar,{{type:'bar',data:{{labels:{json.dumps(ar_labels,ensure_ascii=False)},datasets:[{{data:{json.dumps(ar_values)},backgroundColor:'#9333EA',borderRadius:5}}]}},options:{{indexAxis:'y',plugins:{{legend:{{display:false}}}},scales:{{x:{{beginAtZero:true,grid:{{color:'#EEF1F6'}}}},y:{{grid:{{display:false}},ticks:{{font:{{size:10.5}}}}}}}}}}}});
new Chart(qaBar,{{type:'bar',data:{{labels:{json.dumps(qa_labels,ensure_ascii=False)},datasets:[{{data:{json.dumps(qa_values)},backgroundColor:{json.dumps(qa_colors)},borderRadius:5}}]}},options:{{indexAxis:'y',plugins:{{legend:{{display:false}}}},scales:{{x:{{beginAtZero:true,max:5,grid:{{color:'#EEF1F6'}}}},y:{{grid:{{display:false}},ticks:{{font:{{size:10.5}}}}}}}}}}}});
new Chart(userBar,{{type:'bar',data:{{labels:{json.dumps(us_labels,ensure_ascii=False)},datasets:[{{data:{json.dumps(us_values)},backgroundColor:'#0891B2',borderRadius:5}}]}},options:{{plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:true,grid:{{color:'#EEF1F6'}}}},x:{{grid:{{display:false}}}}}}}}}});
new Chart(dateLine,{{type:'line',data:{{labels:{json.dumps(dt_labels)},datasets:[{{data:{json.dumps(dt_values)},borderColor:'#9333EA',backgroundColor:'rgba(147,51,234,.12)',fill:true,tension:.35,pointRadius:4,pointBackgroundColor:'#9333EA'}}]}},options:{{plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:true,grid:{{color:'#EEF1F6'}}}},x:{{grid:{{display:false}}}}}}}}}});
</script>
</body>
</html>"""

open(OUT, "w").write(HTML)
print("보고서 저장:", OUT)
