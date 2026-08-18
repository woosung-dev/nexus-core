# 확인불요 추가초안 4건(신규2·교체2)을 블레싱 가(5)·나(3) 스토어에 반영 — 사용자 승인분
"""
신규: 데스밸리특별성염, 삼위기대 → upload_document
교체: 천일국_예복예물_안내, 축복헌금_환불규정 → replace_document(업로드 성공 후 구버전 삭제)
대상 bot_id = 3, 5. 보류분(가정공과금·식구가정관리·282호)은 손대지 않는다.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))

DRAFT_DIR = Path("/Users/woosung/문서/docs/RAG 데이터/블레싱_가나_RAG데이터_2026-06-12/02_미반영_추가초안_7")
MIME = "text/markdown"
NEW = ["데스밸리특별성염_전수및사용_2024-019호.md", "삼위기대_안내.md"]
REPLACE = ["천일국_예복예물_안내.md", "축복헌금_환불규정.md"]
BOTS = [3, 5]


async def main():
    from app.services.rag.gemini import GeminiRAGService

    svc = GeminiRAGService()
    for bot_id in BOTS:
        label = "블레싱 가" if bot_id == 5 else "블레싱 나"
        print(f"\n===== bot_id={bot_id} ({label}) =====", flush=True)
        for fname in NEW:
            data = (DRAFT_DIR / fname).read_bytes()
            await svc.upload_document(
                bot_id=bot_id, file_data=data, filename=fname, display_name=fname, mime_type=MIME
            )
            print(f"  + 신규 업로드: {fname} ({len(data)}B)", flush=True)
        for fname in REPLACE:
            data = (DRAFT_DIR / fname).read_bytes()
            await svc.replace_document(
                bot_id=bot_id, file_data=data, filename=fname, display_name=fname, mime_type=MIME
            )
            print(f"  ↻ 교체: {fname} ({len(data)}B)", flush=True)

    print("\n--- 반영 후 문서 수 확인 ---", flush=True)
    for bot_id in BOTS:
        docs = await svc.list_documents(bot_id)
        names = sorted(d.display_name for d in docs)
        print(f"bot_id={bot_id}: {len(docs)}문서")
        for n in names:
            mark = " ←NEW" if n in NEW else (" ←교체" if n in REPLACE else "")
            print(f"    {n}{mark}")


if __name__ == "__main__":
    asyncio.run(main())
