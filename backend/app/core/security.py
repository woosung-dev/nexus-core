# 로그인 성공 시 자체 세션 JWT(HS256)를 발급하는 유틸

from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings


def create_access_token(
    *, subject: str, email: str, provider: str, is_official: bool
) -> tuple[str, int]:
    """세션 JWT 를 발급하고 (토큰, 만료까지 남은 초)를 반환한다.

    deps.get_current_user 가 필수로 요구하는 sub·email 클레임을 반드시 포함한다.
    갱신(refresh) 토큰은 두지 않는다 — 재발급하려면 하나로 비밀번호가 다시 필요해
    의미가 없기 때문이다. 만료되면 재로그인한다.
    """
    settings = get_settings()
    if not settings.AUTH_JWT_SECRET:
        raise RuntimeError("AUTH_JWT_SECRET 미설정 — 세션 토큰을 발급할 수 없습니다.")

    expires_in = settings.AUTH_JWT_EXPIRE_HOURS * 3600
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "email": email,
        "provider": provider,
        "is_official": is_official,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(
        payload, settings.AUTH_JWT_SECRET.get_secret_value(), algorithm="HS256"
    )
    return token, expires_in
