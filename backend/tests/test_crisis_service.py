# 위기 신호 감지·전화번호 문장 필터·검수 문구 순수성 — crisis_service 단위 검증
import pytest

from app.services.crisis_service import (
    BLOCKED_FALLBACK_MESSAGE,
    CRISIS_DIRECTIVE,
    detect_crisis_signal,
    strip_phone_sentences,
)

# --- detect_crisis_signal ---


@pytest.mark.parametrize(
    "message",
    [
        "요즘 죽고 싶다는 생각이 들어",  # 자살
        "그냥 다 살기 싫어요",
        "남편한테 맞았어요",  # 폭력
        "아이를 학대하는 것 같아 무서워요",
        "성폭행을 당했어요",  # 성폭력
        "교회 오빠가 자꾸 성희롱을 해요",
    ],
)
def test_detect_crisis_positive(message):
    assert detect_crisis_signal(message) is not None


@pytest.mark.parametrize(
    "message",
    [
        "점심 메뉴 추천해줘",
        "출석 3개월 기준이 뭐야?",
        "3일 행사 식순 알려줘",
        "축복 반지는 어디서 구입해?",
    ],
)
def test_detect_crisis_negative(message):
    assert detect_crisis_signal(message) is None


def test_detect_returns_matched_keyword():
    # 반환값은 로깅용 매칭 키워드
    assert detect_crisis_signal("요즘 죽고싶다") == "죽고싶"


# --- strip_phone_sentences ---


def test_strip_full_phone_number_sentence():
    text = "도움이 필요하시군요. 급하면 010-1234-5678로 연락 주세요. 힘내세요."
    filtered, removed = strip_phone_sentences(text)

    assert "010" not in filtered
    assert removed == ["급하면 010-1234-5678로 연락 주세요."]
    assert "도움이 필요하시군요." in filtered
    assert "힘내세요." in filtered


def test_strip_short_code_with_context():
    # 한글 조사가 붙은 단축번호("1366으로")도 제거
    text = "여성긴급전화 1366으로 연락하시면 도움을 받을 수 있어요.\n언제든 다시 이야기해 주세요."
    filtered, removed = strip_phone_sentences(text)

    assert "1366" not in filtered
    assert len(removed) == 1
    assert filtered.strip().endswith("언제든 다시 이야기해 주세요.")


def test_strip_emergency_short_code():
    text = "지금 위험하다면 112에 신고하세요."
    filtered, removed = strip_phone_sentences(text)

    assert "112" not in filtered
    assert len(removed) == 1


def test_preserves_normal_numbers():
    # 기간·연도·역사 연도는 상담 문맥어가 없으면 그대로
    text = "출석은 3개월 기준이에요. 2026년 3월 행사에서 만나요. 1392년 역사 이야기도 있죠."
    filtered, removed = strip_phone_sentences(text)

    assert removed == []
    assert filtered == text


def test_preserves_year_even_with_consult_context():
    # 연도 19xx/20xx 는 전화 문맥어가 있어도 단축번호로 오인하지 않음
    text = "1992년부터 상담 부서가 있었고, 2026년에도 상담 일정이 잡혀 있어요."
    filtered, removed = strip_phone_sentences(text)

    assert removed == []
    assert filtered == text


def test_short_code_without_context_kept():
    # 전화 문맥어 없는 단축번호 형태 숫자는 보존 (예: 식구 수 통계)
    text = "참석 인원은 136명이었습니다."
    filtered, removed = strip_phone_sentences(text)

    assert removed == []
    assert filtered == text


# --- 검수 문구 순수성 ---


def test_directive_and_fallback_have_no_phone_numbers():
    # 사용자 확정: 어떤 경로에서도 구체 번호 제시 금지 — 검수 문구 자체부터 보장
    for text in (CRISIS_DIRECTIVE, BLOCKED_FALLBACK_MESSAGE):
        _, removed = strip_phone_sentences(text)
        assert removed == []


def test_directive_mentions_confirmation_and_no_contact_rule():
    # 4원칙 핵심: 확인 단계 + 번호·기관명 금지 지시가 들어 있는지
    assert "확인" in CRISIS_DIRECTIVE
    assert "전화번호·기관명" in CRISIS_DIRECTIVE
