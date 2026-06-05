"""
카카오톡 i 오픈빌더 스킬 콜백 스키마.
요청은 userRequest 안에 user/callbackUrl 이 들어온다(공식 페이로드 구조).
"""

from pydantic import BaseModel


# --- 요청 ---
class KakaoUser(BaseModel):
    id: str
    type: str | None = None
    properties: dict | None = None


class KakaoUserRequest(BaseModel):
    utterance: str
    user: KakaoUser
    callbackUrl: str | None = None
    lang: str | None = None
    timezone: str | None = None


class KakaoBot(BaseModel):
    id: str
    name: str | None = None


class KakaoCallbackRequest(BaseModel):
    userRequest: KakaoUserRequest
    bot: KakaoBot
    intent: dict | None = None
    action: dict | None = None


# --- 응답(스키마 문서화용; 핸들러/워커는 dict 를 직접 만든다) ---
class KakaoSimpleText(BaseModel):
    text: str


class KakaoOutput(BaseModel):
    simpleText: KakaoSimpleText


class KakaoQuickReply(BaseModel):
    label: str
    action: str = "message"
    messageText: str


class KakaoTemplate(BaseModel):
    outputs: list[KakaoOutput]
    quickReplies: list[KakaoQuickReply] | None = None


class KakaoCallbackResponse(BaseModel):
    version: str = "2.0"
    useCallback: bool | None = None
    template: KakaoTemplate | None = None
