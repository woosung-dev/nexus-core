# 하나로 SSO 로그인 요청·응답 스키마

from pydantic import BaseModel, Field


class HanaroLoginRequest(BaseModel):
    """하나로 SSO 로그인 요청. 비밀번호는 검증에만 쓰고 저장하지 않는다."""

    userid: str = Field(..., min_length=1, max_length=100, description="하나로 SSO 아이디")
    password: str = Field(..., min_length=1, max_length=200, description="하나로 SSO 비밀번호")


class LoginResponse(BaseModel):
    """로그인 성공 응답. 토큰은 프론트에서 httpOnly 쿠키로 보관한다."""

    access_token: str = Field(..., description="세션 JWT (HS256)")
    token_type: str = Field(default="bearer", description="토큰 타입")
    expires_in: int = Field(..., description="만료까지 남은 초")
    is_official: bool = Field(..., description="공직자 여부")
