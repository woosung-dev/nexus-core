"""
비동기 데이터베이스 엔진 및 세션 관리.
SQLModel + asyncpg 기반.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

settings = get_settings()

# 비동기 엔진 생성
engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={"server_settings": {"search_path": settings.DB_SCHEMA}},
    echo=settings.DEBUG,
    future=True,
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
