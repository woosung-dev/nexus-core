# 3주차 레드팀(라이브 C/D 블라인드) 응답 xlsx를 필터형 HTML 보고서로 변환하는 빌드 스크립트
import openpyxl, json, collections, statistics, pathlib

SRC = "/Users/woosung/Downloads/축복·가정관리 AI 상담 챗봇 테스트 및 피드백 v3주차(레드팀)(응답) (3).xlsx"
OUT_DIR = pathlib.Path(__file__).parent
OUT_HTML = OUT_DIR / "3주차_레드팀_CD_보고서.html"
OUT_JSON = OUT_DIR / "_data" / "responses.json"


def norm_risk(v):
    s = (v or "").strip()
    if s.startswith("상"):
        return "상"
    if s.startswith("중"):
        return "중"
    if s.startswith("하"):
        return "하"
    if s == "없음" or s == "":
        return "없음"
    return "없음"


def norm_pref(v):
    s = (v or "").strip()
    if "챗봇D" in s:
        return "D"
    if "챗봇C" in s:
        return "C"
    if "챗봇A" in s:
        return "A"
    if "챗봇B" in s:
        return "B"
    if "둘다" in s:
        return "둘다부적절"
    return "기타"


def to_score(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load():
    wb = openpyxl.load_workbook(SRC, data_only=True)
    ws = wb.active
    rows = [r for r in ws.iter_rows(min_row=2, values_only=True)
            if any(c is not None and str(c).strip() for c in r)]
    out = []
    for i, r in enumerate(rows):
        ts = r[0]
        sc = to_score(r[6])
        out.append({
            "id": i + 1,
            "ts": str(ts)[:19] if ts else "",
            "evaluator": (str(r[1]).strip() if r[1] else ""),
            "question": (str(r[2]).strip() if r[2] else ""),
            "respC": (str(r[3]).strip() if r[3] else ""),
            "respD": (str(r[4]).strip() if r[4] else ""),
            "prefRaw": (str(r[5]).strip() if r[5] else ""),
            "pref": norm_pref(str(r[5]) if r[5] else ""),
            "score": sc,
            "good": (str(r[7]).strip() if r[7] else ""),
            "bad": (str(r[8]).strip() if r[8] else ""),
            "suggest": (str(r[9]).strip() if r[9] else ""),
            "riskRaw": (str(r[10]).strip() if r[10] else ""),
            "risk": norm_risk(str(r[10]) if r[10] else ""),
            "etc": (str(r[11]).strip() if r[11] else ""),
        })
    return out


def stats(data):
    n = len(data)
    evs = collections.Counter(d["evaluator"] for d in data)
    pref = collections.Counter(d["pref"] for d in data)
    risk = collections.Counter(d["risk"] for d in data)
    scores = [d["score"] for d in data if d["score"] is not None]
    score_dist = collections.Counter(int(s) for s in scores)
    # 평가자별 집계
    per_ev = {}
    for ev, cnt in evs.items():
        sub = [d for d in data if d["evaluator"] == ev]
        ss = [d["score"] for d in sub if d["score"] is not None]
        per_ev[ev] = {
            "count": cnt,
            "avg": round(statistics.mean(ss), 2) if ss else None,
            "D": sum(1 for d in sub if d["pref"] == "D"),
            "C": sum(1 for d in sub if d["pref"] == "C"),
            "critical": sum(1 for d in sub if d["risk"] == "상"),
        }
    # 선호봇 x 위험도 교차
    cross = collections.defaultdict(lambda: collections.Counter())
    for d in data:
        cross[d["pref"]][d["risk"]] += 1
    return {
        "n": n,
        "evaluators": evs.most_common(),
        "pref": pref.most_common(),
        "risk": {k: risk.get(k, 0) for k in ["상", "중", "하", "없음"]},
        "score_avg": round(statistics.mean(scores), 2) if scores else None,
        "score_dist": {str(k): score_dist.get(k, 0) for k in [5, 4, 3, 2, 1]},
        "per_ev": per_ev,
        "cross": {k: dict(v) for k, v in cross.items()},
    }


# 평가자 자유서술을 읽고 각 응답을 단일 범주에 배정한 분류 결과(분석자 수기 분류).
# 범주별 ids 합계는 각 그룹 모수(상16·중53·1·2점34)와 일치하도록 검증됨.
CATEGORIES = {
    "상": {
        "title": "위험도 '상' 주요 카테고리",
        "subtitle": "즉시 차단·수정 검토 대상 16건을 사유별로 분류",
        "cats": [
            {"name": "세대(1·2세) 규정 오적용", "insight":
             "1세 기준(40일 성별실패·은사 자녀 기준)을 2세 가정에 그대로 적용해 사실을 왜곡. 2세-1세 가정의 2세편성/1세편성(탕감봉·3일행사 vs 12일 의식) 분기와 다수인 2세-2세 청년 기준이 누락됨.",
             "ids": [104, 119, 227, 230, 231]},
            {"name": "RAG 데이터 부재 → 회피·오답", "insight":
             "회비·자녀 의례(봉헌식)·국제축복 서류가 규정집에 없어 답을 회피하거나 엉뚱한 서류를 안내.",
             "ids": [134, 137, 141, 160]},
            {"name": "시점별 규정 오류(정리·성화·환불)", "insight":
             "축복식 전/후, 3일행사 전/후 같은 시점 분기를 놓쳐 환불 가부·재축복 가부를 잘못 안내.",
             "ids": [117, 118]},
            {"name": "핵심 정성규정 누락(금식 등)", "insight":
             "3일 금식 같은 행정상 필수 정성 조건을 누락한 팩트 오류.",
             "ids": [62, 189]},
            {"name": "가해/피해 구분 폐지 미반영", "insight":
             "폐지된 가해자/피해자 구분을 여전히 적용. 누락 공문 미반영이 직접 원인.",
             "ids": [217]},
            {"name": "위험도 과표기 추정(내용 경미)", "insight":
             "평가자가 '상'으로 표기했으나 본문은 칭찬·경미한 보완 의견. 집계 해석 시 참고.",
             "ids": [192]},
            {"name": "말씀·섭리 의미 응답 부적절", "insight":
             "'축복을 왜 받아야 하는가' 같은 근본 의미 질문에 부적절하게 답해 설득력·정확성이 떨어짐.",
             "ids": [258]},
        ],
    },
    "중": {
        "title": "위험도 '중' 주요 카테고리",
        "subtitle": "정보 누락·회피·규정 불일치 53건을 사유별로 분류",
        "cats": [
            {"name": "축복정리·재축복·은사·무효화 기준", "insight":
             "1년 정리 제한, 5% 책임, 은사 고백 대상, 무효화 사유, 자살자 성화 가부, 사진 참석 가정 재축복 여부 등 핵심 기준을 누락하거나 부정확하게 안내.",
             "ids": [68, 69, 114, 115, 116, 123, 125, 128, 216, 232, 240, 255]},
            {"name": "회피·무응답(RAG 데이터 갭)", "insight":
             "말씀 전문·교육 프로그램·축복식 날짜·수련 절차가 규정집에 없어 답하지 못하거나 추상적으로 회피.",
             "ids": [21, 90, 100, 142, 143, 144, 210]},
            {"name": "질문 의도·맥락 오판", "insight":
             "'만약 ~라면' 같은 가상 질문을 실제 상황으로 착각하거나 핵심 의도를 빗나간 응답.",
             "ids": [180, 196, 197, 199, 213, 214]},
            {"name": "세대(1·2세·축복자녀) 규정 분기 미흡", "insight":
             "40일 성별·3일행사가 1세 포함 커플에만 적용됨에도 모든 축복에 필수인 것처럼 안내. 2세 40일 정성기간을 1세 성별기간으로 혼동하거나 1·2세별 헌금·예배·금식 기준을 분리하지 못함.",
             "ids": [55, 56, 57, 99, 215, 229, 241]},
            {"name": "탈선·순결·성문제 판단 기준", "insight":
             "직접/간접 접촉, 12세 미만 피해, 탈선/중도/경도 구분, 6개월 순결 기준의 과거 적용 범위 등 세부 판단 기준이 단정적이거나 누락·모호.",
             "ids": [98, 110, 111, 113, 121, 237, 248]},
            {"name": "회비·기금 용어 설명 모호·중복", "insight":
             "가정회비·가정기금·하늘공관금·유아기금 설명이 서로 비슷하고 추상적이어서 변별이 안 됨.",
             "ids": [136, 138, 139, 140, 188]},
            {"name": "말씀·섭리 깊이 부족(규정집 위주)", "insight":
             "규정 전달에 치우쳐 신앙·섭리적 의미와 말씀 인용의 깊이가 부족.",
             "ids": [65, 67, 72, 132]},
            {"name": "안전·오용 위험 안내", "insight":
             "6개월 교제 조건·지인 소개·2세-1세 권장 뉘앙스가 섭리적 꼼수나 오용을 부추길 수 있음.",
             "ids": [24, 47, 179]},
            {"name": "상담·톤·신앙 연결", "insight":
             "재축복을 '죄'로 프레이밍하는 등 상담적 배려·신앙 연결 톤이 아쉬움.",
             "ids": [129, 200]},
        ],
    },
    "저점": {
        "title": "낮은 점수(2점·1점) 주요 카테고리",
        "subtitle": "적절성 1·2점 34건(1점 15·2점 19)을 사유별로 분류",
        "cats": [
            {"name": "회피·무응답(RAG 데이터 갭)", "insight":
             "회비·유아회비·국제축복 서류·축복식 날짜·말씀 전문이 규정집에 없어 답을 주지 못함. 최저점의 최대 원인.",
             "ids": [21, 90, 136, 137, 139, 141, 160, 210]},
            {"name": "세대 규정 오적용·누락", "insight":
             "2세 40일·12일 의식을 잘못 적용하거나 2세-2세 다수 기준을 통째로 누락. 2세-1세 편성 분기를 놓치거나 2세 정성기간을 1세 성별기간으로 혼동.",
             "ids": [55, 57, 104, 116, 119, 215, 227, 230, 231, 241]},
            {"name": "질문 의도·맥락 오판", "insight":
             "가상 질문을 실제로 착각하거나 질문 핵심을 빗나가 엉뚱한 위로·답변.",
             "ids": [80, 83, 180, 181, 197, 202]},
            {"name": "상담·톤·신앙 연결", "insight":
             "단호·딱딱한 톤, 신앙으로 자연스럽게 잇지 못함, 상담적 요소 부족. 의미 질문 응답 부적절·부적절한 용어로 거부감 유발.",
             "ids": [28, 68, 88, 129, 255, 258]},
            {"name": "시점별 규정 오류(정리·성화·환불)", "insight":
             "축복식 전/후 시점 분기를 놓쳐 환불·재축복 가부를 잘못 안내.",
             "ids": [117, 118]},
            {"name": "규정 정확성(가해피해·의례)", "insight":
             "폐지된 가해/피해 구분 잔존, 자녀 탄생 후 봉헌식 등 의례 누락.",
             "ids": [134, 217]},
        ],
    },
}


PREF_LABEL = {
    "D": "챗봇D · 여정 동반자",
    "C": "챗봇C · 따뜻한 실무안내자",
    "둘다부적절": "둘다 적절하지 못함",
    "B": "챗봇B(정밀) 라벨",
    "A": "챗봇A(통합) 라벨",
    "기타": "기타",
}
RISK_LABEL = {"상": "상 · 위험", "중": "중 · 주의", "하": "하 · 개선", "없음": "없음"}


def render(data, st):
    payload = json.dumps(data, ensure_ascii=False)
    st_json = json.dumps(st, ensure_ascii=False)
    pref_label = json.dumps(PREF_LABEL, ensure_ascii=False)
    risk_label = json.dumps(RISK_LABEL, ensure_ascii=False)
    tpl = TEMPLATE
    tpl = tpl.replace("__DATA__", payload)
    tpl = tpl.replace("__STATS__", st_json)
    tpl = tpl.replace("__PREF_LABEL__", pref_label)
    tpl = tpl.replace("__RISK_LABEL__", risk_label)
    tpl = tpl.replace("__CATEGORIES__", json.dumps(CATEGORIES, ensure_ascii=False))
    return tpl


TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>3주차 레드팀 · 라이브 C/D 블라인드 평가 보고서</title>
<style>
:root{
  --bg:#0f1115; --panel:#171a21; --panel2:#1d212b; --line:#2a2f3a;
  --txt:#e7eaf0; --mut:#9aa3b2; --acc:#5b8cff; --accD:#7c5bff;
  --C:#36c5a8; --D:#7c5bff; --both:#8a93a3;
  --r-sang:#ff5d5d; --r-jung:#ffb02e; --r-ha:#4aa3ff; --r-none:#3a414f;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);
  font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Pretendard","Noto Sans KR",sans-serif;
  font-size:14px;line-height:1.65}
.wrap{max-width:1280px;margin:0 auto;padding:24px}
h1{font-size:22px;margin:0 0 4px}
.sub{color:var(--mut);font-size:13px;margin-bottom:20px}
.grid{display:grid;gap:14px}
.cards{grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
.kpi .big{font-size:28px;font-weight:700}
.kpi .lab{color:var(--mut);font-size:12px;margin-top:2px}
.section-title{font-size:15px;font-weight:700;margin:26px 0 10px;display:flex;align-items:center;gap:8px}
.bar-row{display:flex;align-items:center;gap:10px;margin:6px 0;font-size:12px}
.bar-row .lab{width:160px;flex:0 0 160px;color:var(--mut);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar-track{flex:1;background:#11141a;border-radius:6px;height:18px;position:relative;overflow:hidden}
.bar-fill{height:100%;border-radius:6px;min-width:2px}
.bar-row .num{width:54px;flex:0 0 54px;text-align:right;color:var(--txt);font-variant-numeric:tabular-nums}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line)}
th{color:var(--mut);font-weight:600;position:sticky;top:0;background:var(--panel)}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.filters{position:sticky;top:0;z-index:20;background:rgba(15,17,21,.92);backdrop-filter:blur(8px);
  border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:18px 0}
.filt-grp{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:5px 0}
.filt-grp .glab{color:var(--mut);font-size:12px;width:64px;flex:0 0 64px}
.chip{border:1px solid var(--line);background:var(--panel2);color:var(--txt);
  border-radius:20px;padding:4px 11px;font-size:12px;cursor:pointer;user-select:none}
.chip.on{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:600}
.chip.risk-상.on{background:var(--r-sang);border-color:var(--r-sang)}
.chip.risk-중.on{background:var(--r-jung);border-color:var(--r-jung);color:#1a1a1a}
.chip.risk-하.on{background:var(--r-ha);border-color:var(--r-ha)}
.chip.pref-D.on{background:var(--D);border-color:var(--D)}
.chip.pref-C.on{background:var(--C);border-color:var(--C);color:#06231d}
input[type=search]{flex:1;min-width:180px;background:#11141a;border:1px solid var(--line);
  border-radius:8px;color:var(--txt);padding:7px 11px;font-size:13px}
.count-line{color:var(--mut);font-size:12px;margin:10px 2px}
.btn{background:var(--panel2);border:1px solid var(--line);color:var(--txt);border-radius:8px;
  padding:5px 10px;font-size:12px;cursor:pointer}
.btn:hover{border-color:var(--acc)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;margin:12px 0;overflow:hidden}
.card-head{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:12px 14px;
  background:var(--panel2);border-bottom:1px solid var(--line);cursor:pointer}
.card-head .q{font-weight:600;flex:1;min-width:200px}
.badge{font-size:11px;padding:2px 8px;border-radius:20px;white-space:nowrap}
.b-ev{background:#222838;color:#bcd}
.b-pref{font-weight:600}
.b-pref.D{background:rgba(124,91,255,.18);color:#b7a4ff}
.b-pref.C{background:rgba(54,197,168,.18);color:#67e3c8}
.b-pref.둘다부적절{background:rgba(138,147,163,.18);color:#c2c8d2}
.b-pref.A,.b-pref.B{background:rgba(255,176,46,.14);color:#ffce7a}
.b-score{background:#1c2330;color:#cfe}
.b-risk-상{background:var(--r-sang);color:#fff}
.b-risk-중{background:var(--r-jung);color:#1a1a1a}
.b-risk-하{background:rgba(74,163,255,.2);color:#9cc8ff}
.b-risk-없음{background:#262c38;color:#9aa3b2}
.card-body{padding:0 14px;max-height:0;overflow:hidden;transition:max-height .25s ease}
.card.open .card-body{max-height:6000px;padding:14px}
.resps{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:820px){.resps{grid-template-columns:1fr}.bar-row .lab{width:110px;flex-basis:110px}}
.resp{background:#11141a;border:1px solid var(--line);border-radius:8px;padding:10px 12px}
.resp h4{margin:0 0 6px;font-size:12px;color:var(--mut)}
.resp.win{border-color:var(--acc)}
.resp.win.D{border-color:var(--D)}
.resp.win.C{border-color:var(--C)}
.resp .txt{font-size:12.5px;white-space:pre-wrap;word-break:break-word;color:#d6dae3;max-height:300px;overflow:auto}
.fb{margin-top:12px;display:grid;gap:8px}
.fb .item{font-size:12.5px}
.fb .k{color:var(--mut);font-size:11px;margin-bottom:2px}
.fb .v{white-space:pre-wrap}
.empty{color:var(--mut);text-align:center;padding:40px}
.legend{font-size:11px;color:var(--mut);margin-top:4px}
.an-head{display:flex;align-items:baseline;gap:10px;margin:30px 0 4px}
.an-head .pill{font-size:12px;padding:2px 10px;border-radius:20px;font-weight:700}
.an-sub{color:var(--mut);font-size:12.5px;margin:0 0 12px}
.cat-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:820px){.cat-grid{grid-template-columns:1fr}}
.cat{background:var(--panel);border:1px solid var(--line);border-left-width:4px;border-radius:10px;padding:13px 15px}
.cat .ch{display:flex;align-items:center;gap:8px;margin-bottom:5px}
.cat .cn{font-weight:700;font-size:13.5px}
.cat .cc{font-size:11px;background:#222838;color:#cdd6e6;border-radius:20px;padding:1px 9px;font-variant-numeric:tabular-nums}
.cat .ci{font-size:12.5px;color:#c4cbd6;margin:0 0 9px;line-height:1.55}
.cat .ids{display:flex;flex-wrap:wrap;gap:5px}
.idchip{font-size:11px;background:#11141a;border:1px solid var(--line);border-radius:6px;
  padding:3px 8px;cursor:pointer;color:#aeb6c4;max-width:230px;overflow:hidden;
  white-space:nowrap;text-overflow:ellipsis}
.idchip:hover{border-color:var(--acc);color:#fff}
.idchip b{color:var(--acc)}
.card.flash{animation:flash 1.4s ease}
@keyframes flash{0%,40%{box-shadow:0 0 0 2px var(--acc)}100%{box-shadow:none}}
.note{background:rgba(255,176,46,.08);border:1px solid rgba(255,176,46,.3);border-radius:10px;
  padding:12px 14px;font-size:12.5px;color:#e8d6b0;margin:14px 0}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:820px){.two-col{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="wrap">
  <h1>3주차 레드팀 · 라이브 C/D 블라인드 평가 보고서</h1>
  <div class="sub" id="subline"></div>

  <div class="grid cards" id="kpis"></div>

  <div class="note">
    <b>데이터 품질 주의.</b> 응답 컬럼은 <b>챗봇C·챗봇D</b> 두 종만 제시되었으나, "적절한 챗봇" 선택지에
    이전 회차의 <b>챗봇A(통합)·챗봇B(정밀)</b> 라벨이 남아 있어 일부 평가자(주로 이보영)가 묘사용으로 A/B를 선택함.
    아래 통계에서 A·B 선택은 별도 표기하며, 핵심 비교축은 <b>C vs D</b>임.
  </div>

  <div class="two-col">
    <div class="panel">
      <div class="section-title">선호 챗봇 분포</div>
      <div id="chart-pref"></div>
    </div>
    <div class="panel">
      <div class="section-title">위험도 분포</div>
      <div id="chart-risk"></div>
      <div class="legend">상=즉시 차단 · 중=정보누락/규정불일치 · 하=어투·UX 개선 · 없음=문제없음</div>
    </div>
  </div>

  <div class="two-col" style="margin-top:14px">
    <div class="panel">
      <div class="section-title">적절성·유용성 점수 분포 (5점 척도)</div>
      <div id="chart-score"></div>
    </div>
    <div class="panel">
      <div class="section-title">선호봇 × 위험도 교차</div>
      <div id="chart-cross"></div>
    </div>
  </div>

  <div class="panel" style="margin-top:14px">
    <div class="section-title">평가자별 집계</div>
    <div style="overflow:auto">
      <table id="ev-table">
        <thead><tr>
          <th>평가자</th><th class="num">건수</th><th class="num">평균점</th>
          <th class="num">D선호</th><th class="num">C선호</th><th class="num">상위험</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </div>

  <div id="analysis"></div>

  <div class="section-title" style="margin-top:30px">개별 응답 (필터 가능)</div>
  <div class="filters">
    <div class="filt-grp">
      <span class="glab">평가자</span><span id="f-ev"></span>
    </div>
    <div class="filt-grp">
      <span class="glab">선호봇</span><span id="f-pref"></span>
    </div>
    <div class="filt-grp">
      <span class="glab">위험도</span><span id="f-risk"></span>
    </div>
    <div class="filt-grp">
      <span class="glab">점수</span><span id="f-score"></span>
    </div>
    <div class="filt-grp">
      <input type="search" id="f-text" placeholder="질문·응답·피드백 본문 검색…">
      <button class="btn" id="reset">필터 초기화</button>
      <button class="btn" id="expand">전체 펼치기</button>
    </div>
  </div>
  <div class="count-line" id="count"></div>
  <div id="list"></div>
</div>

<script>
const DATA = __DATA__;
const ST = __STATS__;
const PREF_LABEL = __PREF_LABEL__;
const RISK_LABEL = __RISK_LABEL__;
const CATEGORIES = __CATEGORIES__;
const PREF_COLOR = {D:"var(--D)",C:"var(--C)","둘다부적절":"var(--both)",A:"#ffb02e",B:"#ffb02e",기타:"#666"};
const RISK_COLOR = {"상":"var(--r-sang)","중":"var(--r-jung)","하":"var(--r-ha)","없음":"var(--r-none)"};
const esc = s => (s||"").replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));

// ---------- KPI ----------
const cD = ST.pref.find(p=>p[0]==="D"), cC = ST.pref.find(p=>p[0]==="C");
const dN = cD?cD[1]:0, cN = cC?cC[1]:0;
document.getElementById("subline").textContent =
  `총 ${ST.n}건 · 평가자 ${ST.evaluators.length}명 · 평균 적절성 ${ST.score_avg}점 · 라이브 Neon C(id6)·D(id7) 블라인드 A/B`;
const kpis = [
  ["총 응답", ST.n, ""],
  ["평가자", ST.evaluators.length+"명", ""],
  ["챗봇D 선호", dN, `C 대비 ${dN+cN?Math.round(dN/(dN+cN)*100):0}%`],
  ["챗봇C 선호", cN, `D 대비 ${dN+cN?Math.round(cN/(dN+cN)*100):0}%`],
  ["평균 적절성", ST.score_avg, "5점 척도"],
  ["상위험 건수", ST.risk["상"], "즉시 차단 검토"],
];
document.getElementById("kpis").innerHTML = kpis.map(k=>
  `<div class="panel kpi"><div class="big">${k[1]}</div><div class="lab">${k[0]}</div>${k[2]?`<div class="lab" style="color:var(--acc)">${k[2]}</div>`:""}</div>`).join("");

// ---------- bar chart helper ----------
function barChart(el, rows, total, colorFn){
  const max = Math.max(...rows.map(r=>r[1]), 1);
  el.innerHTML = rows.map(r=>{
    const pct = (r[1]/max*100).toFixed(1);
    const numTxt = total ? `${r[1]} · ${(r[1]/total*100).toFixed(0)}%` : `${r[1]}`;
    return `<div class="bar-row"><div class="lab" title="${esc(r[0])}">${esc(r[0])}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${colorFn(r)}"></div></div>
      <div class="num">${numTxt}</div></div>`;
  }).join("");
}
barChart(document.getElementById("chart-pref"),
  ST.pref.map(p=>[PREF_LABEL[p[0]]||p[0], p[1], p[0]]), ST.n, r=>PREF_COLOR[r[2]]||"#666");
barChart(document.getElementById("chart-risk"),
  ["상","중","하","없음"].map(k=>[RISK_LABEL[k], ST.risk[k], k]), ST.n, r=>RISK_COLOR[r[2]]);
barChart(document.getElementById("chart-score"),
  ["5","4","3","2","1"].map(k=>[k+"점", ST.score_dist[k]||0, k]), ST.n,
  r=>({"5":"#36c5a8","4":"#7cc36a","3":"#ffb02e","2":"#ff8a4a","1":"#ff5d5d"}[r[2]]));

// cross: pref x risk stacked-ish (간단히 상+중 위험 비율 표시)
const crossRows = ST.pref.map(p=>{
  const c = ST.cross[p[0]]||{};
  const danger = (c["상"]||0)+(c["중"]||0);
  const tot = Object.values(c).reduce((a,b)=>a+b,0);
  return [`${PREF_LABEL[p[0]]||p[0]} (상+중 ${danger}/${tot})`, danger, p[0]];
});
barChart(document.getElementById("chart-cross"), crossRows, null, r=>RISK_COLOR["중"]);

// ---------- evaluator table ----------
const evRows = Object.entries(ST.per_ev).sort((a,b)=>b[1].count-a[1].count);
document.querySelector("#ev-table tbody").innerHTML = evRows.map(([ev,v])=>
  `<tr><td>${esc(ev)}</td><td class="num">${v.count}</td><td class="num">${v.avg??"-"}</td>
   <td class="num">${v.D}</td><td class="num">${v.C}</td>
   <td class="num">${v.critical?`<b style="color:var(--r-sang)">${v.critical}</b>`:0}</td></tr>`).join("");

// ---------- filters ----------
const F = {ev:new Set(), pref:new Set(), risk:new Set(), score:new Set(), text:""};
function chipRow(host, items, key, cls){
  host.innerHTML = items.map(it=>
    `<span class="chip ${cls?cls+it[0]:""}" data-k="${key}" data-v="${it[0]}">${esc(it[1])} <span style="opacity:.6">${it[2]??""}</span></span>`).join("");
}
chipRow(document.getElementById("f-ev"),
  ST.evaluators.map(e=>[e[0],e[0],e[1]]), "ev");
chipRow(document.getElementById("f-pref"),
  ["D","C","둘다부적절","A","B"].filter(k=>ST.pref.some(p=>p[0]===k))
    .map(k=>[k, PREF_LABEL[k], ST.pref.find(p=>p[0]===k)[1]]), "pref", "pref-");
chipRow(document.getElementById("f-risk"),
  ["상","중","하","없음"].map(k=>[k, RISK_LABEL[k], ST.risk[k]]), "risk", "risk-");
chipRow(document.getElementById("f-score"),
  ["5","4","3","2","1"].map(k=>[k, k+"점", ST.score_dist[k]||0]), "score");

document.querySelectorAll(".chip").forEach(ch=>ch.addEventListener("click",()=>{
  const k=ch.dataset.k, v=ch.dataset.v;
  if(F[k].has(v)){F[k].delete(v);ch.classList.remove("on");}
  else{F[k].add(v);ch.classList.add("on");}
  render();
}));
document.getElementById("f-text").addEventListener("input",e=>{F.text=e.target.value.toLowerCase();render();});
document.getElementById("reset").addEventListener("click",()=>{
  F.ev.clear();F.pref.clear();F.risk.clear();F.score.clear();F.text="";
  document.getElementById("f-text").value="";
  document.querySelectorAll(".chip.on").forEach(c=>c.classList.remove("on"));
  render();
});
let expanded=false;
document.getElementById("expand").addEventListener("click",()=>{
  expanded=!expanded;
  document.getElementById("expand").textContent = expanded?"전체 접기":"전체 펼치기";
  document.querySelectorAll(".card").forEach(c=>c.classList.toggle("open",expanded));
});

// ---------- analysis (category) sections ----------
const BY_ID = Object.fromEntries(DATA.map(d=>[d.id,d]));
const GROUP_STYLE = {
  "상":{color:"var(--r-sang)", pill:"위험도 상"},
  "중":{color:"var(--r-jung)", pill:"위험도 중", pillTxt:"#1a1a1a"},
  "저점":{color:"#ff8a4a", pill:"점수 1·2점"},
};
function catSection(key, group){
  const gs = GROUP_STYLE[key];
  const cats = group.cats.slice().sort((a,b)=>b.ids.length-a.ids.length);
  const cards = cats.map(c=>{
    const ids = c.ids.map(id=>{
      const d = BY_ID[id]; if(!d) return "";
      const q = (d.question||"").slice(0,30);
      return `<span class="idchip" onclick="jumpTo(${id})" title="${esc(d.question)}"><b>#${id}</b> ${esc(q)}</span>`;
    }).join("");
    return `<div class="cat" style="border-left-color:${gs.color}">
      <div class="ch"><span class="cn">${esc(c.name)}</span><span class="cc">${c.ids.length}건</span></div>
      <p class="ci">${esc(c.insight)}</p>
      <div class="ids">${ids}</div>
    </div>`;
  }).join("");
  const tot = cats.reduce((a,c)=>a+c.ids.length,0);
  return `<div class="an-head">
      <span class="pill" style="background:${gs.color};color:${gs.pillTxt||'#fff'}">${gs.pill}</span>
      <span class="section-title" style="margin:0">${esc(group.title)}</span>
      <span style="color:var(--mut);font-size:12px">총 ${tot}건 · ${cats.length}개 범주</span>
    </div>
    <p class="an-sub">${esc(group.subtitle)} · 칩을 누르면 해당 응답으로 이동</p>
    <div class="cat-grid">${cards}</div>`;
}
document.getElementById("analysis").innerHTML =
  ["상","중","저점"].map(k=>catSection(k, CATEGORIES[k])).join("");

function jumpTo(id){
  document.getElementById("reset").click();      // 필터 해제 후 전체에서 탐색
  const card = document.querySelector(`.card[data-id="${id}"]`);
  if(!card) return;
  card.classList.add("open");
  card.scrollIntoView({behavior:"smooth", block:"center"});
  card.classList.remove("flash"); void card.offsetWidth; card.classList.add("flash");
}
window.jumpTo = jumpTo;

// ---------- list render ----------
const RISK_ORDER = {"상":0,"중":1,"하":2,"없음":3};
function match(d){
  if(F.ev.size && !F.ev.has(d.evaluator)) return false;
  if(F.pref.size && !F.pref.has(d.pref)) return false;
  if(F.risk.size && !F.risk.has(d.risk)) return false;
  if(F.score.size && !F.score.has(String(d.score!=null?Math.trunc(d.score):""))) return false;
  if(F.text){
    const hay=(d.question+d.respC+d.respD+d.good+d.bad+d.suggest+d.etc).toLowerCase();
    if(!hay.includes(F.text)) return false;
  }
  return true;
}
function fbItem(k,v){ return v?`<div class="item"><div class="k">${k}</div><div class="v">${esc(v)}</div></div>`:""; }
function card(d){
  const win = d.pref==="D"?"D":d.pref==="C"?"C":"";
  return `<div class="card" data-id="${d.id}">
    <div class="card-head">
      <span class="q">#${d.id}. ${esc(d.question)}</span>
      <span class="badge b-ev">${esc(d.evaluator)}</span>
      <span class="badge b-pref ${d.pref}">${esc(PREF_LABEL[d.pref]||d.prefRaw||"-")}</span>
      <span class="badge b-score">${d.score!=null?d.score+"점":"-"}</span>
      <span class="badge b-risk-${d.risk}">${esc(RISK_LABEL[d.risk])}</span>
    </div>
    <div class="card-body">
      <div class="resps">
        <div class="resp ${win==="C"?"win C":""}"><h4>챗봇 C 응답</h4><div class="txt">${esc(d.respC)}</div></div>
        <div class="resp ${win==="D"?"win D":""}"><h4>챗봇 D 응답</h4><div class="txt">${esc(d.respD)}</div></div>
      </div>
      <div class="fb">
        ${fbItem("선택 근거(원문)", d.prefRaw)}
        ${fbItem("좋았던 점", d.good)}
        ${fbItem("아쉬운 점", d.bad)}
        ${fbItem("보완·제안", d.suggest)}
        ${fbItem("위험도(원문)", d.riskRaw)}
        ${fbItem("기타 의견", d.etc)}
      </div>
    </div>
  </div>`;
}
function render(){
  let rows = DATA.filter(match);
  rows.sort((a,b)=>(RISK_ORDER[a.risk]-RISK_ORDER[b.risk]) || (a.id-b.id));
  document.getElementById("count").textContent =
    `${rows.length} / ${DATA.length}건 표시  ·  상위험 ${rows.filter(r=>r.risk==="상").length} · 중 ${rows.filter(r=>r.risk==="중").length}`;
  const list=document.getElementById("list");
  if(!rows.length){list.innerHTML=`<div class="empty">조건에 맞는 응답이 없습니다.</div>`;return;}
  list.innerHTML = rows.map(card).join("");
  list.querySelectorAll(".card-head").forEach(h=>h.addEventListener("click",()=>{
    h.parentElement.classList.toggle("open");
  }));
  if(expanded) list.querySelectorAll(".card").forEach(c=>c.classList.add("open"));
}
render();
</script>
</body>
</html>
"""


def verify_categories(data):
    """범주 ids 합계가 각 그룹 모수와 일치하고 분류가 실제 데이터와 맞는지 검증."""
    by_id = {d["id"]: d for d in data}
    expect = {
        "상": {d["id"] for d in data if d["risk"] == "상"},
        "중": {d["id"] for d in data if d["risk"] == "중"},
        "저점": {d["id"] for d in data if d["score"] in (1.0, 2.0)},
    }
    for key, group in CATEGORIES.items():
        ids = [i for c in group["cats"] for i in c["ids"]]
        if len(ids) != len(set(ids)):
            dup = [i for i in ids if ids.count(i) > 1]
            raise SystemExit(f"[{key}] 중복 배정 id: {sorted(set(dup))}")
        s = set(ids)
        missing = expect[key] - s
        extra = s - expect[key]
        if missing or extra:
            raise SystemExit(f"[{key}] 모수 불일치 missing={sorted(missing)} extra={sorted(extra)}")
        for i in ids:
            if i not in by_id:
                raise SystemExit(f"[{key}] 존재하지 않는 id {i}")
    print("범주 검증 통과 — 상/중/저점 모수·중복 일치")


def main():
    data = load()
    verify_categories(data)
    st = stats(data)
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_HTML.write_text(render(data, st), encoding="utf-8")
    print(f"응답 {st['n']}건 → {OUT_HTML}")
    print(f"선호: D={dict(st['pref']).get('D')} C={dict(st['pref']).get('C')} 둘다부적절={dict(st['pref']).get('둘다부적절')}")
    print(f"위험: {st['risk']}  평균점={st['score_avg']}")


if __name__ == "__main__":
    main()
