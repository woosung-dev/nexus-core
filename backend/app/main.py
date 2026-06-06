"""
Nexus Core — FastAPI 애플리케이션 진입점.
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager


from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.exceptions import NexusException
from app.core.request_context import RequestIdFilter, reset_request_id, set_request_id
from app.schemas.common import ErrorResponse

# 로깅 설정 — 모든 레코드에 request_id를 주입하기 위해 root logger 핸들러에 Filter를 단다.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | [%(request_id)s] | %(name)s | %(message)s",
)
for _h in logging.getLogger().handlers:
    _h.addFilter(RequestIdFilter())
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 라이프사이클 관리"""
    settings = get_settings()
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 시작")
    logger.info(f"   DEBUG={settings.DEBUG}")
    if settings.KAKAO_SKILL_SECRET is None:
        logger.warning(
            "KAKAO_SKILL_SECRET 미설정 — 카카오 콜백 엔드포인트 인증이 비활성화 상태입니다. "
            "프로덕션에서는 반드시 설정하세요."
        )
    yield
    logger.info(f"👋 {settings.APP_NAME} 종료")


def create_app() -> FastAPI:
    """FastAPI 앱 팩토리"""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Multi-Persona AI Chatbot Platform — Blessing Q&A 상담 핵심",
        lifespan=lifespan,
    )

    # CORS 미들웨어
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id", "Server-Timing"],
    )

    # 요청 총시간 + request_id 미들웨어 — 관측성 영구 인프라.
    # 모든 응답에 X-Request-Id, Server-Timing 헤더를 부여하고, 한 줄 access log를 남긴다.
    @app.middleware("http")
    async def request_timing_middleware(request: Request, call_next):
        req_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:8]
        token = set_request_id(req_id)
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            # BaseHTTPMiddleware 안에서 raise 하면 CORS 미들웨어가 헤더를 못 붙여 클라이언트가
            # 'TypeError: Failed to fetch' 로 본다. 미들웨어 레벨에서 직접 500 응답을 만들어
            # 반환해야 CORS 가 그 응답에 헤더를 붙일 수 있다.
            # google.genai.errors.APIError 같은 외부 호출 실패의 reason/code/details 도 함께 남겨
            # 다음 사고 진단을 1줄 로그로 끝낼 수 있게 한다.
            elapsed_ms = (time.perf_counter() - start) * 1000
            extra = {
                attr: getattr(exc, attr, None)
                for attr in ("code", "status", "details", "message")
                if hasattr(exc, attr)
            }
            logger.exception(
                "req FAILED %s %s elapsed=%.1fms | %s: %s | extra=%s",
                request.method,
                request.url.path,
                elapsed_ms,
                type(exc).__name__,
                exc,
                extra or "(no extra fields)",
            )
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=ErrorResponse(
                    success=False,
                    error_code="INTERNAL_SERVER_ERROR",
                    message="서버 내부 오류가 발생했습니다. 관리자에게 문의하세요.",
                ).model_dump(),
            )
            response.headers["X-Request-Id"] = req_id
            response.headers["Server-Timing"] = f"total;dur={elapsed_ms:.1f}"
            reset_request_id(token)
            return response
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-Id"] = req_id
        # 기존 Server-Timing이 있으면 보존하고 total span만 append.
        existing = response.headers.get("Server-Timing")
        total_span = f"total;dur={elapsed_ms:.1f}"
        response.headers["Server-Timing"] = (
            f"{existing}, {total_span}" if existing else total_span
        )
        logger.info(
            "req %s %s status=%d elapsed=%.1fms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        reset_request_id(token)
        return response

    # API 라우터 등록
    app.include_router(v1_router)

    # ==========================
    # 글로벌 커스텀 예외 핸들러 등록
    # ==========================
    
    @app.exception_handler(NexusException)
    async def nexus_exception_handler(request: Request, exc: NexusException):
        logger.warning(f"NexusException: {exc.error_code} - {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                success=False,
                error_code=exc.error_code,
                message=exc.message,
                details=exc.details,
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"RequestValidationError: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                success=False,
                error_code="VALIDATION_ERROR",
                message="요청 데이터(스키마)가 올바르지 않습니다.",
                details=exc.errors(),
            ).model_dump(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning(f"HTTPException: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                success=False,
                error_code="HTTP_ERROR",
                message=str(exc.detail),
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        # google.genai.errors.APIError (ClientError/ServerError 포함) 는 reason/code/details 가
        # 진단의 핵심 — 그냥 str(exc) 만 찍으면 'Failed to embed content' 같은 모호한 message 만 남고
        # RESOURCE_EXHAUSTED 의 reason (MODEL_CAPACITY_EXHAUSTED vs USER_QUOTA_EXCEEDED) 을 잃는다.
        extra: dict[str, object] = {}
        for attr in ("code", "status", "details", "message", "response_json"):
            if hasattr(exc, attr):
                try:
                    extra[attr] = getattr(exc, attr)
                except Exception:
                    pass
        if extra:
            logger.error(
                f"Unhandled Exception: {type(exc).__name__}: {exc} | extra={extra}",
                exc_info=True,
            )
        else:
            logger.error(f"Unhandled Exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                success=False,
                error_code="INTERNAL_SERVER_ERROR",
                message="서버 내부 오류가 발생했습니다. 관리자에게 문의하세요.",
            ).model_dump(),
        )

    # 헬스체크
    @app.get("/health", tags=["시스템"])
    async def health_check():
        return {"status": "ok", "version": settings.APP_VERSION}

    return app


# uvicorn 진입점
app = create_app()
