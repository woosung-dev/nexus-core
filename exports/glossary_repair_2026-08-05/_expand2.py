# 선행 `_expand.py` 를 그대로 쓰되 **용어집 파일과 문항 파일만 갈아끼운다.**
#
# 매칭 규칙(STOP·CONFLICT·MIN_LEN·MAX_TERMS·최장일치·조문 전개·확장쿼리 조립)은 한 줄도
# 복사하지 않는다. 복사하면 두 판이 갈라지고, 그 순간 선행 세션 결과와 비교가 깨진다.
# `_expand.py` 는 모듈 로드 시 선행 디렉터리 파일로 TERMS/SURFACES 를 만들어 두므로
# 여기서 그 전역만 다시 세운다.
#
# 단독 실행하면 v1 ↔ v2 를 같은 문항으로 돌려 차이를 찍는다(수리 검증 4번).
import json
import sys
import unicodedata
from pathlib import Path

DIR = Path(__file__).parent
STEER = DIR.parent / "glossary_steering_2026-08-04"
ABLAT = DIR.parent / "branch_ablation_2026-08-04"
sys.path.insert(0, str(STEER))

import _expand as E  # noqa: E402

V1 = ABLAT / "_glossary_terms.json"
V2 = DIR / "_glossary_terms_v2.json"


def use_glossary(path):
    """_expand 의 용어집 전역을 갈아끼운다. 반환: 용어 수."""
    terms = json.loads(Path(path).read_text(encoding="utf-8"))["terms"]
    E.TERMS = terms
    E.BY_TERM = {unicodedata.normalize("NFC", t["term"]): t for t in terms}
    E.BY_ALIAS = {}
    for t in terms:
        for a in (t.get("aliases") or []):
            E.BY_ALIAS[unicodedata.normalize("NFC", a)] = t
    E.SURFACES = E._surfaces()
    return len(terms)


def load_questions(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))["items"]


def expand_one(q):
    """(용어명들, 조문토큰들, 확장쿼리, 확장했는가)"""
    hits = E.lexical_match(q)
    eq, expanded, arts = E.build_query(q, hits)
    return [h["term"] for h in hits], arts, eq, expanded


def snapshot(items):
    return {it["qid"]: expand_one(it["q"])[:2] for it in items}


if __name__ == "__main__":
    qpath = sys.argv[1] if len(sys.argv) > 1 else str(ABLAT / "questions.json")
    items = load_questions(qpath)
    print(f"문항 {len(items)}건 ({Path(qpath).name})\n")

    n1 = use_glossary(V1)
    s1 = snapshot(items)
    n2 = use_glossary(V2)
    s2 = snapshot(items)
    print(f"용어집 v1 {n1}개 · v2 {n2}개\n")

    diffs = [q for q in s1 if s1[q] != s2[q]]
    print(f"v1 → v2 확장 결과가 바뀐 문항: {diffs or '없음'}")
    for q in diffs:
        print(f"  {q}")
        print(f"    용어  {s1[q][0]}\n       → {s2[q][0]}")
        print(f"    조문  {s1[q][1]}\n       → {s2[q][1]}")

    # v2 기준 표 — 선행 세션 재현 확인용
    print("\nv2 기준 M1 매칭")
    zero = []
    for it in items:
        terms, arts, eq, expanded = expand_one(it["q"])
        if not terms:
            zero.append(it["qid"])
        print(f"  {it['qid']:<8} {len(terms)}건 {terms}")
        print(f"           조문 {arts}")
    print(f"\n매칭 0건(= P 팔과 동일한 쿼리): {sorted(zero)}")

    if Path(qpath).name == "questions.json":
        ok = set(zero) == {"A-93", "B-114", "R-219"}
        print(f"선행 재현 (A-93·B-114·R-219 = 0건): {'일치' if ok else '불일치 ⚠'}")
