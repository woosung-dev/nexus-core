"""
카카오톡 i Open Builder 콜백 스키마.
향후 구현을 위한 구조 정의만 포함.
"""

from pydantic import BaseModel


# --- 카카오 요청 구조 ---
class KakaoUserRequest(BaseModel):
    """카카오톡 사용자 발화 정보"""
    utterance: str
    lang: str | None = None
    timezone: str | None = None


class KakaoUser(BaseModel):
    """카카오톡 사용자 식별 정보"""
    id: str
    type: str | None = None
    properties: dict | None = None


class KakaoBot(BaseModel):
    """카카오톡 봇 정보"""
    id: str
    name: str | None = None


class KakaoCallbackRequest(BaseModel):
    """카카오톡 i Open Builder 콜백 요청 본문"""
    intent: dict | None = None
    userRequest: KakaoUserRequest
    user: KakaoUser
    bot: KakaoBot
    action: dict | None = None


# --- 카카오 응답 구조 ---
class KakaoSimpleText(BaseModel):
    """단순 텍스트 응답"""
    text: str


class KakaoOutput(BaseModel):
    """응답 출력 블록"""
    simpleText: KakaoSimpleText


class KakaoTemplate(BaseModel):
    """응답 템플릿"""
    outputs: list[KakaoOutput]


class KakaoCallbackResponse(BaseModel):
    """카카오톡 콜백 응답"""
    version: str = "2.0"
    template: KakaoTemplate
