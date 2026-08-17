# 스테이징 봇(id3)에 신규 공문 4종을 업로드 — append(중복 없음 실측됨). id5(라이브)에는 쓰지 않음.
# 사용: cd backend && set -a; source .env; set +a; uv run python ../exports/_rag_stage_upload.py
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "/Users/woosung/project/agy-project/nexus-core/backend")

from app.services.rag.gemini import GeminiRAGService  # noqa: E402

R3 = Path("/Users/woosung/project/agy-project/nexus-core/exports/round3_rag")
FILES = [
    "매칭확정자_자격및기준_변경_2025-259호.md",
    "2025축복후보자_이수교육_인정기준확대_24-14호.md",
    "12일_가정출발의식_2021.md",
    "장애축복자녀_축복헌금_축도권_2024-96호.md",
]
STAGING_BOT_ID = 3  # 비라이브(카카오 미연결). 라이브 id5 아님.


async def main():
    rag = GeminiRAGService()
    before = await rag.list_documents(bot_id=STAGING_BOT_ID)
    print(f"id{STAGING_BOT_ID} 업로드 전 문서 수: {len(before)}")
    existing_names = {d.display_name for d in before}

    for fn in FILES:
        path = R3 / fn
        data = path.read_bytes()
        if fn in existing_names:
            print(f"  [건너뜀] 이미 존재: {fn}")
            continue
        await rag.upload_document(
            bot_id=STAGING_BOT_ID,
            file_data=data,
            filename=fn,
            display_name=fn,
            mime_type="text/plain",
        )
        print(f"  [업로드] {fn} ({len(data)}B)")

    after = await rag.list_documents(bot_id=STAGING_BOT_ID)
    print(f"id{STAGING_BOT_ID} 업로드 후 문서 수: {len(after)}")
    names = sorted(d.display_name for d in after)
    print("현재 문서 목록:")
    for n in names:
        print("  ", n)


if __name__ == "__main__":
    asyncio.run(main())
