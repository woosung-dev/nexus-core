"""
Alembic 마이그레이션 환경 설정.
- 비동기(asyncpg) 연결 지원
- nexus_core 스키마에서만 마이그레이션 실행
- .env 파일에서 DATABASE_URL과 DB_SCHEMA를 자동으로 읽습니다
"""

import asyncio
from logging.config import fileConfig

import sqlalchemy
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# SQLModel의 metadata를 가져오기 위해 모든 모델을 임포트
from app.models.user import User  # noqa: F401
from app.models.bot import Bot  # noqa: F401
from app.models.chat import ChatSession, Message  # noqa: F401
from sqlmodel import SQLModel

from app.core.config import get_settings

settings = get_settings()

# Alembic Config 객체
config = context.config

# 로깅 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# .env의 DATABASE_URL을 Alembic 설정에 주입
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 모든 모델의 메타데이터를 autogenerate에 사용
target_metadata = SQLModel.metadata

# nexus_core 스키마로 테이블 스키마 설정
# 이 설정이 없으면 Alembic이 public 스키마에 테이블을 생성합니다
for table in target_metadata.tables.values():
    table.schema = settings.DB_SCHEMA


def run_migrations_offline() -> None:
    """오프라인 모드: DB 연결 없이 SQL 스크립트를 생성합니다."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema=settings.DB_SCHEMA,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """실제 마이그레이션 실행 (동기 컨텍스트)."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema=settings.DB_SCHEMA,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """온라인 모드: asyncpg 비동기 엔진으로 마이그레이션을 실행합니다."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={
            # nexus_core 스키마를 search_path로 설정
            "server_settings": {"search_path": settings.DB_SCHEMA},
            # Supabase Pooler(Transaction Mode) 사용 시 필수
            "statement_cache_size": 0,
        },
    )

    async with connectable.connect() as connection:
        # nexus_core 스키마가 없으면 생성 (멱등성 보장)
        await connection.execute(
            sqlalchemy.text(f"CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA}")
        )
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
