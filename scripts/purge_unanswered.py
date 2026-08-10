#!/usr/bin/env python
"""못 답한 질문 기록의 보존 기간 적용 — 90일 초과 행을 지운다.

    cd backend && uv run python ../scripts/purge_unanswered.py            # 미리보기
    cd backend && uv run python ../scripts/purge_unanswered.py --apply    # 실제 삭제
    cd backend && uv run python ../scripts/purge_unanswered.py --days 30 --apply

이 표는 실사용자 질문 원문을 담는다. 테스트 문항에도 성폭력·이혼·불륜이 있었고
관리자 화면에 그대로 뜨므로 수명을 제한한다.

⚠ **이 삭제는 `messages` 를 건드리지 않는다.** 원문은 거기 무기한 남는다 —
실질 노출이 줄어드는 게 아니라 **새로 만든 데이터의 수명만** 제한된다.
전체 보존 정책은 별건이다.

크론 인프라가 없어 수동 실행이다. 자동화하려면 배포 파이프라인에 붙여야 한다.
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import delete, func, select  # noqa: E402

from app.core.database import async_session  # noqa: E402

# FK 대상 테이블이 SQLModel.metadata 에 없으면 매퍼 구성이 NoReferencedTableError 로 죽는다.
# 앱은 라우터가 전부 끌어오지만 단독 스크립트는 직접 챙겨야 한다 (alembic/env.py 와 같은 이유).
from app.models.bot import Bot  # noqa: E402,F401
from app.models.chat import ChatSession, Message  # noqa: E402,F401
from app.models.ops_facts import OpsFact  # noqa: E402,F401
from app.models.unanswered import UnansweredQuestion  # noqa: E402


async def main(days: int, apply: bool) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    async with async_session() as session:
        total = await session.scalar(select(func.count()).select_from(UnansweredQuestion))
        stale = await session.scalar(
            select(func.count())
            .select_from(UnansweredQuestion)
            .where(UnansweredQuestion.created_at < cutoff)
        )
        print(f"보존 {days}일 · 기준 {cutoff.isoformat()}")
        print(f"전체 {total}행 / 삭제 대상 {stale}행")

        if not apply:
            print("미리보기다. 실제로 지우려면 --apply 를 붙여라.")
            return
        if not stale:
            return

        await session.execute(
            delete(UnansweredQuestion).where(UnansweredQuestion.created_at < cutoff)
        )
        await session.commit()
        print(f"삭제 완료 — {stale}행")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.days, args.apply))
