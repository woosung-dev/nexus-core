# RAG 스토어 현황 읽기전용 스냅샷 — 봇ID별 문서 수·고유·중복·버전 파악(생성/삭제 없음)
# 사용: cd backend && set -a; source .env; set +a; uv run python ../exports/_rag_snapshot.py
import asyncio
import json
import sys
from collections import defaultdict
from datetime import date

sys.path.insert(0, "/Users/woosung/project/agy-project/nexus-core/backend")

from app.core.config import get_settings  # noqa: E402
from app.services.llm.gemini import _get_genai_client  # noqa: E402

OUT = f"/Users/woosung/project/agy-project/nexus-core/exports/rag_snapshot_before_{date.today()}.json"


async def main():
    settings = get_settings()
    store_name = settings.FILE_SEARCH_STORE_NAME
    client = _get_genai_client()

    # 스토어를 이름으로 찾는다. 없으면 생성하지 않고 중단(읽기전용 보장).
    target = None
    stores = await client.aio.file_search_stores.list()
    async for s in stores:
        if s.display_name == store_name:
            target = s
            break
    if not target:
        print(f"[중단] 스토어 '{store_name}' 미발견 — 생성하지 않음.")
        return

    print(f"스토어: {store_name} ({target.name})")

    docs = []
    doc_list = await client.aio.file_search_stores.documents.list(parent=target.name)
    async for d in doc_list:
        bot_id = None
        if getattr(d, "custom_metadata", None):
            for meta in d.custom_metadata:
                if meta.key == "bot_id":
                    bot_id = meta.numeric_value
        docs.append({
            "file_id": (d.name or "").rsplit("/", 1)[-1],
            "display_name": d.display_name or "unknown",
            "bot_id": int(bot_id) if bot_id is not None else None,
            "size_bytes": getattr(d, "size_bytes", None),
        })

    print(f"전체 문서 수: {len(docs)}")

    # 봇ID별 집계
    by_bot = defaultdict(list)
    for doc in docs:
        by_bot[doc["bot_id"]].append(doc)

    print("\n봇ID | 문서수 | 고유(display_name) | 최대중복배수")
    print("-" * 55)
    for bot_id in sorted(by_bot, key=lambda x: (x is None, x)):
        group = by_bot[bot_id]
        names = defaultdict(int)
        for doc in group:
            names[doc["display_name"]] += 1
        max_dup = max(names.values()) if names else 0
        print(f"{str(bot_id):>5} | {len(group):>5} | {len(names):>16} | {max_dup}x")

    # 중복·버전 상세(봇ID별 display_name 카운트)
    detail = {}
    for bot_id, group in by_bot.items():
        names = defaultdict(list)
        for doc in group:
            names[doc["display_name"]].append(doc["file_id"])
        detail[str(bot_id)] = {n: ids for n, ids in names.items()}

    snapshot = {
        "store": store_name,
        "store_resource": target.name,
        "total": len(docs),
        "generated": str(date.today()),
        "docs": docs,
        "by_bot_display_names": detail,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    print(f"\n스냅샷 저장: {OUT}")

    # 중복 있는 봇ID·문서 요약
    print("\n=== 중복(동일 display_name 2건 이상) 상세 ===")
    for bot_id, names in detail.items():
        dups = {n: ids for n, ids in names.items() if len(ids) > 1}
        if dups:
            print(f"  bot_id={bot_id}: 고유 {len(names)}개 중 중복 {len(dups)}개")
            for n, ids in sorted(dups.items(), key=lambda x: -len(x[1])):
                print(f"    [{len(ids)}x] {n}")


if __name__ == "__main__":
    asyncio.run(main())
