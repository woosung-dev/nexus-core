"""되묻기 규칙을 봇에 적재한다. **로컬 DB 전용.**

관리자 API(`PUT /admin/bots/{id}`)로는 넣을 수 없다 — `validate_active_policy` 가 활성
규칙마다 봇의 **File Search 스토어**에 있는 `document_id` 를 요구하는데, 대상 봇은
`retrieval_mode='lexical'` 이라 스토어가 없다. 어휘 경로의 `decide()` 는 `document_refs` 를
읽지 않으므로 여기서는 직접 넣는다.

    uv run python ../scripts/load_clarification_policy.py --bot-id 29
    uv run python ../scripts/load_clarification_policy.py --bot-id 29 --disable

라이브(Neon)에는 쓰지 마라. `--dsn` 기본값이 로컬이고, neon 이 들어간 DSN 은 거부한다.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import asyncpg

REPO = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = REPO / "docs" / "architecture" / "clarification-policy-v2-2026-08-10.json"
DEFAULT_DSN = "postgresql://nexus_user:nexus_pass@localhost:5432/nexus_core"


async def main(dsn: str, bot_id: int, policy_path: Path, disable: bool) -> None:
    if "neon" in dsn:
        raise SystemExit("라이브 DB 는 읽기 전용이다. 이 스크립트는 로컬에만 쓴다.")

    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    conn = await asyncpg.connect(dsn, timeout=15)
    try:
        row = await conn.fetchrow(
            "select id, name, retrieval_mode from bots where id = $1", bot_id
        )
        if row is None:
            raise SystemExit(f"봇 {bot_id} 가 없다.")

        if disable:
            await conn.execute("update bots set clarify_enabled = false where id = $1", bot_id)
            print(f"봇 {bot_id}({row['name']}) 되묻기 끔.")
            return

        await conn.execute(
            "update bots set clarification_policy = $2::jsonb, clarify_enabled = true where id = $1",
            bot_id,
            json.dumps(policy, ensure_ascii=False),
        )
        check = await conn.fetchrow(
            "select clarify_enabled, clarification_policy from bots where id = $1", bot_id
        )
        stored = check["clarification_policy"]
        stored = json.loads(stored) if isinstance(stored, str) else stored
        rules = [rule["id"] for rule in stored.get("rules", [])]
        print(
            f"봇 {bot_id}({row['name']} · {row['retrieval_mode']}) "
            f"clarify_enabled={check['clarify_enabled']} 규칙 {len(rules)}개: {', '.join(rules)}"
        )
    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bot-id", type=int, required=True)
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--disable", action="store_true", help="규칙은 두고 되묻기만 끈다")
    args = parser.parse_args()
    asyncio.run(main(args.dsn, args.bot_id, args.policy, args.disable))
