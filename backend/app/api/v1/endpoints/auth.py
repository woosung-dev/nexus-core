# 하나로 SSO 로그인 엔드포인트 — 자격을 검증하고 세션 JWT 를 발급한다

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import NexusException
from app.core.hanaro import check_official
from app.core.security import create_access_token
from app.crud import crud_user
from app.schemas.auth import HanaroLoginRequest, LoginResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["인증"])

# 검증 실패 사유 → (HTTP 상태, 에러코드, 사용자에게 보일 메시지).
# 설정 문제와 자격증명 문제를 뭉개지 않는 것이 핵심 — 뭉치면 원인을 오진한다.
_FAILURE: dict[str, tuple[int, str, str]] = {
    "invalid_credentials": (
        status.HTTP_401_UNAUTHORIZED,
        "INVALID_CREDENTIALS",
        "아이디 또는 비밀번호가 올바르지 않습니다.",
    ),
    "rate_limited": (
        status.HTTP_429_TOO_MANY_REQUESTS,
        "RATE_LIMITED",
        "로그인 시도가 너무 많습니다. 약 5분 후 다시 시도해 주세요.",
    ),
    "server_config": (
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "AUTH_SERVER_CONFIG",
        "로그인 서버 설정에 문제가 있습니다. 관리자에게 문의해 주세요.",
    ),
    "upstream_key_rejected": (
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "AUTH_UPSTREAM_KEY_REJECTED",
        "로그인 서버 설정에 문제가 있습니다. 관리자에게 문의해 주세요.",
    ),
    "upstream_error": (
        status.HTTP_502_BAD_GATEWAY,
        "AUTH_UPSTREAM_ERROR",
        "인증 서버와 통신하지 못했습니다. 잠시 후 다시 시도해 주세요.",
    ),
}


@router.post("/hanaro/login", response_model=LoginResponse)
async def hanaro_login(
    body: HanaroLoginRequest,
    session: AsyncSession = Depends(get_session),
) -> LoginResponse:
    """하나로 SSO 계정을 검증하고 세션 JWT 를 발급한다.

    비밀번호는 검증에만 사용하고 저장·로깅하지 않는다(규격서 8장).
    하나로는 이름·이메일 등 개인정보를 반환하지 않으므로 email 은 저장하지 않는다.
    사용자 식별은 clerk_user_id("hanaro:{userid}") 로만 한다.
    """
    userid = body.userid.strip()
    result = await check_official(userid, body.password)

    if not result.ok:
        http_status, code, message = _FAILURE.get(
            result.reason or "upstream_error", _FAILURE["upstream_error"]
        )
        raise NexusException(error_code=code, message=message, status_code=http_status)

    user = await crud_user.get_or_create_by_clerk_id(
        session=session,
        clerk_user_id=f"hanaro:{userid}",
        provider="hanaro",
        is_official=result.is_official,
    )

    if not user.is_active:
        raise NexusException(
            error_code="USER_INACTIVE",
            message="비활성화된 계정입니다. 관리자에게 문의해 주세요.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    token, expires_in = create_access_token(
        subject=f"hanaro:{userid}",
        provider="hanaro",
        is_official=result.is_official,
    )
    logger.info("하나로 로그인 성공 user_id=%s is_official=%s", user.id, result.is_official)

    return LoginResponse(
        access_token=token, expires_in=expires_in, is_official=result.is_official
    )
