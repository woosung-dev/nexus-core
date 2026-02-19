"""
Nexus Core — FastAPI 애플리케이션 진입점.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import get_settings

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
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API 라우터 등록
    app.include_router(v1_router)

    # 헬스체크
    @app.get("/health", tags=["시스템"])
    async def health_check():
        return {"status": "ok", "version": settings.APP_VERSION}

    return app


# uvicorn 진입점
app = create_app()
