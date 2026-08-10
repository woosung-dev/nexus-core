"""되묻기 규칙을 봇에 적재한다.

관리자 API(`PUT /admin/bots/{id}`)로는 넣을 수 없다 — `validate_active_policy` 가 활성
규칙마다 봇의 **File Search 스토어**에 있는 `document_id` 를 요구하는데, 대상 봇은
`retrieval_mode='lexical'` 이라 스토어가 없다. 어휘 경로의 `decide()` 는 `document_refs` 를
읽지 않으므로 여기서는 직접 넣는다.

    uv run python ../scripts/load_clarification_policy.py --bot-id 29
    uv run python ../scripts/load_clarification_policy.py --bot-id 29 --disable

**라이브(Neon)에 쓸 때는 두 개를 더 대야 한다.** 기본값은 여전히 로컬이고, neon DSN 은
`--live` 없이는 거부한다.

    ... --dsn "$LIVE" --bot-id 11 --live --expect-bot-name "테스트 봇 D-1 ver2" --dry-run
    ... --dsn "$LIVE" --bot-id 11 --live --expect-bot-name "테스트 봇 D-1 ver2"

`--expect-bot-name` 이 필수인 이유는 **로컬과 라이브의 봇 id 가 다른 봇을 가리키기
때문이다** — 로컬 11 은 `opus2_v4`, 라이브 11 은 `테스트 봇 D-1 ver2` 다. id 만 믿고
쏘면 엉뚱한 봇의 프롬프트 경로를 바꾼다. 이름이 다르면 아무것도 쓰지 않고 죽는다.
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


async def main(
    dsn: str,
    bot_id: int,
    policy_path: Path,
    disable: bool,
    live: bool,
    expect_bot_name: str | None,
    dry_run: bool,
) -> None:
    is_live = "neon" in dsn
    if is_live and not live:
        raise SystemExit("라이브 DSN 이다. 의도한 것이면 --live 와 --expect-bot-name 을 대라.")
    if live and not expect_bot_name:
        raise SystemExit("--live 에는 --expect-bot-name 이 필수다. 봇 id 는 DB 마다 다른 봇이다.")

    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    conn = await asyncpg.connect(dsn, timeout=15)
    try:
        row = await conn.fetchrow(
            "select id, name, retrieval_mode, clarify_enabled, clarification_policy "
            "from bots where id = $1",
            bot_id,
        )
        if row is None:
            raise SystemExit(f"봇 {bot_id} 가 없다.")
        if expect_bot_name and row["name"] != expect_bot_name:
            raise SystemExit(
                f"봇 {bot_id} 의 이름이 {row['name']!r} 다 — {expect_bot_name!r} 를 기대했다. "
                "아무것도 쓰지 않았다."
            )

        before = row["clarification_policy"]
        before = json.loads(before) if isinstance(before, str) else before
        print(
            f"[전] 봇 {bot_id}({row['name']} · {row['retrieval_mode']}) "
            f"clarify_enabled={row['clarify_enabled']} "
            f"규칙 {len((before or {}).get('rules', []))}개"
        )
        if dry_run:
            planned = [rule["id"] for rule in policy.get("rules", [])]
            print(f"[dry-run] 쓰지 않았다. 넣으려던 규칙 {len(planned)}개: {', '.join(planned)}")
            return

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
            f"[후] 봇 {bot_id}({row['name']} · {row['retrieval_mode']}) "
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
    parser.add_argument("--live", action="store_true", help="라이브 DSN 에 쓰는 것을 명시한다")
    parser.add_argument(
        "--expect-bot-name",
        help="이 이름이 아니면 아무것도 쓰지 않는다. --live 에 필수 (봇 id 는 DB 마다 다른 봇이다)",
    )
    parser.add_argument("--dry-run", action="store_true", help="현재 상태만 찍고 쓰지 않는다")
    args = parser.parse_args()
    asyncio.run(
        main(
            args.dsn,
            args.bot_id,
            args.policy,
            args.disable,
            args.live,
            args.expect_bot_name,
            args.dry_run,
        )
    )
