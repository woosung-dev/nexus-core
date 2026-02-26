"""
초기 봇 시드 데이터 스크립트.
Blessing Q&A 상담 봇 + DB 테이블 생성.

사용법:
    uv run python -m scripts.seed_bots
"""

import asyncio
import logging

from sqlmodel import SQLModel, select

from app.core.database import async_session, engine
from app.models.bot import Bot
from app.models.chat import ChatSession, Message  # noqa: F401 — 테이블 생성용
from app.models.user import User  # noqa: F401 — 테이블 생성용

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Blessing Q&A 시드 데이터
SEED_BOTS = [
    {
        "name": "Blessing Q&A",
        "description": "축복과 관련된 질문에 대해 성경 기반의 따뜻한 상담을 제공하는 AI 어시스턴트입니다.",
        "icon_url": None,
        "tags": ["상담", "축복", "Q&A"],
        "is_verified": True,
        "is_new": True,
        "plan_required": "FREE",
        "system_prompt": (
            "당신은 축복 상담 전문 AI 어시스턴트 'Blessing Q&A'입니다.\n"
            "사용자의 질문에 대해 따뜻하고 위로가 되는 답변을 제공하세요.\n"
            "답변은 한국어로 작성하며, 공감과 격려를 중심으로 대화하세요.\n"
            "필요한 경우 성경 구절을 인용할 수 있습니다."
        ),
        "llm_model": "gemini-3.0-flash",
        "is_active": True,
    },
]


async def seed_database():
    """DB 테이블 생성 및 시드 데이터 삽입"""
    # 1. 테이블 생성
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    logger.info("✅ DB 테이블 생성 완료")

    # 2. 시드 데이터 삽입
    async with async_session() as session:
        for bot_data in SEED_BOTS:
            # 중복 체크
            result = await session.execute(
                select(Bot).where(Bot.name == bot_data["name"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.info(f"⏭️  이미 존재: {bot_data['name']}")
                continue

            bot = Bot(**bot_data)
            session.add(bot)
            logger.info(f"➕ 봇 추가: {bot_data['name']}")

        await session.commit()

    logger.info("🎉 시드 데이터 삽입 완료!")


if __name__ == "__main__":
    asyncio.run(seed_database())
