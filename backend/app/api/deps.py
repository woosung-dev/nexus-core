"""
FastAPI 공통 Dependencies.
JWKS(JSON Web Key Set) 기반으로 JWT를 검증합니다.
인증 플랫폼(Clerk, Auth0 등)에 독립적인 구조입니다.
"""

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import get_settings
from app.core.database import get_session
from app.crud import crud_user
from app.models.user import User

settings = get_settings()
security = HTTPBearer()

# JWKS 클라이언트: 인증 서버의 공개키를 자동으로 가져와 캐싱합니다.
# 플랫폼 교체 시 AUTH_JWKS_URL 환경변수만 변경하면 됩니다.
jwks_client = PyJWKClient(settings.AUTH_JWKS_URL, cache_keys=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    JWKS 방식으로 JWT를 검증하고, DB에서 해당 사용자를 조회합니다.
    DB에 사용자가 없다면 자동으로 생성합니다 (JIT Provisioning).

    - Clerk, Auth0 등 표준 JWKS 엔드포인트를 가진 모든 플랫폼에서 작동합니다.
    - 시크릿 키를 Backend에 저장하지 않아 보안성이 높습니다.

    Args:
        credentials: Authorization 헤더의 Bearer 토큰
        session: 비동기 DB 세션

    Returns:
        User: 인증된 사용자 모델 인스턴스

    Raises:
        HTTPException 401: 토큰이 유효하지 않은 경우
        HTTPException 403: 비활성화된 사용자인 경우
    """
    token = credentials.credentials

    try:
        # JWKS에서 이 토큰에 맞는 공개키를 자동으로 찾아 검증
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256", "HS256"],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 만료되었습니다. 다시 로그인해 주세요.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 토큰입니다.",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 서버와의 통신에 실패했습니다.",
        )

    # JWT payload에서 사용자 정보 추출
    clerk_user_id: str | None = payload.get("sub")
    email: str | None = payload.get("email")

    if not clerk_user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰에 필수 사용자 정보가 없습니다.",
        )

    # JIT Provisioning: clerk_user_id로 사용자 조회, 없으면 자동 생성
    provider = payload.get("provider", "unknown")
    avatar_url = payload.get("avatar_url")

    user = await crud_user.get_or_create_by_clerk_id(
        session=session,
        clerk_user_id=clerk_user_id,
        email=email,
        provider=provider,
        avatar_url=avatar_url,
    )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다. 관리자에게 문의해 주세요.",
        )

    return user
