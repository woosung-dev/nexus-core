# 운영 사실 시드를 DB(ops_facts)에 적재한다 — 관리자 검수 화면이 읽는 곳.
#
# 적재 규칙
#   · **전부 status='초안' 으로 넣는다.** 런타임은 승인분만 읽으므로 적재만으로는
#     챗봇 동작이 1도 바뀌지 않는다. 이게 안전 착지점이다.
#   · **관리자가 이미 판정한 행은 건드리지 않는다.** status != '초안' 이면 건너뛴다.
#     (golden 적재 스크립트와 같은 규약 — 재적재로 사람의 판단을 덮어쓰지 않는다)
#   · 같은 행의 식별자는 (kind, title). 시드를 고쳐 다시 돌리면 초안만 갱신된다.
#
# 시드 내용의 출처는 셋뿐이다. 지어낸 사실은 없다.
#   ① exports/regression/_l2.py 의 하드코딩 규칙 (표기·구버전 수치·폐지·미검증 용어)
#   ② ~/Downloads/축복챗봇_정답지_요청_2026-08-06.xlsx 의 ②·④ 탭 (이미 등록됨으로 적힌 것)
#   ③ exports/prompt4_2026-08-05/FINDINGS.md 의 실측
#   회신이 필요한 칸은 statement 를 "확인 대기"로 적어 두고 admin_note 에 무엇을 기다리는지 남긴다.
#
# ⚠ 시드에 없는 것 — '청평 → HJ천주천보수련원(청평)'
#   단순 치환으로는 '청평수련'(프로그램명 복합어)이 'HJ천주천보수련원(청평)수련'이 된다.
#   _l2.py 의 term_cheongpyeong 이 복합어를 review 로 넘기는 문맥 규칙을 갖고 있어
#   그쪽에 남겨 뒀다. 관리자 회신(④-5) 후 치환 규칙을 어떻게 쓸지 정하고 옮긴다.
#
# 사용:
#   set -a; source backend/.env; set +a
#   backend/.venv/bin/python exports/ops_facts_2026-08/_load.py            # 미리보기
#   backend/.venv/bin/python exports/ops_facts_2026-08/_load.py --apply    # 실제 반영
#
#   DATABASE_URL 을 덮어쓰면 로컬 DB 에 넣을 수 있다 (backend/.env 는 라이브 Neon 이다).
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

FIELDS = ("kind", "title", "superseded", "statement", "triggers", "detect",
          "evidence", "source_docs", "priority", "admin_note")


def _row(item: dict) -> dict:
    return {
        "kind": item["kind"],
        "title": item.get("title", ""),
        "superseded": item.get("superseded", ""),
        "statement": item.get("statement", ""),
        "triggers": item.get("triggers", []),
        "detect": item.get("detect", []),
        "evidence": item.get("evidence", []),
        "source_docs": item.get("source_docs", []),
        "priority": item.get("priority", 100),
        "admin_note": item.get("admin_note", ""),
    }


async def main(apply: bool):
    seed = [_row(i) for i in json.loads((DIR / "_seed.json").read_text(encoding="utf-8"))]
    print(f"시드 {len(seed)}건 — kind별:", end=" ")
    kinds: dict[str, int] = {}
    for r in seed:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    print(kinds)

    url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").split("?")[0]
    conn = await asyncpg.connect(url, ssl="require" if "neon.tech" in url else False)

    existing = {
        (r["kind"], r["title"]): r["status"]
        for r in await conn.fetch("select kind, title, status from ops_facts where bot_id is null")
    }
    decided = [r for r in seed if existing.get((r["kind"], r["title"]), "초안") != "초안"]
    to_write = [r for r in seed if (r["kind"], r["title"]) not in {(d["kind"], d["title"]) for d in decided}]

    print(f"  판정 완료라 보존 {len(decided)}건 · 적재 대상 {len(to_write)}건")
    if decided:
        print("   보존:", [(d["kind"], d["title"]) for d in decided])

    if not apply:
        print("\n[미리보기] --apply 를 붙여야 실제로 씁니다.")
        for r in to_write:
            print(f"  {r['kind']:<11} {r['title']}")
            print(f"    superseded={r['superseded']!r} → {r['statement'][:60]}…")
        await conn.close()
        return

    # (kind, title) 에 unique 제약이 없으므로 존재 여부로 갈라 쓴다.
    # 이미 있는 초안은 갱신, 없으면 삽입 — 재실행해도 행이 늘지 않는다.
    inserted = updated = 0
    for r in to_write:
        args = (
            r["superseded"], r["statement"],
            json.dumps(r["triggers"], ensure_ascii=False),
            json.dumps(r["detect"], ensure_ascii=False),
            json.dumps(r["evidence"], ensure_ascii=False),
            json.dumps(r["source_docs"], ensure_ascii=False),
            r["priority"], r["admin_note"], r["kind"], r["title"],
        )
        if (r["kind"], r["title"]) in existing:
            await conn.execute(
                """
                update ops_facts set
                  superseded=$1, statement=$2, triggers=$3::json, detect=$4::json,
                  evidence=$5::json, source_docs=$6::json, priority=$7, admin_note=$8,
                  updated_at=now()
                where bot_id is null and kind=$9 and title=$10 and status='초안'
                """,
                *args,
            )
            updated += 1
        else:
            await conn.execute(
                """
                insert into ops_facts
                  (bot_id, superseded, statement, triggers, detect,
                   evidence, source_docs, priority, admin_note, kind, title, status)
                values (null,$1,$2,$3::json,$4::json,$5::json,$6::json,$7,$8,$9,$10,'초안')
                """,
                *args,
            )
            inserted += 1
    n = inserted + updated

    rows = await conn.fetch("select status, count(*) n from ops_facts group by 1 order by 2 desc")
    approved = await conn.fetchval(
        "select count(*) from ops_facts where status in ('승인','수정승인') and is_active")
    await conn.close()
    print(f"\n적재 {n}건 (신규 {inserted} · 초안 갱신 {updated})")
    print("  status:", {r["status"]: r["n"] for r in rows})
    print(f"  런타임 반영 대상(승인+수정승인): {approved}건 — 0이면 챗봇 동작 무변경")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    asyncio.run(main(ap.parse_args().apply))
