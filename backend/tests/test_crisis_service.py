# 위기 신호 감지·전화번호 문장 필터·검수 문구 순수성 — crisis_service 단위 검증
import pytest

from app.services.crisis_service import (
    BLOCKED_FALLBACK_MESSAGE,
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


def test_strip_hallucinated_number():
    # 봇이 지어낸 미검증 번호 문장은 제거 (일본 사례: 오안내가 더 위험)
    text = "도움이 필요하면 1588-9999 상담센터로 전화하세요.\n언제든 다시 이야기해 주세요."
    filtered, removed = strip_phone_sentences(text)

    assert "1588" not in filtered
    assert len(removed) == 1
    assert filtered.strip().endswith("언제든 다시 이야기해 주세요.")


def test_preserves_verified_crisis_numbers():
    # 급성 위기 검증 핫라인(109·1577-0199·112·119)은 보존 (2026-06-12 사용자 결정)
    text = (
        "지금은 안전이 먼저예요. 자살예방 상담전화 109나 정신건강 위기상담 1577-0199로 연락해 주세요. "
        "위험이 임박하면 112·119로 도움을 요청하세요."
    )
    filtered, removed = strip_phone_sentences(text)

    assert removed == []
    assert "109" in filtered and "1577-0199" in filtered and "112" in filtered


def test_strips_unverified_keeps_verified_when_mixed():
    # 검증 번호와 환각 번호가 섞이면 환각 문장만 제거
    text = "자살예방 상담전화 109로 연락하세요. 그리고 02-1234-5678 사설 기관도 안내드려요."
    filtered, removed = strip_phone_sentences(text)

    assert "109" in filtered
    assert "02-1234-5678" not in filtered
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


# --- 검수 고정문 (차단 시 폴백) ---


def test_blocked_fallback_includes_verified_crisis_numbers():
    # 차단은 급성 위기 질문에서 잦으므로 검증 핫라인 포함 (2026-06-12 결정). strip 은 폴백에 미적용.
    assert "109" in BLOCKED_FALLBACK_MESSAGE
    assert "1577-0199" in BLOCKED_FALLBACK_MESSAGE
    # 검증 번호만 들어 있어 strip 통과 시 제거되지 않음
    _, removed = strip_phone_sentences(BLOCKED_FALLBACK_MESSAGE)
    assert removed == []
