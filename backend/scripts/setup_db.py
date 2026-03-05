#!/usr/bin/env python
"""
Nexus Core — DB 초기 세팅 스크립트

Alembic 마이그레이션을 실행하여 스키마 및 테이블을 생성합니다.
실제 운영 데이터는 서버 기동 후 Admin UI 또는 API를 통해 직접 입력하세요.

Usage:
    uv run python scripts/setup_db.py          # 마이그레이션 실행
    uv run python scripts/setup_db.py --reset  # 스키마 초기화 후 재생성 (⚠️ 모든 데이터 삭제)
"""

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from app.core.config import get_settings


# ─── 스키마 초기화 (--reset 옵션) ────────────────────────────────────────
async def reset_schema(engine, schema: str) -> None:
    """스키마를 완전히 삭제 후 재생성합니다. 주의: 모든 데이터가 삭제됩니다."""
    print(f"\n⚠️  스키마 '{schema}'를 초기화합니다. 기존 데이터가 모두 삭제됩니다.")
    async with engine.connect() as conn:
        await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        await conn.execute(text(f"CREATE SCHEMA {schema}"))
        await conn.commit()
    print(f"✅ 스키마 '{schema}' 초기화 완료!")


# ─── Alembic 마이그레이션 ─────────────────────────────────────────────────
def run_migrations() -> None:
    """alembic upgrade head를 실행하여 테이블을 생성합니다."""
    print("\n[1/1] Alembic 마이그레이션 실행 중...")
    backend_dir = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=backend_dir,
        capture_output=False,
    )
    if result.returncode != 0:
        print("❌ 마이그레이션 실패. 위 에러 로그를 확인하세요.")
        sys.exit(1)
    print("✅ 마이그레이션 완료!")


# ─── Main ────────────────────────────────────────────────────────────────
async def main(args: argparse.Namespace) -> None:
    settings = get_settings()
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        connect_args={
            "server_settings": {"search_path": settings.DB_SCHEMA},
            "statement_cache_size": 0,
        },
    )

    try:
        if args.reset:
            await reset_schema(engine, settings.DB_SCHEMA)

        run_migrations()

        print("\n🎉 DB 초기 세팅 완료!")
        print("   → 서버를 기동하고 Admin UI 또는 Swagger(/api/docs)에서 데이터를 입력하세요.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nexus Core DB 초기 세팅 스크립트")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="⚠️  스키마 전체 삭제 후 처음부터 재생성 (모든 데이터 삭제!)",
    )
    args = parser.parse_args()
    asyncio.run(main(args))
