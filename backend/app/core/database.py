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
    connect_args={
        "server_settings": {"search_path": settings.DB_SCHEMA},
        # [중요] Supabase 등 PgBouncer/Supavisor 기반의 "Transaction Mode" Pooler를 
        # 사용 중이라면 statement_cache_size=0 으로 캐시를 꺼야 에러가 발생하지 않습니다.
        # 추후 AWS RDS, GCP Cloud SQL 등에 "직접 연결(Direct Connection)" 하거나 
        # "Session Mode" Pooler를 사용할 경우, 이 줄을 삭제(또는 주석 처리)하여 
        # asyncpg의 캐싱 성능(속도 향상)을 다시 활성화하는 것이 유리합니다.
        "statement_cache_size": 0,
    },
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
