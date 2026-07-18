"""
FastAPI 공통 Dependencies.
JWKS(JSON Web Key Set) 기반으로 JWT를 검증합니다.
인증 플랫폼(Clerk, Auth0 등)에 독립적인 구조입니다.
"""

import logging
import time
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

logger = logging.getLogger(__name__)

settings = get_settings()
security = HTTPBearer()

# JWKS 클라이언트: 인증 서버의 공개키를 자동으로 가져와 캐싱합니다.
# 플랫폼 교체 시 AUTH_JWKS_URL 환경변수만 변경하면 됩니다.
jwks_client = PyJWKClient(settings.AUTH_JWKS_URL, cache_keys=True)

# User TTL 캐시 — clerk_user_id별로 SELECT 결과를 짧게 메모이즈해 매 요청 ~400ms DB 호출을 제거.
# 30초 TTL이면 admin이 유저 deactivate 시 최악 30초간 stale 접근. 챗봇 워크로드에서는 수용 가능.
# 캐시는 process 로컬이므로 worker가 여러 개라면 worker별로 독립.
_user_cache: dict[str, tuple[User, float]] = {}
_USER_CACHE_TTL_SEC = 30.0


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
        # 캐시 hit이면 마이크로초, miss면 Clerk JWKS endpoint로 sync HTTP가 발생해 event loop를 막을 수 있어 측정.
        t_jwks = time.perf_counter()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        jwks_ms = (time.perf_counter() - t_jwks) * 1000
        if jwks_ms >= 5.0:
            logger.info("jwks lookup elapsed=%.1fms (cache miss likely)", jwks_ms)
        else:
            logger.debug("jwks lookup elapsed=%.1fms", jwks_ms)

        # iat 검증 비활성화 + leeway 유지:
        # - PyJWT 2.6+ 가 RFC 7519 보다 엄격하게 iat(미래값)을 거부하는데, 이게 Clerk 서버 시계가
        #   백엔드보다 살짝 앞설 때 ImmatureSignatureError 를 일으킴. RFC 는 iat 를 정보용으로
        #   정의하지 "이 시각 전엔 유효하지 않다" 라고 정의하지 않음 (그건 nbf 의 의미).
        # - exp 만료 검증 + 서명 검증은 그대로라 보안 변경 없음. Clerk Node.js SDK 의 기본 동작과 동일.
        # - leeway=10: 만약 Clerk 가 nbf 를 사용하기 시작하면 시계 차이 흡수.
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256", "HS256"],
            leeway=10,
            options={"verify_iat": False},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 만료되었습니다. 다시 로그인해 주세요.",
        )
    except jwt.InvalidTokenError as e:
        # InvalidTokenError 가 다시 발생하면 시계 skew 가 leeway 도 못 견딜 만큼 큰 것.
        # unverified decode 로 iat/nbf/exp 노출해 진단 가능하게 함.
        skew_info = ""
        try:
            unv = jwt.decode(token, options={"verify_signature": False})
            now = int(time.time())
            iat = unv.get("iat")
            nbf = unv.get("nbf")
            exp = unv.get("exp")
            skew_iat = (iat - now) if iat else None
            skew_info = f" iat={iat} nbf={nbf} exp={exp} now={now} skew_iat={skew_iat:+d}s" if skew_iat is not None else f" iat={iat} nbf={nbf} exp={exp} now={now}"
        except Exception:
            pass
        logger.info("JWT invalid: %s — %s%s", type(e).__name__, e, skew_info)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 토큰입니다.",
        )
    except Exception as e:
        logger.warning("JWT validation generic failure: %s — %s", type(e).__name__, e)
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
    # JWT 템플릿이 boolean을 문자열로 렌더링할 수 있음
    raw_official = payload.get('is_official')
    is_official = raw_official is True or (isinstance(raw_official, str) and raw_official.strip().lower() == 'true')

    t_user = time.perf_counter()
    now = time.monotonic()
    cached = _user_cache.get(clerk_user_id)
    if cached and now - cached[1] < _USER_CACHE_TTL_SEC:
        user = cached[0]
        user_ms = (time.perf_counter() - t_user) * 1000
        logger.debug("user cache hit elapsed=%.3fms", user_ms)
    else:
        user = await crud_user.get_or_create_by_clerk_id(
            session=session,
            clerk_user_id=clerk_user_id,
            email=email,
            provider=provider,
            avatar_url=avatar_url,
            is_official=is_official,
        )
        # session에서 detach해 캐시에 보관 — 후속 요청은 다른 session 컨텍스트라
        # 그대로 두면 DetachedInstanceError 가능. 읽기 전용 필드만 사용한다는 가정.
        session.expunge(user)
        _user_cache[clerk_user_id] = (user, now)
        user_ms = (time.perf_counter() - t_user) * 1000
        if user_ms >= 50.0:
            logger.info("user upsert elapsed=%.1fms (cache miss, cold DB)", user_ms)
        else:
            logger.debug("user upsert elapsed=%.1fms (cache miss)", user_ms)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다. 관리자에게 문의해 주세요.",
        )

    return user
