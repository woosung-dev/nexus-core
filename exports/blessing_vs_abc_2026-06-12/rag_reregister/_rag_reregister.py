# 새 Gemini 키(프로젝트)에 블레싱 나(id3)·가(id5) RAG 문서를 재등록(업로드).
# 전제: backend/.env 의 GEMINI_API_KEY 를 새 키로 교체 후 실행.
# 사용: cd nexus-core && set -a; source backend/.env; set +a; backend/.venv/bin/python exports/blessing_vs_abc_2026-06-12/rag_reregister/_rag_reregister.py
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, "/Users/woosung/project/agy-project/nexus-core/backend")
import logging
logging.disable(logging.INFO)

from app.services.rag.gemini import GeminiRAGService  # noqa: E402

RR = Path("/Users/woosung/project/agy-project/nexus-core/exports/blessing_vs_abc_2026-06-12/rag_reregister")
DOCS = RR / "docs"
TARGET_BOTS = [3, 5]  # 블레싱 나, 블레싱 가 (동일 문서셋)
MIME = {".pdf": "application/pdf", ".md": "text/plain", ".txt": "text/plain"}


async def main():
    manifest = json.loads((RR / "rag_manifest.json").read_text(encoding="utf-8"))
    docs_meta = {d["display_name"]: d for d in manifest["documents"]}

    rag = GeminiRAGService()
    store = await rag.ensure_store()
    print(f"대상 스토어(신규 프로젝트): {store}")

    # docs/ 에 실제 존재하는 파일만 업로드 대상
    local_files = sorted(p for p in DOCS.iterdir() if p.is_file())
    print(f"업로드 후보 파일 {len(local_files)}개 (manifest 전체 {len(docs_meta)}종)\n")

    for bid in TARGET_BOTS:
        before = await rag.list_documents(bid)
        have = {d.display_name for d in before}
        print(f"--- bot_id={bid} ({manifest['bots'][str(bid)]}) 업로드 전 {len(before)}종 ---")
        for f in local_files:
            name = f.name
            # 이 문서가 해당 봇 소속인지 manifest 로 확인
            meta = docs_meta.get(name)
            if not meta or bid not in meta["bot_ids"]:
                continue
            if name in have:
                print(f"  [건너뜀] 이미 존재: {name}")
                continue
            data = f.read_bytes()
            await rag.upload_document(
                bot_id=bid, file_data=data, filename=name,
                display_name=name, mime_type=MIME.get(f.suffix.lower(), "text/plain"))
            print(f"  [업로드] {name} ({len(data)}B)")
        after = await rag.list_documents(bid)
        print(f"  → bot_id={bid} 업로드 후 {len(after)}종\n")

    # 누락 안내
    missing = [d["display_name"] for d in manifest["documents"] if not d["available"]]
    if missing:
        print(f"⚠️ 원본 부재로 재등록 못한 문서 {len(missing)}종 (docs/ 에 넣고 재실행 필요):")
        for n in missing:
            print("  -", n)
    print("\n재등록 완료.")


if __name__ == "__main__":
    asyncio.run(main())
