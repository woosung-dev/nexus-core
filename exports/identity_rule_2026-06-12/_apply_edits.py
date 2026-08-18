# 검증 통과한 Edit A(영적 주체성+헤딩금지+구체성) + Edit B(감정 객관화/경계선)를 dev 봇 3·5에 적용
"""
프로브 통과 후 실행. dev localhost 만(Neon 금지). 적용 전 백업 + 앵커 검증 + 변경 로그.
실행: cd backend && uv run python ../exports/identity_rule_2026-06-12/_apply_edits.py --apply
--apply 없으면 드라이런(앵커 검증 + 미리보기만).
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

# Edit A — 관계·갈등 영적 주체성(가정연합 아이덴티티) + 제3자 헤딩 금지 + (나)구체성
EDIT_A = {
    5: (
        "5. 지속·심화·위기 신호일 때는 떠넘김이 아닌 동반 제안으로 전문 상담을 권한다.",
        "5. 부부·가정의 갈등에는 하늘부모님을 중심에 두고 서로 존중·배려하면 외부의 개입 없이도 가정 안에서 "
        "주체적으로 풀어갈 수 있다는 확신을 준다(가정연합의 핵심 정체성). 외부 기관·멘토 의존을 답변의 중심이나 "
        "별도 헤딩으로 앞세우지 말고, 부부·가족이라는 1차 관계 안에서 함께 이겨낼 내적 주체성을 독려한다. "
        "전문 상담은 지속·심화·위기 신호가 실제로 있을 때만, 떠넘김이 아닌 동반 제안으로 본문 끝에 짧게 권한다.",
    ),
    3: (
        "봇이 먼저 충분히 곁에 있어준 뒤, 지속·심화 신호일 때만 떠넘김이 아닌 동반 제안으로 전문 상담을 권한다.",
        "부부·가정의 갈등에는 하늘부모님을 중심에 두고 서로 존중·배려하면 외부의 개입 없이도 가정 안에서 "
        "주체적으로 풀어갈 수 있다는 확신을 준다(가정연합의 핵심 정체성). 외부 기관·멘토 의존을 답변의 중심이나 "
        "별도 헤딩으로 앞세우지 말고, 부부·가족이라는 1차 관계 안에서 함께 이겨낼 내적 주체성을 독려한다. "
        "해결책은 추상적 나열로 끝내지 말고 실천 가능한 구체 단계(예: 경청의 시간 만들기, 감정·의도 전달, 작은 정성)로 "
        "제시한다. 전문 상담은 봇이 충분히 곁에 있어준 뒤 지속·심화 신호일 때만, 본문 끝에 짧게 동반 제안한다.",
    ),
}
# Edit B — 감정 객관화 + 행동 경계선(거리두기=안전장치). 두 봇 동일 앵커.
ANCHOR_B = "끌림·고통은 인정하되 권장하지 않는다. 폭력·강요·통제가 있으면 위기(안전) 우선."
NEW_B = (
    "끌림·고통은 인정하되 권장하지 않는다. 감정·충동이 올라올 때는 억누르거나 자책하게 두지 말고 "
    "'지금 잠시 흔들리고 있구나'라고 객관적으로 인지하도록 돕고(감정의 객관화), 물리적 거리두기 같은 "
    "구체적 행동의 경계선을 '축복을 지키기 위한 최소한의 안전장치'로 제시해 실천하기 쉬운 단계로 준다. "
    "폭력·강요·통제가 있으면 위기(안전) 우선."
)


def _db_url_localhost():
    for line in (Path("/Users/woosung/project/agy-project/nexus-core/backend/.env")).read_text().splitlines():
        s = line.strip()
        if s.startswith("#") or not s.startswith("DATABASE_URL"):
            continue
        v = s.split("=", 1)[1].strip().strip('"').strip("'")
        if "neon" in v.lower():
            continue
        v = re.sub(r"@[^:/]+", "@localhost", v, count=1).replace("postgresql+asyncpg://", "postgresql://")
        assert "neon" not in v.lower(), "Neon 금지"
        return v
    raise RuntimeError("localhost DATABASE_URL 없음")


async def main():
    import asyncpg

    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제 dev DB 갱신 (없으면 드라이런)")
    args = ap.parse_args()

    conn = await asyncpg.connect(_db_url_localhost())
    try:
        rows = {r["id"]: r["system_prompt"] for r in await conn.fetch("SELECT id, system_prompt FROM bots WHERE id IN (3,5)")}
        BACKUP.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%dT%H%M")
        changes = []
        for bid in (5, 3):
            base = rows[bid]
            old_a, new_a = EDIT_A[bid]
            assert old_a in base, f"id{bid} Edit A 앵커 미발견"
            assert ANCHOR_B in base, f"id{bid} Edit B 앵커 미발견"
            edited = base.replace(old_a, new_a).replace(ANCHOR_B, NEW_B)
            assert edited != base and new_a in edited and NEW_B in edited
            (BACKUP / f"id{bid}_base_{ts}.md").write_text(base, encoding="utf-8")
            changes.append((bid, base, edited))
            print(f"id{bid}: {len(base)}자 → {len(edited)}자 (+{len(edited)-len(base)}) 앵커 2종 검증 OK")

        if not args.apply:
            print("\n[드라이런] --apply 로 실제 적용. 백업은 _backup_prompts/ 에 기록됨.")
            return

        for bid, _b, edited in changes:
            await conn.execute("UPDATE bots SET system_prompt=$1 WHERE id=$2", edited, bid)
        print(f"\n적용 완료 (dev localhost id 3·5). 백업: {BACKUP}")

        lines = [f"# 관계·갈등 프롬프트 업그레이드 변경 로그 ({ts})", "",
                 "대상: dev localhost id5(블레싱 가)·id3(블레싱 나). Neon 미적용.",
                 "근거: 2주차 레드팀 피드백 3건(제3자 앞세움·감정객관화/경계선·하늘부모님 중심 주체성/구체성).",
                 "검증: 멀티샘플 base vs edited 프로브 — 제3자 헤딩 0/9, 감정객관화 9/9, 위기 에스컬레이션 6/6 유지.", "",
                 "## Edit A (관계·갈등 영적 주체성 = 가정연합 아이덴티티 + 제3자 헤딩 금지 + 나 구체성)",
                 "기존 '동반 제안' 줄을 본문 통합 대체.", "",
                 "## Edit B (감정 객관화 + 행동 경계선)",
                 "'끌림·고통은 인정하되 권장하지 않는다' 줄에 통합.", "",
                 f"백업: _backup_prompts/id{{5,3}}_base_{ts}.md"]
        LOG.write_text("\n".join(lines), encoding="utf-8")
        print(f"변경 로그: {LOG}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
