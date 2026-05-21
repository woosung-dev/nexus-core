# 요청 단위 식별자(request_id)를 ContextVar로 보관해 다중 동시 요청에서 로그 그룹핑을 가능하게 함.
"""
미들웨어가 요청 시작 시 request_id를 set 하고, 로깅 Filter가 이를 LogRecord 속성으로 주입한다.
서비스 레이어 코드는 별도 인자 전달 없이 logger 호출만으로 자동으로 prefix가 붙는다.
"""

import logging
from contextvars import ContextVar

# 빈 문자열 default — 미들웨어 밖에서 호출되는 코드(앱 부트스트랩 등)의 로그도 깨지지 않도록.
_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def set_request_id(req_id: str) -> object:
    """요청 시작 시 호출. 반환값은 reset 용 토큰."""
    return _request_id.set(req_id)


def reset_request_id(token: object) -> None:
    """요청 종료 시 호출. set_request_id의 반환값을 그대로 넘긴다."""
    _request_id.reset(token)  # type: ignore[arg-type]


def get_request_id() -> str:
    return _request_id.get()


class RequestIdFilter(logging.Filter):
    """모든 LogRecord에 request_id 속성을 채워, format 문자열에서 %(request_id)s 사용 가능."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True
