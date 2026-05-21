"""
비동기 데이터베이스 엔진 및 세션 관리.
SQLModel + asyncpg 기반.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

settings = get_settings()

# 비동기 엔진 생성.
# Pool 설정 명시 — 기본값(pool_size=5)은 동시 요청이 늘면 즉시 saturate.
# Supabase Free tier 직접 연결 한도(~60)를 고려해 10+10으로 설정.
# pool_recycle: stale connection 자동 재생성 (Supabase는 idle 후 일정 시간 지나면 끊음).
# pool_pre_ping: 매 사용 전 연결 유효성 ping. 안정성을 위해 켬 (운영 환경 우선).
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_size=10,
    max_overflow=10,
    pool_recycle=1800,
    pool_pre_ping=True,
)

# 비동기 세션 팩토리
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency: 비동기 DB 세션 주입"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
