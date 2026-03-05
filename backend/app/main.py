"""
Nexus Core — FastAPI 애플리케이션 진입점.
"""

import logging
from contextlib import asynccontextmanager


from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.exceptions import NexusException
from app.schemas.common import ErrorResponse

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 라이프사이클 관리"""
    settings = get_settings()
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 시작")
    logger.info(f"   DEBUG={settings.DEBUG}")
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
    )

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
        logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
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
