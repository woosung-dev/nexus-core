# faqs_export.json 질문 + 문서전용 앵커(정답지 정규식 추출) + 코퍼스外 부정 질문으로 _questions.json 생성
import json
import re
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
FAQS = json.load(open(ROOT / "exports/faq_test/faqs_export.json", encoding="utf-8"))
OUT = ROOT / "exports/rag_citation_audit/_questions.json"

# 문서전용(베이스 모델이 모를) 고정밀 앵커 패턴 — L2 오라클용
ANCHOR_PATTERNS = [
    r"제?\s?\d{4}-\d+\s?호",            # 공문번호 2025-259호
    r"세가한본\s*제?\s?\d{4}-\d+\s?호",  # 공문 발신처
    r"\d{1,3}(?:,\d{3})+\s?원",          # 15,000원 / 3,000원
    r"만\s?\d{1,2}\s?세",                # 만 25세
    r"HJ효정천보",
    r"크리스티나\s?한|Kristina\s?Han",
    r"하나로\s*시스템",
    r"원리교육\s?\d회|참부모론\s?\d회",
    r"\d{1,2}일\s*(?:가정출발의식|수련|행사)",
    r"\d{1,2}개월\s*(?:전|이상)",
]
ANCHOR_RE = [re.compile(p) for p in ANCHOR_PATTERNS]


def mine_anchors(answer: str) -> list[str]:
    found = []
    for rx in ANCHOR_RE:
        for m in rx.findall(answer):
            s = (m if isinstance(m, str) else m[0]).strip()
            if s and s not in found:
                found.append(s)
    return found


questions = []
for f in FAQS:
    anchors = mine_anchors(f["answer"])
    questions.append({
        "qid": f"faq{f['id']}",
        "question": f["question"],
        "golden": f["answer"],
        "anchors": anchors,
        "expected_retrieval": True,
        "source": "faq",
    })

# 확인된 강한 문서전용 앵커 질문(파일럿에서 검증: 답에 "25" 등장)
questions.append({
    "qid": "anchor_age",
    "question": "축복자녀-1세 매칭확정자의 변경된 연령 기준은?",
    "golden": "축복자녀 남녀 모두 만 25세 이상(공문 세가한본 제2025-259호, 2025-11-19). 1세는 연령 불문.",
    "anchors": ["25", "2025-259"],
    "expected_retrieval": True,
    "source": "anchor",
})

# 코퍼스外 부정 질문 — 검색 없어야 정상, 환각인용/오검색 측정용
NEG = [
    ("neg_eiffel", "에펠탑의 높이는 몇 미터인가요?"),
    ("neg_python", "파이썬에서 리스트를 오름차순으로 정렬하는 함수는?"),
    ("neg_weather", "다음 주 서울의 날씨를 알려줘."),
    ("neg_bitcoin", "비트코인의 현재 시세는 얼마인가요?"),
]
for qid, q in NEG:
    questions.append({
        "qid": qid, "question": q, "golden": "",
        "anchors": [], "expected_retrieval": False, "source": "negative",
    })

OUT.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")
n_anchor = sum(1 for q in questions if q["anchors"])
print(f"질문 {len(questions)}개 → {OUT}")
print(f"  faq {sum(1 for q in questions if q['source']=='faq')} · anchor 1 · negative {len(NEG)}")
print(f"  앵커 보유 질문 {n_anchor}개")
print("\n앵커 예시:")
for q in questions:
    if q["anchors"]:
        print(f"  {q['qid']}: {q['anchors']}")
