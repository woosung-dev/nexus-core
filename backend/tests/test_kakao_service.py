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
