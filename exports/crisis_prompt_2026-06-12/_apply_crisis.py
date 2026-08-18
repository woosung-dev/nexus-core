# 위기 섹션 본문 보강(번호 유지 + 안전검토 개선: 확인+동시행동·고립폴백·내부권위 후순위·생성형) dev 적용
"""
사용자 결정(급성 위기 검증번호 유지) + 적대적 안전검토 개선을 위기 '대응' 줄에 본문 통합.
dev localhost id3·5 만(Neon 금지). 백업 + 변경 로그.
실행: cd backend && uv run python ../exports/crisis_prompt_2026-06-12/_apply_crisis.py --apply
"""

import argparse
import asyncio
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))
BACKUP = Path(__file__).resolve().parent / "_backup_prompts"
LOG = Path(__file__).resolve().parent / "변경로그.md"

# 두 봇 공통 앵커(번호 목록 줄 끝). 번호는 유지하고 뒤에 안전 개선 절을 본문 통합.
ANCHOR = "5) 긴 설명·교리·죄책감·행정 중단. 전화번호는 이 고정 목록 그대로만 안내하고 새로 지어내지 않는다."
NEW = (
    ANCHOR
    + " 확인을 기다리느라 멈추지 말고, 안전 행동(안전한 곳으로 옮기기·혼자 있지 않기·곁의 사람에게 지금 "
    "도움 청하기)을 같은 응답에서 함께 제시한다. 곁에 아무도 떠오르지 않아도 위 상담 전화는 24시간 지금 닿을 수 "
    "있음을 알리고, 끝까지 곁에 머문다. 위기의 원인이 공동체·축복·담당자 자체로 보이면 그쪽으로 먼저 보내지 말고 "
    "전문 상담과 안전을 우선한다. 정형 고정문을 낭독하지 말고 그 사람의 말에 맞춰 따뜻하게 응답하되 안전을 향한 "
    "절박함은 끝까지 유지한다."
)


def _db_url_localhost():
    for line in Path("/Users/woosung/project/agy-project/nexus-core/backend/.env").read_text().splitlines():
        s = line.strip()
        if s.startswith("#") or not s.startswith("DATABASE_URL"):
            continue
        v = s.split("=", 1)[1].strip().strip('"').strip("'")
        if "neon" in v.lower():
            continue
        v = re.sub(r"@[^:/]+", "@localhost", v, count=1).replace("postgresql+asyncpg://", "postgresql://")
        assert "neon" not in v.lower()
        return v
    raise RuntimeError("localhost DATABASE_URL 없음")


async def main():
    import asyncpg

    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    conn = await asyncpg.connect(_db_url_localhost())
    try:
        rows = {r["id"]: r["system_prompt"] for r in await conn.fetch("SELECT id, system_prompt FROM bots WHERE id IN (3,5)")}
        BACKUP.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%dT%H%M")
        changes = []
        for bid in (5, 3):
            base = rows[bid]
            assert ANCHOR in base, f"id{bid} 위기 앵커 미발견"
            assert base.count(ANCHOR) == 1, f"id{bid} 앵커 중복"
            edited = base.replace(ANCHOR, NEW)
            assert edited != base
            (BACKUP / f"id{bid}_base_{ts}.md").write_text(base, encoding="utf-8")
            changes.append((bid, edited))
            print(f"id{bid}: {len(base)}자 → {len(edited)}자 (+{len(edited)-len(base)}) 위기 앵커 OK")

        if not args.apply:
            print("\n[드라이런] --apply 로 실제 적용.")
            return
        for bid, edited in changes:
            await conn.execute("UPDATE bots SET system_prompt=$1 WHERE id=$2", edited, bid)
        print(f"\n적용 완료 (dev id 3·5). 백업: {BACKUP}")
        LOG.write_text(
            "\n".join([
                f"# 위기 섹션 본문 보강 변경 로그 ({ts})",
                "",
                "대상: dev localhost id5(가)·id3(나). Neon 미적용.",
                "근거: 피드백 #1(위기·민감) + 사용자 결정(급성 위기 검증번호 유지) + 적대적 안전검토 개선.",
                "내용: 위기 '대응' 줄에 — 확인+동시 안전행동, 고립 사용자 폴백(번호 24시간 닿음+봇 현존),",
                "      위기 원인이 공동체·담당자면 내부 권위 후순위, 정형 낭독 금지(생성형) 를 본문 통합.",
                "코드 동반 변경: crisis_service CRISIS_DIRECTIVE 주입 제거(본문 이관), strip 검증번호 화이트리스트,",
                "      BLOCKED_FALLBACK 검증번호 포함. 백엔드 테스트 90 통과.",
                f"백업: _backup_prompts/id{{5,3}}_base_{ts}.md",
            ]),
            encoding="utf-8",
        )
        print(f"변경 로그: {LOG}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
