# 하나로 SSO 공직자 판별 API v2 를 호출해 로그인 검증과 공직자 여부를 받는 클라이언트

import logging
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 규격서(공직자 판별 API v2, 2026-07-16) 2장 — 엔드포인트
DEFAULT_URL = "https://hanaro.ffwp.or.kr/API_kim/officialLoginCheck2"
TIMEOUT_SEC = 8.0


@dataclass(frozen=True)
class OfficialCheckResult:
    """하나로 검증 결과.

    reason 은 실패했을 때만 채워진다.
    - invalid_credentials  아이디/비밀번호 불일치 (사용자 잘못)
    - rate_limited         아이디당 실패 15회 누적 (규격서 5장)
    - server_config        우리 서버에 발급 키가 없음 (우리 잘못)
    - upstream_key_rejected 키를 보냈으나 하나로가 거부 (IT팀 확인 필요)
    - upstream_error       네트워크·응답 형식 오류
    """

    ok: bool
    is_official: bool = False
    reason: str | None = None


async def check_official(userid: str, password: str) -> OfficialCheckResult:
    """하나로 아이디·비밀번호를 검증하고 공직자 여부를 받는다.

    발급 키와 비밀번호는 어떤 경우에도 로깅하지 않는다(규격서 8장).
    """
    settings = get_settings()
    key = (
        settings.OFFICIAL_CHECK_KEY.get_secret_value()
        if settings.OFFICIAL_CHECK_KEY
        else None
    )
    url = settings.OFFICIAL_CHECK_URL or DEFAULT_URL

    if not key:
        logger.error("OFFICIAL_CHECK_KEY 미설정 — 하나로 API 를 호출하지 않는다")
        return OfficialCheckResult(ok=False, reason="server_config")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SEC) as client:
            resp = await client.post(
                url,
                data={"keyValue": key, "userid": userid, "password": password},
            )
    except Exception as e:
        logger.error("하나로 API 호출 실패: %s — %s", type(e).__name__, e)
        return OfficialCheckResult(ok=False, reason="upstream_error")

    # 규격서 5장 — 아이디당 실패 15회 누적 시 429. 마지막 실패로부터 5분 뒤 자동 해제.
    if resp.status_code == 429:
        return OfficialCheckResult(ok=False, reason="rate_limited")

    try:
        data = resp.json()
    except ValueError:
        logger.error("하나로 응답 JSON 파싱 실패 (status=%s)", resp.status_code)
        return OfficialCheckResult(ok=False, reason="upstream_error")

    error = data.get("error")
    if error == "rate_limited":
        return OfficialCheckResult(ok=False, reason="rate_limited")
    if error in ("invalid_key", "missing_parameter"):
        # 업스트림 에러코드만 남긴다 — 설정 오류를 진단할 유일한 단서다.
        # (v1 전용 키를 v2 주소에 쓰면 invalid_key 가 온다.)
        logger.error("하나로가 설정을 거절: %s (url=%s)", error, url)
        return OfficialCheckResult(ok=False, reason="upstream_key_rejected")

    # 규격서 4장 — isOfficial 은 authenticated 가 true 일 때만 유효하다.
    if data.get("authenticated") is True:
        return OfficialCheckResult(ok=True, is_official=data.get("isOfficial") is True)

    return OfficialCheckResult(ok=False, reason="invalid_credentials")
