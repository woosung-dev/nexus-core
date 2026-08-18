# 쿼리 확장 라이브러리 — API 호출 0. 팔 M1·M2 가 공유한다.
#
# 입력: 선행 세션 ETL 산출물 (읽기 전용)
#   ../branch_ablation_2026-08-04/_glossary_terms.json   행정용어 147개
#   ../branch_ablation_2026-08-04/questions.json         문항 10건
#
# 매칭 규칙은 핸드오프 §3 에서 확정된 것을 그대로 옮겼다. 단독 실행하면 10문항 M1 표를 찍는다.
# 재현 검증 기준: A-93 · B-114 · R-219 = 0건, 나머지 7건은 1~3건.
import json
import re
import unicodedata
from pathlib import Path

DIR = Path(__file__).parent
SRC = DIR.parent / "branch_ablation_2026-08-04"

# 핸드오프 §3 "어휘 매칭 규칙" — 변형 금지.
STOP = {"축복", "성별", "은사", "헌금", "후보자", "해원", "환불"}      # 거의 모든 질문에 걸리는 일반어
CONFLICT = {"교회", "확정자", "중도문제"}                              # 현장교회 / 축복식 확정자 / 경도문제
MIN_LEN = 3        # 2자 이하 표기 제외
MAX_TERMS = 6      # 매핑 결과 상한 (M1·M2 공통)


def nfkc(s):
    return unicodedata.normalize("NFKC", s or "").casefold()


def load_terms():
    d = json.loads((SRC / "_glossary_terms.json").read_text(encoding="utf-8"))
    return d["terms"]


def load_questions():
    return json.loads((SRC / "questions.json").read_text(encoding="utf-8"))["items"]


TERMS = load_terms()
BY_TERM = {unicodedata.normalize("NFC", t["term"]): t for t in TERMS}
# 별칭 → 정규명. M2 가 별칭으로 답해도 정규명으로 접는다.
BY_ALIAS = {}
for _t in TERMS:
    for _a in (_t.get("aliases") or []):
        BY_ALIAS[unicodedata.normalize("NFC", _a)] = _t


def canonical(name):
    """147개 안의 용어면 정규 term dict, 아니면 None. 별칭도 받는다."""
    k = unicodedata.normalize("NFC", (name or "").strip())
    return BY_TERM.get(k) or BY_ALIAS.get(k)


def _surfaces():
    """(정규화표기, term, 원표기) 최장 우선 정렬."""
    out = []
    for t in TERMS:
        for s in [t["term"]] + list(t.get("aliases") or []):
            s = s.strip()
            if len(s) < MIN_LEN or s in STOP or s in CONFLICT:
                continue
            out.append((nfkc(s), t, s))
    out.sort(key=lambda x: -len(x[0]))
    return out


SURFACES = _surfaces()


def lexical_match(q):
    """M1 — NFKC+casefold 부분문자열, 최장일치 우선. 이미 채택된 표기에 포함되는 짧은 표기는 흡수."""
    nq = nfkc(q)
    taken, hits = [], []
    for ns, t, sur in SURFACES:
        if ns not in nq:
            continue
        if any(ns in prev for prev in taken):
            continue
        taken.append(ns)
        hits.append({"term": t["term"], "no": t["no"], "surface": sur,
                     "articles": list(t["source_articles"]),
                     "definition": t["definition"]})
    return hits[:MAX_TERMS]


_RANGE = re.compile(r"^제(\d+)~(\d+)조$")
_SINGLE = re.compile(r"^제(\d+)조$")


def articles_for(hits):
    """조문 토큰 조립. 중복 제거.

    범위표기(`제39~43조`)는 핸드오프 §3 이 규정하지 않았다 — 원문과 전개형을 둘 다 넣는다.
    문서 본문은 `제42조` 처럼 개별 번호로 쓰여 있어 전개형이 없으면 유도가 약해진다.
    """
    ranges, nums, others = [], set(), []
    for h in hits:
        for a in h["articles"]:
            a = a.strip()
            if not a:
                continue
            m = _RANGE.match(a)
            if m:
                lo, hi = int(m.group(1)), int(m.group(2))
                if a not in ranges:
                    ranges.append(a)
                if lo <= hi and hi - lo <= 20:      # 비정상 범위 방어
                    nums.update(range(lo, hi + 1))
                continue
            m = _SINGLE.match(a)
            if m:
                nums.add(int(m.group(1)))
                continue
            if a not in others:                      # 예상 밖 표기는 원문 보존
                others.append(a)
    singles = [f"제{n}조" for n in sorted(nums)]
    return ranges + singles + others


def build_query(q, hits):
    """핸드오프 §3: 확장쿼리 = 원질문 + " " + 표준용어들 + " " + 조문번호들.

    매칭 0건이면 확장하지 않고 원 질문 그대로 (= P 팔과 동일).
    반환: (쿼리문자열, 확장했는가, 조문토큰들)
    """
    usable = [h for h in hits if h["articles"]]      # source_articles 빈 용어 제외 (실제 147/147 보유)
    if not usable:
        return q, False, []
    arts = articles_for(usable)
    terms = " ".join(h["term"] for h in usable)
    return f"{q} {terms} {' '.join(arts)}", True, arts


def vocab_prompt(mode):
    """M2 에 넣을 147개 닫힌어휘 목록. names=1,945자 · defs=11,233자.

    정의 원문에는 pdftotext 줄바꿈 흔적(단어 중간 공백)이 남아 있다. 표기 정규화는
    매칭에만 필요하고 여기서는 사람·모델 모두 읽을 수 있으므로 원문 그대로 넣는다.
    """
    lines = []
    for t in TERMS:
        al = "/".join(t.get("aliases") or [])
        head = f"{t['no']}. {t['term']}" + (f" (={al})" if al else "")
        lines.append(head if mode == "names" else f"{head} — {t['definition']}")
    return "\n".join(lines)


if __name__ == "__main__":
    qs = load_questions()
    print(f"용어 {len(TERMS)}개 · 매칭 표기 {len(SURFACES)}개 "
          f"(용어 {len({id(t) for _, t, _ in SURFACES})}개 커버)")
    print(f"어휘목록 길이 — names {len(vocab_prompt('names'))}자 · defs {len(vocab_prompt('defs'))}자\n")

    zero = []
    for it in qs:
        hits = lexical_match(it["q"])
        eq, expanded, arts = build_query(it["q"], hits)
        if not hits:
            zero.append(it["qid"])
        print(f"{it['qid']:<7} {len(hits)}건  {[h['term'] for h in hits]}")
        print(f"        조문 {arts}")
        print(f"        확장쿼리({'O' if expanded else 'X'}) {eq[:160]}")
    print(f"\n매칭 0건: {zero}")
    ok = set(zero) == {"A-93", "B-114", "R-219"}
    print(f"핸드오프 §2 재현 (A-93·B-114·R-219 = 0건): {'일치' if ok else '불일치 ⚠'}")
