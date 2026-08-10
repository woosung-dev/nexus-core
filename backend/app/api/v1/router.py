"""
API v1 라우터 통합.
모든 v1 엔드포인트를 하나의 라우터로 결합한다.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, bots, chat, clarification_preview, kakao, users, dashboard
from app.api.v1.endpoints.admin import bots as admin_bots, users as admin_users, faqs, chats, redteam, instructions as admin_instructions, ops_facts as admin_ops_facts, unanswered as admin_unanswered

router = APIRouter(prefix="/api/v1")

# Public API
router.include_router(auth.router)
router.include_router(bots.router)
router.include_router(chat.router)
router.include_router(clarification_preview.router)
router.include_router(kakao.router)
router.include_router(users.router)

# Admin API
router.include_router(admin_bots.router)
router.include_router(admin_users.router)
router.include_router(faqs.router)
router.include_router(chats.router)
router.include_router(redteam.router)
router.include_router(admin_instructions.router)
router.include_router(admin_ops_facts.router)
router.include_router(admin_unanswered.router)
router.include_router(dashboard.router)
