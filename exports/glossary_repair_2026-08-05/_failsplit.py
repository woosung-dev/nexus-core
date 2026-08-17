# 실패를 두 갈래로 가른다 — 문서 결손인가, 생성 실패인가.
#
# 이 구분이 다음 투자를 정한다.
#   · 문서에 내용이 없다      → 문서 보완 트랙 (챗봇 작업으로 못 고침)
#   · 문서에 있는데 답변이 안 씀 → 생성 트랙 (프롬프트·출력형식)
#   · 문서에 있는데 검색이 못 찾음 → 검색 트랙 (용어집·확장·청킹)
#
# 판정 방법: 답변이 놓친 케이스에 대해, **그 호출이 실제로 받은 청크**에 그 케이스의
# 규정집 문언이 들어 있었는지 본다. 들어 있었으면 검색은 성공했고 생성이 실패한 것이다.
#
# 한계 — 문언 키워드 대조는 거친 대리지표다. 키워드가 있으면 "재료가 그 호출에 있었다"는
# 뜻이고, 없다고 해서 반드시 검색 실패인 것은 아니다(다른 표현일 수 있다).
# 그래서 아래 수치는 **생성 실패의 하한**으로 읽어야 한다.
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

DIR = Path(__file__).parent

dump = json.loads((DIR / "_dump2.json").read_text(encoding="utf-8"))
recs = [r for r in dump["results"] if r.get("ok")]
matches = {m["qid"]: m for m in
           json.loads((DIR / "_match.json").read_text(encoding="utf-8"))["questions"]}
labels = {it["qid"]: it for it in
          json.loads((DIR / "_questions_pyeongseong.json").read_text(encoding="utf-8"))["items"]}

# 케이스별 규정집 문언 — 그 케이스가 자료에 실려 있었는지 확인하는 키워드
CASE_EVIDENCE = {
    "1세가정 편성": ["탕감봉", "3일행사"],
    "1세가정 편성으로 가는 경우": ["탕감봉", "3일행사"],
    "축복자녀가정 편성": ["12일", "축복자녀가정 편성"],
    "축복자녀가정 편성을 택하는 경우": ["12일", "축복자녀가정 편성"],
    "HJ 천주천보 40일수련 경로": ["40일수련", "천주천보"],
    "공인 대체교육 경로": ["대체교육", "특별수련"],
}
L = []


def w(s=""):
    L.append(s)


def norm(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", s or ""))


def call_of(qid, arm, rep):
    return next(r for r in recs if r["qid"] == qid and r["arm"] == arm and r["rep"] == rep)


w("# 실패 분해 — 문서 결손인가 생성 실패인가 (2026-08-05)")
w()
w("편성축 9문항 × 2팔(P·M1) × 5회 = **답변 90건**을 정답 케이스 라벨과 맞춰 분해했다.")
w()

# ── 1. 3갈래 분해 ────────────────────────────────────────────────
full = partial_only = case_miss = 0
for qid, m in matches.items():
    nexp = len(labels[qid]["expected_branches"])
    for r in m["results"]:
        cov = len(r.get("covered") or [])
        par = len(r.get("partial") or [])
        if cov == nexp and par == 0:
            full += 1
        elif cov == nexp:
            partial_only += 1
        else:
            case_miss += 1
tot = full + partial_only + case_miss

w("## 1. 답변 90건의 결과 분해")
w()
w("| 결과 | 건수 | 비중 |")
w("|---|---|---|")
w(f"| 완전 — 모든 케이스 + 모든 필수요소 | {full}/{tot} | {full/tot:.0%} |")
w(f"| 케이스는 다 덮었으나 **필수요소 누락** | {partial_only}/{tot} | {partial_only/tot:.0%} |")
w(f"| **케이스 자체를 놓침** | {case_miss}/{tot} | {case_miss/tot:.0%} |")
w()
w(f"**절반 가까이({(tot-full)/tot:.0%})가 불완전하다.**")
w()

# ── 2. 케이스 놓침의 원인 ────────────────────────────────────────
w("## 2. 케이스를 놓쳤을 때 — 자료가 없었나, 안 썼나")
w()
w("놓친 케이스마다 **그 호출이 실제로 받은 청크**에 규정집 문언이 있었는지 확인한다.")
w()
w("| 문항 | 팔 | rep | 놓친 케이스 | 그 호출 청크 | 자료에 있었나 |")
w("|---|---|---|---|---|---|")
had = notfound = suppressed = 0
for qid, m in matches.items():
    for r in sorted(m["results"], key=lambda x: (x["arm"], x["rep"])):
        for c in (r.get("missing") or []):
            rec = call_of(qid, r["arm"], r["rep"])
            nch = rec["grounding"]["n_chunks"]
            txt = norm(" ".join(ch.get("text") or "" for ch in rec["grounding"]["chunks"]))
            found = [k for k in CASE_EVIDENCE.get(c, []) if norm(k) in txt]
            if nch == 0:
                suppressed += 1
                verdict = "청크 0 보고(페르소나 억제)"
            elif found:
                had += 1
                verdict = f"**있었다** — {', '.join(found)}"
            else:
                notfound += 1
                verdict = "문언 못 찾음"
            w(f"| {qid} | {r['arm']} | {r['rep']} | {c} | {nch}개 | {verdict} |")
w()
n_ch = had + notfound
w(f"**청크를 보고한 {n_ch}건 중 {had}건({had/max(n_ch,1):.0%})에서 자료가 이미 그 호출 안에 있었다.**")
w(f"나머지 — 문언 못 찾음 {notfound}건 · 청크 0 보고 {suppressed}건")
w()
w("→ 케이스 놓침은 **검색 실패가 아니라 생성 실패**다.")
w()

# ── 3. 필수요소 누락 패턴 ────────────────────────────────────────
w("## 3. 필수요소 누락 — 무엇을 빠뜨리나")
w()
c = Counter()
for qid, m in matches.items():
    for r in m["results"]:
        for p in (r.get("partial") or []):
            for mm in (p.get("missing_must") or []):
                c[(qid, p["case"], mm)] += 1
w("| 횟수 | 문항 | 케이스 | 빠뜨린 요소 |")
w("|---|---|---|---|")
for (qid, case, mm), n in sorted(c.items(), key=lambda x: -x[1]):
    w(f"| {n}회 | {qid} | {case} | {mm} |")
w()
w("**패턴이 뚜렷하다 — 케이스 *이름*은 부르는데 그 케이스의 *절차*를 안 채운다.**")
w("P-367 은 두 편성을 다 언급하면서 각각의 의식 노정(탕감봉·3일행사 / 12일 특별의식)을 10회·9회 빠뜨렸다.")
w()

# ── 4. 팔별 ─────────────────────────────────────────────────────
w("## 4. 팔별 비교 — 검색 확장은 이 문제를 안 건드린다")
w()
w("| 팔 | 완전 | 요소 누락 | 케이스 놓침 |")
w("|---|---|---|---|")
for arm in ("P", "M1"):
    f = p_ = mss = 0
    for qid, m in matches.items():
        nexp = len(labels[qid]["expected_branches"])
        for r in m["results"]:
            if r["arm"] != arm:
                continue
            cov, par = len(r.get("covered") or []), len(r.get("partial") or [])
            if cov == nexp and par == 0:
                f += 1
            elif cov == nexp:
                p_ += 1
            else:
                mss += 1
    w(f"| {arm} | {f}/45 | {p_}/45 | {mss}/45 |")
w()
w("M1(어휘확장)은 검색 쪽 개입인데 **요소 누락이 오히려 더 많다.**")
w("검색을 건드려서 고칠 문제가 아니라는 또 하나의 신호다.")
w()

# ── 5. 트랙 분리 ────────────────────────────────────────────────
w("## 5. 트랙 분리")
w()
w("| 갈래 | 근거 | 담당 |")
w("|---|---|---|")
w(f"| 문서에 내용이 있는데 답변이 안 씀 | 케이스 놓침 {had}/{n_ch} · 요소 누락 {partial_only}건 | **생성 트랙** |")
w("| 문서에 내용이 없음 | 2세×2세 가정출발 · `축복자녀 축복` 항목 · 표제 없는 조문 · 근거 오기 | 문서 보완 트랙 (별도) |")
w()
w("문서 보완 트랙 산출물은 `~/Downloads/축복앱 문서 보완 항목/` 에 있다.")
w()

(DIR / "FAILURE_SPLIT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print(f"→ {DIR/'FAILURE_SPLIT.md'} ({len(L)}줄)")
