# 실제 카카오 페이로드 구조 파싱 — 현 스키마(최상위 user 필수)는 여기서 실패한다.
from app.schemas.kakao import KakaoCallbackRequest


def test_parses_real_payload_shape():
    payload = {
        "userRequest": {
            "utterance": "안녕",
            "user": {"id": "abc123", "type": "botUserKey"},
            "callbackUrl": "https://bot-api.kakao.com/callback/xyz",
        },
        "bot": {"id": "bot-123", "name": "테스트봇"},
        "action": {"params": {}},
    }
    req = KakaoCallbackRequest.model_validate(payload)
    assert req.userRequest.user.id == "abc123"
    assert req.userRequest.callbackUrl.endswith("/xyz")
    assert req.bot.id == "bot-123"


def test_callback_url_optional():
    payload = {
        "userRequest": {"utterance": "안녕", "user": {"id": "u1"}},
        "bot": {"id": "b1"},
    }
    req = KakaoCallbackRequest.model_validate(payload)
    assert req.userRequest.callbackUrl is None
