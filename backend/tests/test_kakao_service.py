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


from app.services.kakao_service import to_quick_replies, build_callback_payload, fallback_payload


def test_quick_replies_cap_10():
    qr = to_quick_replies([f"질문{i}" for i in range(15)])
    assert len(qr) == 10
    assert qr[0] == {"label": "질문0", "action": "message", "messageText": "질문0"}


def test_quick_replies_empty():
    assert to_quick_replies(None) == []
    assert to_quick_replies([]) == []


def test_build_payload_structure():
    payload = build_callback_payload("안녕", ["다시 질문"])
    assert payload["version"] == "2.0"
    assert payload["template"]["outputs"][0]["simpleText"]["text"] == "안녕"
    assert payload["template"]["quickReplies"][0]["messageText"] == "다시 질문"


def test_build_payload_no_quick_replies_key_when_empty():
    payload = build_callback_payload("안녕", [])
    assert "quickReplies" not in payload["template"]


def test_fallback_payload():
    p = fallback_payload()
    assert p["version"] == "2.0"
    assert p["template"]["outputs"][0]["simpleText"]["text"]


def test_blocks_non_http_scheme():
    assert is_allowed_callback_host("ftp://kakao.com/cb", [".kakao.com"]) is False
    assert is_allowed_callback_host("//kakao.com/cb", [".kakao.com"]) is False


def test_quick_reply_label_truncation():
    long_q = "가" * 15  # KAKAO_QUICK_REPLY_LABEL_LIMIT(14) 초과
    qr = to_quick_replies([long_q])
    assert len(qr[0]["label"]) == 14
    assert qr[0]["label"].endswith("…")
    assert qr[0]["messageText"] == long_q  # 전체 텍스트 보존


def test_quick_replies_skips_blank_items():
    qr = to_quick_replies([None, "", "질문"])
    assert len(qr) == 1
    assert qr[0]["messageText"] == "질문"
