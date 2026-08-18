# 베이스(프로브 최고) + 보강레이어 병합 → localhost 개발 DB id5 에 검증 적용(운영 Neon·store bot_id5 미반영)
# 사용: cd backend && set -a; source .env; set +a; uv run --with asyncpg python ../exports/_freeze_apply_local.py [BASE_NAME]
import asyncio
import json
import os
import re
import sys
from pathlib import Path

EXP = Path("/Users/woosung/project/agy-project/nexus-core/syste-prompt-ver/_experiment")
R3 = Path("/Users/woosung/project/agy-project/nexus-core/exports/round3_rag")
GRADED = Path("/Users/woosung/project/agy-project/nexus-core/exports/probe_graded.json")
BASE_FILES = {"A_원리": EXP / "A_원리.md", "B_정밀정보": EXP / "B_정밀정보.md", "D_통합v5": EXP / "D_통합v5.md"}
DEV_BOT_ID = 5  # localhost 개발 DB id5(default) — 검증용. 운영 Neon 아님.


def build_merged(base_name):
    base = BASE_FILES[base_name].read_text(encoding="utf-8")
    layer = (R3 / "system_prompt_보강레이어.md").read_text(encoding="utf-8")
    # 보강레이어의 메타 주석/헤더는 떼고 본문 규칙만 덧붙인다.
    layer_body = re.sub(r"^<!--.*?-->\n", "", layer, flags=re.DOTALL)
    merged = base.rstrip() + "\n\n---\n\n# [3주차 보강 — 신규 공문·6대오류·표기 규칙]\n\n" + layer_body.strip() + "\n"
    out = R3 / f"final_system_prompt_{base_name}.md"
    out.write_text(merged, encoding="utf-8")
    return merged, out


async def main():
    if len(sys.argv) > 1:
        base_name = sys.argv[1]
    elif GRADED.exists():
        base_name = json.loads(GRADED.read_text(encoding="utf-8"))["best"]
    else:
        print("베이스 미지정 + probe_graded.json 없음 — BASE_NAME 인자 필요"); return
    print(f"베이스: {base_name}")

    merged, out = build_merged(base_name)
    print(f"병합 system_prompt 저장: {out} ({len(merged)} chars)")

    # localhost 개발 DB 연결(db→localhost:5432 오버라이드)
    clean = re.sub(r"\+asyncpg", "", os.environ.get("DATABASE_URL", ""))
    url = re.sub(r"@db:\d+", "@localhost:5432", clean); url = re.sub(r"@db/", "@localhost:5432/", url)
    import asyncpg
    conn = await asyncpg.connect(url, timeout=8)
    row = await conn.fetchrow("select id, name, length(coalesce(system_prompt,'')) as plen from bots where id=$1", DEV_BOT_ID)
    if not row:
        print(f"  [중단] localhost DB 에 id={DEV_BOT_ID} 없음"); await conn.close(); return
    print(f"  대상(개발 DB): id={row['id']} name={row['name']} 기존 prompt 길이={row['plen']}")
    await conn.execute("update bots set system_prompt=$1 where id=$2", merged, DEV_BOT_ID)
    after = await conn.fetchrow("select length(system_prompt) as plen from bots where id=$1", DEV_BOT_ID)
    print(f"  적용 완료: 새 prompt 길이={after['plen']} (localhost 개발 DB 전용, 운영 Neon·store bot_id5 미반영)")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
