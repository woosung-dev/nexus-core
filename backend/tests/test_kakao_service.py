# kakao_service 순수함수 유닛 테스트
from app.services.kakao_service import is_allowed_callback_host

ALLOWED = [".kakao.com"]


def test_allows_kakao_subdomain():
    assert is_allowed_callback_host("https://bot-api.kakao.com/callback/xyz", ALLOWED) is True


def test_allows_apex_kakao():
    assert is_allowed_callback_host("https://kakao.com/cb", ALLOWED) is True


def test_blocks_other_hosts():
    assert is_allowed_callback_host("https://evil.example.com/x", ALLOWED) is False
    assert is_allowed_callback_host("http://169.254.169.254/latest/meta-data", ALLOWED) is False
    assert is_allowed_callback_host("https://kakao.com.evil.com/x", ALLOWED) is False
    assert is_allowed_callback_host("https://fakekakao.com/x", ALLOWED) is False
    assert is_allowed_callback_host("not a url", ALLOWED) is False


from app.services.kakao_service import to_simple_text_outputs


def test_short_text_single_bubble():
    assert to_simple_text_outputs("안녕하세요") == [{"simpleText": {"text": "안녕하세요"}}]


def test_blank_text_fallbacks():
    out = to_simple_text_outputs("   ")
    assert out[0]["simpleText"]["text"] == "응답을 생성하지 못했습니다."


def test_long_text_splits_max_3_and_under_limit():
    long = "이것은 한 문장입니다. " * 400  # 약 4800자
    out = to_simple_text_outputs(long)
    assert 1 <= len(out) <= 3
    for o in out:
        assert len(o["simpleText"]["text"]) <= 1000


def test_unbreakable_overflow_truncates_last_with_ellipsis():
    out = to_simple_text_outputs("가" * 5000)  # 공백 없음 → 3청크, 마지막 …
    assert len(out) == 3
    assert out[-1]["simpleText"]["text"].endswith("…")
