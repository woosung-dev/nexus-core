# golden 초안을 DB(redteam_goldens)에 적재한다 — 검수 화면이 읽는 곳.
#
# 적재 규칙
#   · 인용 대조를 통과한 카드만 넣는다. 통과 못 한 카드는 기준이 흔들린 것이라 넣지 않는다.
#     ("검증 기준의 결함은 챗봇 결함보다 찾기 어렵다" — QA 방법론 체크리스트)
#   · **관리자가 이미 판정한 행은 건드리지 않는다.** status != '초안' 이면 건너뛴다.
#     재적재로 사람의 판단을 덮어쓰는 일이 없어야 한다.
#   · `model_answer`(리뷰어 메모 46건)는 손대지 않는다.
#
# 사용:
#   set -a; source backend/.env; set +a
#   backend/.venv/bin/python exports/golden_2026-08/_load.py            # 미리보기
#   backend/.venv/bin/python exports/golden_2026-08/_load.py --apply    # 실제 반영
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

DIR = Path(__file__).parent
ROOT = DIR.parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import asyncpg  # type: ignore[import-not-found]  # noqa: E402

CORPUS_VERSION = "reg-v20 / glossary-v4 / gongmun-4"


async def main(apply: bool):
    cards = {int(k): v for k, v in json.loads((DIR / "_cards.json").read_text(encoding="utf-8")).items()}
    verify = {int(k): v for k, v in json.loads((DIR / "_verify.json").read_text(encoding="utf-8")).items()}

    ok = [g for g in cards if verify.get(g, {}).get("ok")]
    skipped = [g for g in cards if g not in ok]
    print(f"카드 {len(cards)}건 · 인용 대조 통과 {len(ok)}건 · 미통과 {len(skipped)}건 {skipped}")

    url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").split("?")[0]
    conn = await asyncpg.connect(url, ssl="require")

    # 관리자가 이미 판정한 행 — 절대 덮어쓰지 않는다
    decided = {r["group_id"] for r in await conn.fetch(
        "select group_id from redteam_goldens where status <> '초안'")}
    valid = {r["id"] for r in await conn.fetch(
        "select id from redteam_question_groups where id = any($1::int[])", ok)}

    to_write = [g for g in ok if g in valid and g not in decided]
    print(f"  판정 완료라 보존 {len(decided & set(ok))}건 · 없는 그룹 {len(set(ok) - valid)}건")
    print(f"  적재 대상 {len(to_write)}건")

    if not apply:
        print("\n[미리보기] --apply 를 붙여야 실제로 씁니다.")
        for g in to_write[:3]:
            c = cards[g]
            print(f"  gid {g} · coverage={c.get('coverage')} · 근거 {len(c.get('evidence', []))}건")
            print(f"    {c.get('golden', '')[:100]}…")
        await conn.close()
        return

    n = 0
    for g in to_write:
        c = cards[g]
        await conn.execute(
            """
            insert into redteam_goldens
              (group_id, golden, evidence, must_any, must_not, source_docs,
               corpus_version, coverage, open_question, draft_engine, status)
            values ($1,$2,$3::json,$4::json,$5::json,$6::json,$7,$8,$9,'codex','초안')
            on conflict (group_id) do update set
              golden = excluded.golden,
              evidence = excluded.evidence,
              must_any = excluded.must_any,
              must_not = excluded.must_not,
              source_docs = excluded.source_docs,
              corpus_version = excluded.corpus_version,
              coverage = excluded.coverage,
              open_question = excluded.open_question,
              updated_at = now()
            """,
            g,
            c.get("golden", ""),
            json.dumps(c.get("evidence", []), ensure_ascii=False),
            json.dumps(c.get("must_any", []), ensure_ascii=False),
            json.dumps(c.get("must_not", []), ensure_ascii=False),
            json.dumps(c.get("source_docs", []), ensure_ascii=False),
            CORPUS_VERSION,
            c.get("coverage"),
            c.get("open_question") or "",
        )
        n += 1

    rows = await conn.fetch(
        "select status, count(*) n from redteam_goldens group by 1 order by 2 desc")
    cov = await conn.fetch(
        "select coverage, count(*) n from redteam_goldens group by 1 order by 2 desc")
    await conn.close()
    print(f"\n적재 {n}건")
    print("  status:", {r["status"]: r["n"] for r in rows})
    print("  coverage:", {r["coverage"]: r["n"] for r in cov})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    asyncio.run(main(ap.parse_args().apply))
