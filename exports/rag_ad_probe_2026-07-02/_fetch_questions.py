# Neon 실서버에서 최근 실사용자 질문 ~25개를 읽기 전용으로 추출해 questions.json 으로 저장
import asyncio
import json
import re
import sys
from pathlib import Path

import asyncpg

# 라이브 DSN 은 `backend/.env` 에서 읽는다 — 코드에 박지 않는다.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _neon import neon_url  # noqa: E402

EXCLUDE_EMAIL = "woosung@test.com"
TARGET = 25
OUT = Path(__file__).parent / "questions.json"

# 인사말·무의미 입력 제외 패턴
_SKIP_RE = re.compile(r"^(안녕|하이|hi|hello|테스트|test|ㅎㅇ|ㅋ+|ㅇㅇ|넵?|응|감사|고마워)[\s!.~?]*$", re.I)


# 복붙된 채팅 UI 잔여물("You • 오후 10:12" 등) 제거
_UI_JUNK_RE = re.compile(r"\s*You\s*\n?[•·]\s*\n?(오전|오후)?\s*[\d:]*\s*$", re.I)


def clean(q: str) -> str:
    return _UI_JUNK_RE.sub("", q.strip()).strip()


def usable(q: str) -> bool:
    q = q.strip()
    if len(q) < 8 or len(q) > 500:
        return False
    if _SKIP_RE.match(q):
        return False
    return True


async def main():
    conn = await asyncpg.connect(neon_url())
    try:
        rows = await conn.fetch(
            """
            SELECT m.id AS message_id, m.content, m.created_at, b.name AS bot_name, u.email
            FROM messages m
            JOIN chat_sessions s ON s.id = m.session_id
            JOIN users u ON u.id = s.user_id
            LEFT JOIN bots b ON b.id = s.bot_id
            WHERE m.role::text IN ('USER', 'user')
              AND u.email <> $1
            ORDER BY m.created_at DESC
            LIMIT 400
            """,
            EXCLUDE_EMAIL,
        )
    finally:
        await conn.close()

    seen: set[str] = set()
    picked = []
    for r in rows:
        q = clean(r["content"] or "")
        if not usable(q):
            continue
        key = re.sub(r"\s+", "", q)[:80]
        if key in seen:
            continue
        seen.add(key)
        picked.append({
            "question": q,
            "source": "neon",
            "bot_name": r["bot_name"] or "",
            "asked_at": r["created_at"].isoformat(),
            "message_id": r["message_id"],
        })
        if len(picked) >= TARGET:
            break

    OUT.write_text(json.dumps(picked, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"수집 {len(picked)}문항 → {OUT.name}")
    for p in picked[:30]:
        print(f"  [{p['asked_at'][:10]}] ({p['bot_name']}) {p['question'][:70]}")


asyncio.run(main())
