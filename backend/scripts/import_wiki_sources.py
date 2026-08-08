"""위키 산출물(원문 조문 250건 + 페이지 138쪽)을 파일시스템에서 DB 로 적재한다.

`exports/wiki_2026-08/` 는 gitignore 라 배포 이미지에 실리지 않는다. 어휘 검색을 라이브에
붙이려면 원문이 DB 에 있어야 한다. 이 스크립트가 그 한 번의 이관을 한다.

자연키는 원문 `(sha8, src_id)` · 페이지 `(bot_id, slug)` 다. 재실행하면 같은 행을 갱신하므로
몇 번 돌려도 안전하다.

**페이지는 답변 본문이 아니라 검색 신호로 넣는다.** 위키 본문으로 답하는 팔 C 는 기각됐지만,
페이지의 `## 사실` 문장 971개가 fact 스케일이 되고 그것이 RRF 융합의 세 순위표 중 하나다.
빼고 45문항을 재보니 실제 주입 원문이 43/45 에서 달라졌다.

Usage:
    # 로컬 docker DB (Neon 금지)
    docker compose up -d db
    DATABASE_URL=postgresql+asyncpg://nexus_user:nexus_pass@localhost:5432/nexus_core \
        uv run python scripts/import_wiki_sources.py --bot 11 --dry-run
    DATABASE_URL=... uv run python scripts/import_wiki_sources.py --bot 11
"""

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlmodel import select  # noqa: E402

from app.core.database import async_session  # noqa: E402
from app.models.bot import Bot  # noqa: E402,F401  — wiki_bot_sources.bot_id FK 해석에 필요
from app.models.wiki_source import (  # noqa: E402
    WikiBotSource,
    WikiPageRow,
    WikiSourceUnit,
)

WIKI_ROOT = Path(
    os.getenv("WIKI_ROOT", ROOT.parent / "exports" / "wiki_2026-08")
)

_FRONT = re.compile(r"^---\n(.*?)\n---\n+(.*)", re.S)


def read_manifest(bot_id: int) -> list[dict]:
    path = WIKI_ROOT / "bots" / str(bot_id) / "manifest.json"
    if not path.is_file():
        sys.exit(f"❌ manifest 없음: {path}")
    return json.loads(path.read_text(encoding="utf-8"))["sources"]


def read_units(sha8: str, expected: int) -> list[dict]:
    """`sources/<sha8>/NNN.md` 를 읽는다. meta.json 의 count 와 어긋나면 중단한다.

    `_split.py` 가 원본 PDF 해시를 검증하고 나서 쪼갠 결과다. 개수가 다르면 디렉터리가
    부분 복사됐다는 뜻이라 조용히 넘기면 안 된다.
    """
    d = WIKI_ROOT / "sources" / sha8
    if not d.is_dir():
        sys.exit(f"❌ 소스 디렉터리 없음: {d}")
    units = []
    for path in sorted(d.glob("*.md")):
        m = _FRONT.match(path.read_text(encoding="utf-8"))
        if not m:
            sys.exit(f"❌ 프론트매터 없음: {path}")
        head = dict(re.findall(r"^(\w+):\s*(.+)$", m.group(1), re.M))
        body = m.group(2).rstrip()
        units.append(
            {
                "sha8": sha8,
                "src_id": head["src_id"],
                "doc": head["doc"],
                "locator": head["locator"],
                "text": body,
                "chars": len(body),
            }
        )
    if len(units) != expected:
        sys.exit(f"❌ {sha8} 조문 수 불일치 — manifest {expected} vs 파일 {len(units)}")
    return units


def _section(body: str, name: str) -> str:
    m = re.search(rf"^## {name}\n(.*?)(?=^## |\Z)", body, re.S | re.M)
    return m.group(1).strip() if m else ""


def read_pages(bot_id: int) -> list[dict]:
    """`bots/<id>/wiki/pages/*.md`. `store.load_pages` 와 같은 것을 읽어야 한다."""
    d = WIKI_ROOT / "bots" / str(bot_id) / "wiki" / "pages"
    if not d.is_dir():
        sys.exit(f"❌ 위키 페이지 디렉터리 없음: {d}")
    pages = []
    for path in sorted(d.glob("*.md")):
        m = _FRONT.match(path.read_text(encoding="utf-8"))
        if not m:
            sys.exit(f"❌ 프론트매터 없음: {path}")
        head, body = m.group(1), m.group(2)
        fields = dict(re.findall(r"^(\w+):\s*(.+)$", head, re.M))
        raw = fields.get("sources", "").strip().strip("[]")
        pages.append(
            {
                "bot_id": bot_id,
                "slug": fields.get("slug", path.stem),
                "title": fields.get("title", path.stem),
                "summary": _section(body, "요약"),
                "facts": _section(body, "사실"),
                "sources": [s.strip() for s in raw.split(",") if s.strip()],
            }
        )
    return pages


async def _upsert(session, model, key_fields: dict, payload: dict) -> bool:
    """자연키로 찾아 갱신하거나 새로 넣는다. 새로 넣었으면 True."""
    conds = [getattr(model, k) == v for k, v in key_fields.items()]
    existing = (await session.execute(select(model).where(*conds))).scalar_one_or_none()
    if existing:
        for k, v in payload.items():
            setattr(existing, k, v)
        session.add(existing)
        return False
    session.add(model(**payload))
    return True


async def run(bot_id: int, dry_run: bool) -> None:
    sources = read_manifest(bot_id)
    all_units: list[dict] = []
    for s in sources:
        units = read_units(s["sha8"], s["count"])
        all_units.extend(units)
        print(f"  {s['sha8']} {s['doc']:<10} {len(units):>4}건 "
              f"{sum(u['chars'] for u in units):>7,}자  ({s['prefix']})")
    pages = read_pages(bot_id)
    fact_lines = sum(
        len([ln for ln in p["facts"].splitlines() if ln.strip().startswith("- ")])
        for p in pages
    )

    print(f"\n원문 {len(all_units)}건 · {sum(u['chars'] for u in all_units):,}자")
    print(f"페이지 {len(pages)}쪽 · 사실문장 {fact_lines}건 (fact 스케일)")
    if dry_run:
        print("→ --dry-run 이라 DB 에 쓰지 않는다")
        return

    async with async_session() as session:
        n_unit = 0
        for u in all_units:
            n_unit += await _upsert(
                session, WikiSourceUnit, {"sha8": u["sha8"], "src_id": u["src_id"]}, u)

        n_link = 0
        for s in sources:
            payload = {
                "bot_id": bot_id,
                "sha8": s["sha8"],
                "prefix": s.get("prefix", ""),
                "doc": s.get("doc", ""),
                "display_name": s.get("display_name", ""),
                "count": s.get("count", 0),
            }
            n_link += await _upsert(
                session, WikiBotSource, {"bot_id": bot_id, "sha8": s["sha8"]}, payload)

        n_page = 0
        for p in pages:
            n_page += await _upsert(
                session, WikiPageRow, {"bot_id": bot_id, "slug": p["slug"]}, p)

        await session.commit()

    print(f"\n✅ 완료 — 원문 {len(all_units)}건(신규 {n_unit}) · "
          f"페이지 {len(pages)}쪽(신규 {n_page}) · 봇-문서 연결 {len(sources)}건(신규 {n_link})")


def main() -> None:
    parser = argparse.ArgumentParser(description="위키 원문 조문을 DB 에 적재")
    parser.add_argument("--bot", type=int, default=11, help="봇 id (기본 11)")
    parser.add_argument("--dry-run", action="store_true", help="DB 변경 없이 개수만 출력")
    args = parser.parse_args()
    print(f"WIKI_ROOT = {WIKI_ROOT}")
    asyncio.run(run(args.bot, args.dry_run))


if __name__ == "__main__":
    main()
