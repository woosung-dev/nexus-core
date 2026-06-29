"""
레드팀 질문 정규화 및 유사도 매칭 헬퍼.
임포트 스크립트와 수동 매칭 후보 조회(API)에서 공통으로 사용한다.
"""

import re
from difflib import SequenceMatcher

# 5종 표준 카테고리와 키워드 휴리스틱 (3주차 자동분류 폴백용)
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "축복 준비 및 매칭": ("매칭", "교류", "약혼", "대상", "이성", "만남", "소개", "호감", "연애", "준비"),
    "가정출발": ("가정출발", "성생활", "신혼", "출발", "동거", "부부", "결혼생활", "책임분담", "임신", "자녀"),
    "축복정리": ("정리", "이혼", "별거", "재축복", "탕감", "파혼", "취소"),
    "축복유형": ("미혼", "1세", "2세", "축복자녀", "은사", "유형", "독신"),
    "탈선 등 성적 문제": ("탈선", "순결", "음란", "포르노", "자위", "동성", "성적", "유혹"),
}

CANONICAL_CATEGORIES = tuple(CATEGORY_KEYWORDS.keys())


def normalize_question(text: str | None) -> str:
    """질문 정규화 — 공백제거 + 소문자 + 한글/영숫자 외 제거"""
    s = str(text or "").strip().lower()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^\w가-힣]", "", s)
    return s


def similarity(a_norm: str, b_norm: str) -> float:
    """정규화된 두 질문의 유사도 (0.0~1.0). 정확일치=1.0"""
    if not a_norm or not b_norm:
        return 0.0
    if a_norm == b_norm:
        return 1.0
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def canonical_category(raw: str | None) -> str | None:
    """원본 유형 텍스트를 5종 표준 카테고리로 정규화 (1·2주차 유형 칸 → 표준)"""
    if not raw:
        return None
    t = str(raw)
    for cat in CANONICAL_CATEGORIES:
        if cat in t:
            return cat
    # 부분 키워드로 매핑 (유형 칸 표기 변형 대응)
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return cat
    return None


def classify_by_keywords(question: str | None) -> str | None:
    """질문 텍스트 키워드로 5종 카테고리 추정 (매칭 실패 시 None)"""
    if not question:
        return None
    t = str(question)
    best: tuple[str, int] | None = None
    for cat, keywords in CATEGORY_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in t)
        if hits and (best is None or hits > best[1]):
            best = (cat, hits)
    return best[0] if best else None
