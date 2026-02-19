"""
API v1 라우터 통합.
모든 v1 엔드포인트를 하나의 라우터로 결합한다.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import admin, bots, chat, kakao

router = APIRouter(prefix="/api/v1")

# Public API
router.include_router(bots.router)
router.include_router(chat.router)
router.include_router(kakao.router)

# Admin API
router.include_router(admin.router)
