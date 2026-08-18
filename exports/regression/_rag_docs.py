# 봇별 RAG 문서 목록 스냅샷 → _ragdocs.json (읽기 전용. 생성/삭제 없음)
#
#   cd backend && set -a; source .env; set +a
#   .venv/bin/python ../exports/regression/_rag_docs.py --bots 7,11
#
# 리포트가 "어떤 자료로 답했는지"를 문서 단위로 보여주기 위한 근거 파일이다.
# 파일명은 macOS 업로드 경로에 따라 NFD/NFC 가 섞이므로 NFC 로 정규화해 저장한다.
import argparse
import asyncio
import json
import sys
import unicodedata as u
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/Users/woosung/project/agy-project/nexus-core/backend")

from app.core.config import get_settings  # noqa: E402
from app.services.llm.gemini import _get_genai_client  # noqa: E402

DIR = Path(__file__).parent
OUT = DIR / "_ragdocs.json"


async def main(bots):
    st = get_settings()
    cl = _get_genai_client()

    target = None
    async for s in await cl.aio.file_search_stores.list():
        if s.display_name == st.FILE_SEARCH_STORE_NAME:
            target = s
            break
    if not target:
        raise SystemExit(f"[중단] 스토어 '{st.FILE_SEARCH_STORE_NAME}' 미발견 — 생성하지 않음")

    by_bot = {}
    total = 0
    # page_size 는 API 제약상 1~20
    async for d in await cl.aio.file_search_stores.documents.list(
            parent=target.name, config={"page_size": 20}):
        total += 1
        bid = None
        for cm in (d.custom_metadata or []):
            if cm.key == "bot_id":
                bid = int(cm.numeric_value)
        if bid is None:
            continue
        by_bot.setdefault(bid, []).append({
            "name": u.normalize("NFC", d.display_name or "?"),
            "size_bytes": getattr(d, "size_bytes", None),
            "created": str(getattr(d, "create_time", "") or "")[:10],
        })

    picked = {str(b): sorted(by_bot.get(b, []), key=lambda x: x["name"]) for b in bots}
    OUT.write_text(json.dumps({
        "store": target.display_name, "store_resource": target.name,
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_in_store": total, "by_bot": picked,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"스토어 {target.display_name} · 전체 {total}건 → {OUT.name}")
    for b in bots:
        docs = picked[str(b)]
        print(f"  봇 {b}: {len(docs)}개")
        for d in docs:
            sz = f"{d['size_bytes']:,}B" if d["size_bytes"] else "—"
            print(f"     {d['name']}  [{sz} · {d['created']}]")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bots", default="7,11", help="쉼표 구분 bot_id")
    a = ap.parse_args()
    asyncio.run(main([int(x) for x in a.bots.split(",") if x.strip()]))
