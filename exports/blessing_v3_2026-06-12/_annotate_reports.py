# 블레싱 가·나 리포트 HTML 문제문항에 "진단·해결" 배너 주입 (원본 보존, 주석본 별도 저장)
import html
import json
import re
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
DL = Path("/Users/woosung/Downloads")
V3 = ROOT / "exports/blessing_v3_2026-06-12"
RECS = json.load(open(ROOT / "exports/_redteam_v2_data.json"))["records"]

# user -> [(qid, question)] (리포트와 동일 순서/번호)
BYUSER = {}
for r in RECS:
    BYUSER.setdefault(r["user"], [])
for u in BYUSER:
    rs = [r for r in RECS if r["user"] == u]
    BYUSER[u] = [(f"{u}-{i:02d}", (r["q"] or "").strip()) for i, r in enumerate(rs, 1)]


def qid_for(user, substr):
    for qid, q in BYUSER.get(user, []):
        if substr in q:
            return qid
    return None


# 트랙 메타: emoji, 라벨, 색클래스
TRACKS = {
    "raggap":  ("🟥", "RAG 신규문서 필요", "raggap"),
    "ragsurf": ("🟧", "RAG 미surfacing(있는데 못 꺼냄)", "ragsurf"),
    "prompt":  ("🟪", "프롬프트", "prompt"),
    "safety":  ("🟦", "세이프티(코드)", "safety"),
    "solved":  ("🟩", "v3에서 해소됨", "solved"),
}

# 정밀 매핑 (substring, user, track, problem, fix). 데스벨리는 성염보다 먼저.
PRECISE = [
    ("데스벨리 성염", "미야자키시호", "solved",
     "RAG에 2024-019호(데스벨리 성염·개인 불가) 문서는 있었으나, 가 원본은 '생물학적 정보=범위 밖'으로 거부(미surfacing)",
     "v3 성물 거부금지 프롬프트 패치로 해결 — 원본 거부(codex 1점)→v3 정답(양쪽 best 5). RAG 공백 아님"),
    ("성염의 번식 방법", "미야자키시호", "solved",
     "RAG에 규정집 4대성물(성염 증식) 문서는 있었으나, 가 원본은 '서비스 범위 밖'으로 거부(미surfacing)",
     "v3 성물 거부금지 프롬프트 패치로 해결 — 원본 거부(codex 모두부적절)→v3 정답(양쪽 best 5). RAG 공백 아님"),
    ("1세 상대자의 부모님도 축복", "조화연", "ragsurf",
     "1세 상대자 부모의 기성축복 요건이 2025-259호에 '전도기준+기성축복식'으로 있는데 봇이 '필수 아님'으로 오답",
     "프롬프트 앵커(현행 정본 명시) + 해당 공문을 표→서술형으로 풀어 재업로드"),
    ("2세가정 편성을 꼭 해야", "조화연", "prompt",
     "공감 부족 + 미적용 개념(천일국매칭) 언급, '2세가정 편성만 중요' 인상",
     "프롬프트: 부모 공감 우선 + 미적용 개념 억제(v3 일부 개선)"),
    ("1세청년에게 2세 축복자녀를 소개", "조화연", "ragsurf",
     "축복자녀 2세-1세 연령(만25세, 2025-259호)을 못 surfacing + 은사축복(탈선 함의) 부적절 언급",
     "프롬프트 앵커(만25세 명시) + 은사 직행 금지 규칙"),
    ("탈선까지는 아니었지만 성적인 접촉", "조화연", "safety",
     "Gemini 기본 세이프티 필터가 정상적인 부모 상담을 차단(응답 없음)",
     "코드 safety_settings 추가(BLOCK_ONLY_HIGH) — 확인 후. 프롬프트로는 불가"),
    ("약혼 이후 상대가 아닌 다른 이성과 부적절한 관계", "조화연", "prompt",
     "'부적절한 관계'에 선(先)확인(탈선/중도/경도) 없이 은사 절차로 직행",
     "프롬프트: 성문제 선확인 하드룰(v3 패치 대상)"),
]

# 자동분류 키워드(우선순위: safety > raggap > ragsurf > prompt)
KW = {
    "safety":  ["차단", "답변을 주지 못", "응답 없", "응답이 나오지", "세이프티", "과차단", "과도한 세이프"],
    "raggap":  ["rag에", "rag 보강", "추가되어야", "추가가 필요", "문서가 없", "자료실", "구매처",
                "지원금", "familyfed", "공식 채널", "공식 홈페이지", "넣었으면", "넣어주", "보강이 필요", "보강 요청"],
    "ragsurf": ["공문", "2025-259호", "259호", "표로 압축", "압축돼"],
    "prompt":  ["2세-1세", "은사", "분류", "선확인", "선상황", "기성가정", "공감", "단정", "민감", "출처"],
}


def classify(issues_text):
    t = issues_text.lower()
    for track in ["safety", "raggap", "ragsurf", "prompt"]:
        if any(k.lower() in t for k in KW[track]):
            return track
    return "prompt"


def load_v3_eval(bot):
    # agent
    araw = json.load(open(V3 / f"agent_eval_{bot}_v3.json"))
    agent = {e["user"]: {r["qid"]: r for r in e["eval"]["results"]} for e in araw}
    users = list(agent.keys())
    codex = {}
    for u in users:
        codex[u] = {r["qid"]: r for r in json.load(open(V3 / f"codex_{bot}_{u}_v3.json"))["results"]}
    return agent, codex, users


def build_diag_map(bot, users):
    agent, codex, _ = load_v3_eval(bot)
    diag = {}
    # 1) 자동분류: v3에서 best!=블레싱 또는 vs=lose (둘 중 하나라도)
    for u in users:
        for qid in agent.get(u, {}):
            ae = agent[u].get(qid, {})
            ce = codex[u].get(qid, {})
            problem = (ae.get("best") != "블레싱" and ae.get("best")) and \
                      (ce.get("best") != "블레싱") or \
                      ae.get("blessing_vs_tester") == "lose" or ce.get("blessing_vs_tester") == "lose"
            # best가 둘 다 블레싱이 아니거나, 어느 한쪽이라도 lose면 문제로
            both_not_best = ae.get("best") != "블레싱" and ce.get("best") != "블레싱"
            any_lose = ae.get("blessing_vs_tester") == "lose" or ce.get("blessing_vs_tester") == "lose"
            if not (both_not_best or any_lose):
                continue
            # 트랙 분류는 '블레싱 이슈' 텍스트만 사용(코멘트엔 A/B/C 무응답 등이 섞여 오분류 유발)
            issues = " ".join((ae.get("blessing_issues") or []) + (ce.get("blessing_issues") or []))
            track = classify(issues)
            # 짧은 문제 요약: 첫 이슈 또는 comment 앞부분
            first_issue = (ae.get("blessing_issues") or ce.get("blessing_issues") or [""])[0]
            diag[qid] = {"track": track, "problem": first_issue[:90] or "블레싱이 최우수가 아니거나 기존 선택에 밀림",
                         "fix": TRACKS[track][1], "auto": True}
    # 2) 정밀 매핑 override
    for substr, user, track, problem, fix in PRECISE:
        if user not in users:
            continue
        qid = qid_for(user, substr)
        if qid:
            diag[qid] = {"track": track, "problem": problem, "fix": fix, "auto": False}
    return diag


CSS = """
.diag{margin:8px 0 4px;padding:9px 12px;border-radius:9px;font-size:12.5px;line-height:1.5;border:1px solid;}
.diag b{font-weight:800;}
.diag-raggap{background:#FEF2F2;border-color:#FECACA;color:#991B1B;}
.diag-ragsurf{background:#FFF7ED;border-color:#FED7AA;color:#9A3412;}
.diag-prompt{background:#FAF5FF;border-color:#E9D5FF;color:#6B21A8;}
.diag-safety{background:#EFF6FF;border-color:#BFDBFE;color:#1E40AF;}
.diag-solved{background:#F0FDF4;border-color:#BBF7D0;color:#166534;}
.diag-auto{opacity:.92;}
.dleg{margin:12px 0;padding:12px 16px;background:#fff;border:1px solid #E5E9F0;border-radius:12px;font-size:12.5px;display:flex;gap:14px;flex-wrap:wrap;align-items:center;}
.dleg b{font-weight:800;margin-right:4px;}
.dleg .lg{padding:2px 8px;border-radius:999px;font-weight:700;}
"""

LEGEND = ('<div class="dleg"><b>🔧 진단 범례</b>'
          '<span class="lg diag-raggap">🟥 RAG 신규문서</span>'
          '<span class="lg diag-ragsurf">🟧 RAG 미surfacing</span>'
          '<span class="lg diag-prompt">🟪 프롬프트</span>'
          '<span class="lg diag-safety">🟦 세이프티(코드)</span>'
          '<span class="lg diag-solved">🟩 이미 해소</span>'
          '<span style="color:#5A6678">· 문제문항에만 표시 · "(자동)"=이슈텍스트 자동분류</span></div>')


def annotate(report_path, out_path, diag):
    src = report_path.read_text(encoding="utf-8")
    # CSS 삽입
    src = src.replace("</style>", CSS + "</style>", 1)
    # 범례 삽입 (deltabar 뒤 또는 첫 <h2> 앞)
    if '<div class="deltabar">' in src:
        src = re.sub(r'(<div class="deltabar">.*?</div>)', r"\1" + LEGEND, src, count=1, flags=re.S)
    else:
        src = src.replace("<h2>", LEGEND + "<h2>", 1)

    # details 블록별 주입
    parts = src.split('<details class="q"')
    matched = []
    for i in range(1, len(parts)):
        seg = parts[i]
        m = re.search(r'<span class="qid">([^<]+)</span>', seg)
        if not m:
            continue
        qid = m.group(1).strip()
        d = diag.get(qid)
        if not d:
            continue
        emoji, label, cls = TRACKS[d["track"]]
        auto = ' diag-auto' if d.get("auto") else ''
        suffix = ' <span style="opacity:.7">(자동)</span>' if d.get("auto") else ''
        banner = (f'<div class="diag diag-{cls}{auto}">🔧 <b>진단:</b> {emoji} {label}{suffix}'
                  f' · <b>문제:</b> {html.escape(d["problem"])} · <b>해결:</b> {html.escape(d["fix"])}</div>')
        # 해당 블록의 첫 <div class="qbody"> 뒤에 삽입
        seg2, n = re.subn(r'(<div class="qbody">)', r"\1" + banner, seg, count=1)
        if n:
            parts[i] = seg2
            matched.append(qid)
    out = '<details class="q"'.join(parts)
    out_path.write_text(out, encoding="utf-8")
    return matched


JOBS = [
    ("나", DL / "블레싱_나_v1v2v3_vs_ABC_2026-06-12.html", DL / "블레싱_나_v1v2v3_진단주석_2026-06-12.html"),
    ("가", DL / "블레싱_가_원본v3_vs_ABC_2026-06-12.html", DL / "블레싱_가_원본v3_진단주석_2026-06-12.html"),
]
for bot, src, out in JOBS:
    _, _, users = load_v3_eval(bot)
    diag = build_diag_map(bot, users)
    matched = annotate(src, out, diag)
    auto = sum(1 for q in matched if diag[q].get("auto"))
    precise = len(matched) - auto
    by_track = {}
    for q in matched:
        by_track[diag[q]["track"]] = by_track.get(diag[q]["track"], 0) + 1
    print(f"[{bot}] 주석 {len(matched)}문항 (정밀 {precise}, 자동 {auto}) · 트랙별 {by_track}")
    print(f"     → {out}")
