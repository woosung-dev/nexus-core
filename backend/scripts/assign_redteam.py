# 레드팀 입력관리 질문을 담당자 N명에게 랜덤·균등 배정하는 스크립트
"""
레드팀 입력관리(redteam_question_groups)의 전체 고유 질문을 담당자 N명에게
랜덤·균등(1/N)으로 배정한다. 기존 assignee 값은 모두 덮어쓴다.

Usage:
    uv run python scripts/assign_redteam.py --dry-run
    uv run python scripts/assign_redteam.py
    uv run python scripts/assign_redteam.py --seed 42 --assignees "이치무라 준나,윤종범,이동규"

실서버(Neon) 적용 — DATABASE_URL을 Neon 연결 문자열로 지정:
    DATABASE_URL=<neon> uv run python scripts/assign_redteam.py --dry-run
    DATABASE_URL=<neon> uv run python scripts/assign_redteam.py
"""

import argparse
import asyncio
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select, update

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.database import async_session  # noqa: E402
from app.models.redteam import RedteamQuestionGroup  # noqa: E402

DEFAULT_ASSIGNEES = ["이치무라 준나", "윤종범", "이동규"]


def _split_even(ids: list[int], n: int) -> list[list[int]]:
    """ids를 n개 그룹으로 가능한 균등 분할 (나머지는 앞쪽 그룹에 1개씩 추가)."""
    base, extra = divmod(len(ids), n)
    chunks: list[list[int]] = []
    start = 0
    for i in range(n):
        size = base + (1 if i < extra else 0)
        chunks.append(ids[start : start + size])
        start += size
    return chunks


async def run(dry_run: bool, seed: int | None, assignees: list[str]) -> None:
    async with async_session() as session:
        ids = list(
            (await session.execute(select(RedteamQuestionGroup.id))).scalars().all()
        )
        total = len(ids)
        if total == 0:
            print("질문 그룹이 없습니다.")
            return

        rng = random.Random(seed)
        rng.shuffle(ids)
        chunks = _split_even(ids, len(assignees))

        print(f"전체 질문 그룹: {total}")
        for name, chunk in zip(assignees, chunks):
            print(f"  {name}: {len(chunk)}건")
        assert sum(len(c) for c in chunks) == total

        if dry_run:
            print("[dry-run] DB 변경 없음.")
            return

        # 기존 assignee 값 백업
        backup = (
            await session.execute(
                select(RedteamQuestionGroup.id, RedteamQuestionGroup.assignee)
            )
        ).all()
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = ROOT / "scripts" / f"assign_backup_{ts}.json"
        backup_path.write_text(
            json.dumps(
                [{"id": r.id, "assignee": r.assignee} for r in backup],
                ensure_ascii=False,
                indent=2,
            )
        )
        print(f"백업 저장: {backup_path}")

        now = datetime.now(timezone.utc)
        for name, chunk in zip(assignees, chunks):
            if not chunk:
                continue
            await session.execute(
                update(RedteamQuestionGroup)
                .where(RedteamQuestionGroup.id.in_(chunk))
                .values(assignee=name, updated_at=now)
            )
        await session.commit()

        # 검증 — 담당자별 건수
        verify = (
            await session.execute(
                select(RedteamQuestionGroup.assignee, func.count()).group_by(
                    RedteamQuestionGroup.assignee
                )
            )
        ).all()
        print("적용 후 담당자별 건수:")
        for a, c in verify:
            print(f"  {a or '(미지정)'}: {c}")


def main() -> None:
    parser = argparse.ArgumentParser(description="레드팀 질문 담당자 랜덤·균등 배정")
    parser.add_argument("--dry-run", action="store_true", help="DB 변경 없이 분포만 출력")
    parser.add_argument("--seed", type=int, default=None, help="셔플 시드(재현용)")
    parser.add_argument(
        "--assignees",
        type=str,
        default=",".join(DEFAULT_ASSIGNEES),
        help="쉼표 구분 담당자 명단",
    )
    args = parser.parse_args()
    assignees = [a.strip() for a in args.assignees.split(",") if a.strip()]
    if not assignees:
        parser.error("담당자 명단이 비어 있습니다.")
    asyncio.run(run(args.dry_run, args.seed, assignees))


if __name__ == "__main__":
    main()
