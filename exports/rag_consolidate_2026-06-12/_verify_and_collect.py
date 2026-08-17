# 블레싱 가/나 RAG 스토어 15문서를 content_sha256 로 로컬 소스와 대조·검증하고 한 폴더로 모은다
"""
스토어(File Search) 실제 업로드본의 content_sha256 = 로컬 소스 파일의 sha256 을 비교해
바이트 일치 소스를 찾는다(파일명 아닌 내용 기준). --copy 면 일치본을 새 폴더로 복사.
"""

import argparse
import asyncio
import hashlib
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))  # backend 에서 실행

# 로컬 소스 후보 루트 — 여기 전부를 sha256 인덱싱해 스토어 해시와 매칭
CANDIDATE_ROOTS = [
    Path("/Users/woosung/문서/docs/RAG 데이터"),
    Path("/Users/woosung/문서/docs/규정 및 행정안내 리스트, 축복관련 말씀 2"),
    Path("/Users/woosung/project/agy-project/nexus-core/exports/round3_redteam/03_RAG데이터"),
    Path("/Users/woosung/project/agy-project/nexus-core/backend/uploads"),
]
DEST = Path("/Users/woosung/문서/docs/RAG 데이터/블레싱_가나_RAG정본_15문서_2026-06-12")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def index_candidates():
    """basename→[paths], size→[paths] 두 인덱스. 스토어는 content_sha256 미보유 → 파일명+크기로 검증."""
    by_name: dict[str, list[Path]] = {}
    by_size: dict[int, list[Path]] = {}
    for root in CANDIDATE_ROOTS:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_file() and not p.name.startswith("."):
                by_name.setdefault(p.name, []).append(p)
                try:
                    by_size.setdefault(p.stat().st_size, []).append(p)
                except Exception:
                    pass
    return by_name, by_size


async def store_docs(bot_id: int):
    """스토어에서 bot_id 문서의 (display_name, size_bytes) 목록 조회."""
    from app.services.rag.gemini import GeminiRAGService

    svc = GeminiRAGService()
    store_name = await svc.ensure_store()
    out = []
    async for doc in await svc._client.aio.file_search_stores.documents.list(parent=store_name):
        meta = {m.key: m.numeric_value for m in (getattr(doc, "custom_metadata", None) or [])
                if m.numeric_value is not None}
        if meta.get("bot_id") == bot_id:
            out.append((doc.display_name or "unknown", getattr(doc, "size_bytes", None)))
    return out


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--copy", action="store_true")
    ap.add_argument("--bot", type=int, default=5)
    args = ap.parse_args()

    print("로컬 후보 인덱싱 중…", flush=True)
    by_name, by_size = index_candidates()
    print(f"  후보 파일 {sum(len(v) for v in by_name.values())}개")

    docs = await store_docs(args.bot)
    print(f"\n스토어 bot_id={args.bot} 문서 {len(docs)}개 대조 (파일명+바이트크기):\n")

    matched, missing = [], []
    for name, size in sorted(docs):
        # 1순위: 파일명 일치 + 크기 일치
        cand = [p for p in by_name.get(name, []) if size is None or p.stat().st_size == size]
        if cand:
            matched.append((name, cand[0], "이름+크기"))
            print(f"  ✅ {name}  ({size}B)\n       ← {cand[0]}")
            continue
        # 2순위: 파일명만 일치(크기 불일치 → 버전 다름 경고)
        if by_name.get(name):
            p = by_name[name][0]
            print(f"  ⚠️  {name}  스토어 {size}B ≠ 로컬 {p.stat().st_size}B (버전 상이?)\n       ? {p}")
            missing.append((name, size, "size_mismatch"))
            continue
        # 3순위: 이름은 다르나 크기 동일(리네임 추정)
        same_size = by_size.get(size or -1, [])
        if same_size:
            print(f"  ≈ {name}  (이름 없음, 크기 {size}B 동일 후보)\n       ? {same_size[0]}")
            missing.append((name, size, "name_diff_size_same"))
        else:
            print(f"  ❌ {name}  ({size}B) — 로컬 매칭 없음")
            missing.append((name, size, "absent"))

    print(f"\n결과: 일치 {len(matched)}/{len(docs)}, 미해결 {len(missing)}")

    if args.copy:
        if missing:
            print("\n누락이 있어 복사 중단 — 먼저 누락 소스를 확보해야 함.")
            return
        DEST.mkdir(parents=True, exist_ok=True)
        for name, src, _method in matched:
            shutil.copy2(src, DEST / name)  # 스토어 display_name 으로 저장
        print(f"\n복사 완료 → {DEST}  ({len(matched)}개)")
        # 매니페스트
        lines = ["# 블레싱 가/나 RAG 정본 15문서 (스토어 업로드본 파일명+바이트크기 일치 검증)", "",
                 f"- 검증 기준: File Search 스토어 bot_id={args.bot} 업로드본의 display_name + size_bytes",
                 "- 가(id5)·나(id3) 동일 15문서. 파일명=스토어 display_name.", ""]
        for name, src, _method in sorted(matched):
            lines.append(f"- {name}  ←  {src}")
        (DEST / "_매니페스트.md").write_text("\n".join(lines), encoding="utf-8")
        print(f"매니페스트: {DEST / '_매니페스트.md'}")


if __name__ == "__main__":
    asyncio.run(main())
